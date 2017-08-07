import os
import functools
import operator
import calendar
from datetime import datetime

import pypnusershub.routes

from sqlalchemy.orm import joinedload, undefer
from sqlalchemy import extract

from flask import render_template, send_from_directory, request, redirect, g, jsonify

from werkzeug.exceptions import BadRequest

from flask_admin import Admin

from flask_admin.contrib.sqla import ModelView

from pypnusershub.db.models import User, db
from pypnusershub.db.tools import AccessRightsError, user_from_token
from pypnusershub.routes import check_auth

from .conf import app
from .db.models import AuthRequest


# Automatic admin
admin = Admin(app, name='Admin de la BDD des autorisations')
admin.add_view(ModelView(User, db.session))

# Auth
app.register_blueprint(pypnusershub.routes.routes, url_prefix='/auth')


MONTHS = [('all-months', 'tout mois')]
MONTHS.extend((i, datetime(2008, i, 1).strftime('%B')) for i in range(1, 13))
MONTHS_VALUES = [str(key) for key, val in MONTHS]


AUTH_STATUS = {
    'both': "émises ou valides",
    'emitted': 'émises',
    'active': 'valides'
}


def to_int(obj, default):
    try:
        return int(obj)
    except (TypeError, ValueError):
        return default


@app.route("/")
def home():
    try:
        # redirect on the auth listing page if the user is authenticated
        user_from_token(request.cookies['token'])
    except (AccessRightsError, KeyError):
        return render_template(
            'home.html',
            usershub_app_id=app.config['AUTHCIRCU_USERSHUB_APP_ID']
        )
    return redirect('/authorizations', code=302)


@app.route("/authorizations/new")
@check_auth(2, redirect_on_expiration="/", redirect_on_invalid_token="/")
def auth_form():
    return render_template('auth_form.html')


# if you change this route, change it in script.js too
@app.route("/authorizations")
@check_auth(1, redirect_on_expiration="/", redirect_on_invalid_token="/")
def listing():

    now = datetime.utcnow()
    # Find the oldest year to start from
    oldest_auth_date = (
        AuthRequest.query
                   .filter(AuthRequest.auth_start_date is not None)
                   .order_by(AuthRequest.auth_start_date.asc())
                   .first().auth_start_date
    )

    oldest_request_date = (
        AuthRequest.query
                   .filter(AuthRequest.request_date is not None)
                   .order_by(AuthRequest.request_date.asc())
                   .first().request_date
    )

    if oldest_request_date and oldest_auth_date:
        oldest_date = min((oldest_auth_date, oldest_request_date))
    else:
        oldest_date = oldest_request_date or oldest_auth_date

    # listing of years you can select auth from
    years = [('last-5-years', 'depuis 5 ans')]
    upper_bound = oldest_date.year - 1
    years.extend(((i, f'de {i}')) for i in range(now.year, upper_bound, -1))

    # get the status of auth to list
    default_status = 'emitted'
    if g.user.id_droit_max < 1:  # field agents are more interested in this
        default_status = 'active'

    selected_auth_status = request.args.get('auth_status',
                                            default_status).lower()
    if selected_auth_status not in AUTH_STATUS:
        selected_auth_status = default_status

    return render_template(
       'listing.html',
       selected_year=now.year,
       selected_month=now.month,
       type=type,
       years=years,
       months=MONTHS,
       selected_auth_status=selected_auth_status,
       auth_status=AUTH_STATUS,
       searched_terms=request.args.get('search', '')
    )


