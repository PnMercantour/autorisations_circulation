import os
import uuid
import json
import functools
import operator
import calendar

from io import BytesIO
from datetime import datetime, date

import flask_excel

import weasyprint

import pypnusershub.routes

from sqlalchemy.orm import joinedload
from sqlalchemy import extract
from sqlalchemy.orm.session import make_transient

from flask import (
    render_template,
    send_from_directory,
    request,
    redirect,
    g,
    jsonify,
    send_file,
    Response
)

from werkzeug.exceptions import abort
from werkzeug.exceptions import BadRequest

from pypnusershub.db.tools import AccessRightsError, user_from_token
from pypnusershub.routes import check_auth

from .conf import app
from .db.models import AuthRequest, RequestMotive, RestrictedPlace, db
from .db.utils import get_object_or_abort, model_to_json
from .admin import setup_admin

setup_admin(app)

# Auth
app.register_blueprint(pypnusershub.routes.routes, url_prefix='/auth')

# ODS export intégration
flask_excel.init_excel(app)

# Some constants we use in the later views
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


@app.context_processor
def inject_user():
    return dict(user=getattr(g, 'user', None))


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
    category = request.args.get('category', 'other')

    if category == "agropasto":
        filter = RestrictedPlace.category != "legacy"
    else:
        filter = RestrictedPlace.category == "piste"

    motives = RequestMotive.query.order_by(RequestMotive.created.asc())
    places = (RestrictedPlace.query
                             .filter(
                                 filter &
                                 (RestrictedPlace.active == True)  # noqa
                             ).order_by(RestrictedPlace.name.asc()))

    return render_template(
        'auth_form.html',
        motives=motives,
        category=request.args.get('category', 'other'),
        places=json.dumps([place.serialize() for place in places])
    )


@app.route("/authorizations/<auth_id>")
@check_auth(2, redirect_on_expiration="/", redirect_on_invalid_token="/")
def auth_edit_form(auth_id):
    auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)

    motives = RequestMotive.query.order_by(RequestMotive.created.asc())

    if auth_req.category == "agropasto":
        filter = RestrictedPlace.category != "legacy"
    else:
        filter = RestrictedPlace.category == "piste"

    places = (RestrictedPlace.query
                             .filter(
                                 filter &
                                 (RestrictedPlace.active == True)  # noqa
                             ).order_by(RestrictedPlace.name.asc()))

    return render_template(
        'auth_form.html',
        motives=motives,
        category=request.args.get('category', 'other'),
        places=json.dumps([place.serialize() for place in places]),
        auth_request=model_to_json(auth_req),
        auth_num=auth_req.number
    )


@app.route("/authorizations/<auth_id>/clone")
@check_auth(2, redirect_on_expiration="/", redirect_on_invalid_token="/")
def clone_auth(auth_id):
    auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
    db.session.expunge(auth_req)
    make_transient(auth_req)
    auth_req.request_date = date.today()
    auth_req.id = uuid.uuid4()
    auth_req.valid = False
    auth_req.number = None
    db.session.add(auth_req)
    db.session.commit()
    return redirect('/authorizations/' + str(auth_req.id), code=302)


# if you change this route, change it in script.js too
@app.route("/authorizations")
@check_auth(1, redirect_on_expiration="/", redirect_on_invalid_token="/")
def listing():
    now = datetime.utcnow()
    # Find the oldest year to start from
    oldest_auth_date = (
        AuthRequest.query
                   .filter(
                       (AuthRequest.auth_start_date != None) &  # noqa
                       (AuthRequest.active == True)
                    )
                   .order_by(AuthRequest.auth_start_date.asc())
                   .first().auth_start_date
    )

    oldest_request_date = (
        AuthRequest.query
                   .filter(
                       (AuthRequest.request_date != None) &  # noqa
                       (AuthRequest.active == True)
                    )
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
       years=years,
       months=MONTHS,
       selected_auth_status=selected_auth_status,
       auth_status=AUTH_STATUS,
       searched_terms=request.args.get('search', '')
    )


@app.route('/exports/authorizations', methods=['POST'])
@check_auth(1)
def export_authorizations():
    try:
        authorizations = request.json['authorizations']
    except KeyError:
        raise BadRequest('"Authorizations" must be provided')

    header = [
        'Dates',
        'Auteur',
        'Adresse',
        'Lieux',
        'Véhicules',
    ]

    rows = [header]
    for auth in authorizations:

        dates = ''
        start = auth.get('auth_start_date', '')
        if start:
            dates = f"Début: {start}\n"
        end = auth.get('auth_end_date', '')
        if end:
            dates += f'Fin: {end}'

        name = {
            'm': 'M. ',
            'f': 'Mme. ',
            'na': ''
        }[auth.get('author_prefix', '')]
        name += auth.get('author_name') or ''

        rows.append([
            dates,
            name,
            auth.get('author_address') or '',
            ', '.join(place['name'] for place in auth.get('places', [])),
            ', '.join(auth.get('vehicules', []))
        ])

    if request.args.get('format', 'ods') != 'pdf':
        return flask_excel.make_response_from_array(rows, "ods")
    else:
        template = app.jinja_env.get_template('pdf-export.html')
        now = f'{datetime.now():%d/%m/%Y}'
        rendered = template.render(auth_requests=rows, date=now)
        pdf = BytesIO(weasyprint.HTML(string=rendered).write_pdf())
        return send_file(pdf, attachment_filename='authorizations.pdf')