@app.route('/api/v1/authorizations', methods=['GET'])
def api_get_authorizations():

    # check that the HTTP request is valid
    try:
        year = request.args['year']
        if year != "last-5-years":
            year = int(year)
    except ValueError:
        raise BadRequest('"year" must be an int or "last-5-years"')
    except KeyError:
        raise BadRequest('"year" must be provided')

    try:
        month = request.args['month']
        if month != "all-months":
            month = int(month)
        if str(month) not in MONTHS_VALUES:
            raise BadRequest(f'"month" must be among: {", ".join(MONTHS_VALUES)}')
    except ValueError:
        raise BadRequest('"month" must be an int or "all-months"')
    except KeyError:
        raise BadRequest('"month" must be provided')

    try:
        status = request.args['status']
        if status not in AUTH_STATUS.keys():
            raise BadRequest(f'"status" must be among: {", ".join(AUTH_STATUS.keys())}')
    except KeyError:
        raise BadRequest('"status" must be provided')

    # Get a base query object from SQLAlchemy that we can filter
    # later
    auth_requests = (
        AuthRequest.query
                    # preload data from other table
                    # to speed up later serialization
                    .options(
                        joinedload(AuthRequest.places),
                        joinedload(AuthRequest.motive),
                    )
    )

    # From here we start filtering authorizations requests, taking in
    # consideration their status, month and year according to the sent
    # HTTP parameters.

    # SQLalchemy constructs that we will use later for filtering
    extracted_creation_year = extract('year', AuthRequest.request_date)
    extracted_auth_start_year = extract('year', AuthRequest.auth_start_date)
    extracted_auth_end_year = extract('year', AuthRequest.auth_end_date)

    now = datetime.now()

    if month == "all-months": # Don't filter by months

        if year == "last-5-years":  # Filter on a range of 5 years

            current_year = now.year
            five_years_ago = current_year - 5

            # Keep request emitted anytime between now and 5 years ago
            is_emitted = (
                (five_years_ago <= extracted_creation_year) &
                (extracted_creation_year <= current_year)
            )
            if status == "emitted":
                auth_requests = auth_requests.filter(is_emitted)

            # Keep authorizations active anytime between now and 5 years ago
            is_active = (
                (extracted_auth_start_year <= current_year) &
                (five_years_ago <= extracted_auth_end_year)
            )
            if status == 'active':
                auth_requests = auth_requests.filter(is_active)

            # Keep any of the above
            if status == "both":
                auth_requests = auth_requests.filter(is_emitted | is_active)

        else:  # Filter only on one year

            # Keep requests emitted any time during this particular year
            is_emitted = extracted_creation_year == year
            if status == "emitted":
                auth_requests = auth_requests.filter(is_emitted)

            # Keep authorisations active any time of this particular year
            is_active = (
                (extracted_auth_start_year <= year) &
                (extracted_auth_end_year >= year)
            )
            if status == 'active':
                auth_requests = auth_requests.filter(is_active)

            #  Keep any of the above
            if status == "both":
                auth_requests = auth_requests.filter(is_active | is_emitted)


    else:  # Filter by status, year AND by month

        extracted_creation_month = extract('month', AuthRequest.request_date)

        if year == "last-5-years":  # Filter on a range of 5 years

            current_year = now.year
            five_years_ago = current_year - 5

            # Keep requests emitted sometime between these 5 years,
            # but on this particular month
            is_emitted = (
               (
                    (five_years_ago <= extracted_creation_year) &
                    (extracted_creation_year <= current_year)
               ) & (extracted_creation_month == month)
            )
            if status == "emitted":
                auth_requests = auth_requests.filter(is_emitted)

            # Take the starting and ending date of this month for
            # each years of the past 5 years. Then keep the authorizations
            # that were active during at least one of those month.
            # Keep authorizations that are still valid during one of the
            # month
            filters = []
            for year in range(five_years_ago, current_year + 1):
                month_start_date = datetime(year, month, 1)
                month_end_date = datetime(year, month, calendar.mdays[month])
                filters.append(
                    (AuthRequest.auth_start_date <= month_end_date) &
                    (AuthRequest.auth_end_date >= month_start_date)
                )
            is_active = functools.reduce(operator.or_, filters)
            if status == 'active':
                auth_requests = auth_requests.filter(is_active)

            # Keep any of the above
            if status == "both":
                auth_requests = auth_requests.filter(is_active | is_emitted)

        else:  # Filter only on one year

            # Keep requests emitted any time during this particular month
            # of this particular year
            is_emitted = (
                (extracted_creation_year == year) &
                (extracted_creation_month == month)
            )
            if status == "emitted":
                auth_requests = auth_requests.filter(is_emitted)

            # Keep authorizations that are still valid during this particular
            # month of this particular year
            month_start_date = datetime(year, month, 1)
            month_end_date = datetime(year, month, calendar.mdays[month])
            is_active = (
                (AuthRequest.auth_start_date <= month_end_date) &
                (AuthRequest.auth_end_date >= month_start_date)
            )
            if status == 'active':
                auth_requests = auth_requests.filter(is_active)

            # Keep any of the above
            if status == "both":
                auth_requests = auth_requests.filter(is_active | is_emitted)

    auth_requests = (auth_requests.order_by(AuthRequest.request_date.desc())
                                  .all())

    return jsonify([obj.serialize() for obj in auth_requests])


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico',
                               mimetype='image/vnd.microsoft.icon')