@app.route('/api/v1/authorizations', methods=['GET'])
@check_auth(1)
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
            raise BadRequest(
                f'"month" must be among: {", ".join(MONTHS_VALUES)}'
            )
    except ValueError:
        raise BadRequest('"month" must be an int or "all-months"')
    except KeyError:
        raise BadRequest('"month" must be provided')

    try:
        status = request.args['status']
        if status not in AUTH_STATUS.keys():
            raise BadRequest(
                f'"status" must be among: {", ".join(AUTH_STATUS.keys())}'
            )
    except KeyError:
        raise BadRequest('"status" must be provided')

    # Get a base query object from SQLAlchemy that we can filter
    # later
    auth_requests = (
        AuthRequest.query
                    # preload data from other table
                    # to speed up later serialization
                    .filter(AuthRequest.active == True)  # noqa
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

    if month == "all-months":  # Don't filter by months

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


def parseJSDate(string):
    """ Parse a JS date string and return a Python date() object or None"""
    if not string:
        return None
    return datetime.strptime(string.split('T')[0], '%Y-%m-%d').date()


@app.route('/api/v1/authorizations', methods=['POST'])
@check_auth(2)
def api_post_authorizations():
    """ Create a new authorization

        We should use some kind of automatic validation for this on the server
        side, but it's unlikely somebody will try to disable JS in the parc and
        so to keep the implementation simple (which is a requirement),
        we will just save the data here without integrity validation and
        trust client side validation.

        @check_auth still ensure permissions are respected, and SQLAlchemy
        will automatically sanitize SQL so we should be ok security wise.
    """
    places = []
    for place in request.json.get('places', []):
        filter = RestrictedPlace.id == place['id']
        places.append(RestrictedPlace.query.filter(filter).one())

    auth_req = AuthRequest(
        category=request.json.get('category'),
        request_date=parseJSDate(request.json.get('requestDate')),
        motive_id=request.json.get('motive'),
        author_gender=request.json.get('authorGender'),
        author_name=request.json.get('authorName'),
        author_address=request.json.get('authorAddress'),
        author_phone=request.json.get('authorPhone'),
        group_vehicules_on_doc=request.json.get('groupVehiculesOnDoc'),
        auth_start_date=parseJSDate(request.json.get('authStartDate')),
        auth_end_date=parseJSDate(request.json.get('authEndDate')),
        proof_documents=request.json.get('proofDocuments', []),
        rules=request.json.get('rules'),
        vehicules=request.json.get('vehicules', []),
        places=places,
        active=True,
        valid=request.json.get('valid', False)
    )

    db.session.add(auth_req)
    db.session.commit()
    return jsonify(auth_req.serialize())


@app.route('/api/v1/authorizations/<auth_id>', methods=['PUT'])
@check_auth(2)
def api_put_authorizations(auth_id):
    """ Update an existing AuthRequest

        Same notes that for api_post_authorizations().
    """
    auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)

    places = []
    for place in request.json.get('places', []):
        filter = RestrictedPlace.id == place['id']
        places.append(RestrictedPlace.query.filter(filter).one())

    auth_req.category = request.json.get('category')
    auth_req.request_date = parseJSDate(request.json.get('requestDate'))
    auth_req.motive_id = request.json.get('motive')
    auth_req.author_gender = request.json.get('authorGender')
    auth_req.author_name = request.json.get('authorName')
    auth_req.author_address = request.json.get('authorAddress')
    auth_req.author_phone = request.json.get('authorPhone')
    auth_req.group_vehicules_on_doc = request.json.get('groupVehiculesOnDoc')
    auth_req.auth_start_date = parseJSDate(request.json.get('authStartDate'))
    auth_req.auth_end_date = parseJSDate(request.json.get('authEndDate'))
    auth_req.proof_documents = request.json.get('proofDocuments', [])
    auth_req.rules = request.json.get('rules')
    auth_req.vehicules = request.json.get('vehicules', [])
    auth_req.places = places
    auth_req.active = True
    auth_req.valid = request.json.get('valid', False)

    db.session.add(auth_req)
    db.session.commit()
    return jsonify(auth_req.serialize())


@app.route('/api/v1/authorizations/<auth_id>', methods=['DELETE'])
@check_auth(2)
def api_delete_authorization(auth_id):
    auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
    if auth_req.valid:
        return abort(400, message="You can delete non draft authorization.")
    db.session.delete(auth_req)
    db.session.commit()
    return Response('ok')


@app.route('/favicon.ico')
def favicon():
    """ Serve favicon on dev server. Override this with nginx or apache """
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.errorhandler(404)
@app.errorhandler(403)
def redirect_to_listing(e):
    return redirect('/authorizations', code=302)
