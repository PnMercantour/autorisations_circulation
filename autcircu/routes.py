import os

from datetime import datetime

import pypnusershub.routes

from flask import render_template, send_from_directory, request, redirect, g

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
@check_auth(2, redirect_on_expiration="/")
def auth_form():
    return render_template('auth_form.html')


# if you change this route, change it in script.js too
@app.route("/authorizations")
@check_auth(1, redirect_on_expiration="/")
def listing():

    now = datetime.utcnow()

    selected_year = request.args.get('year')
    if selected_year != "last-5-years":
        selected_year = to_int(selected_year, now.year)

    selected_month = request.args.get('month')
    if selected_month != "all-months":
        selected_month = to_int(selected_month, now.month)

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

    return render_template('listing.html',
                           selected_year=selected_year,
                           selected_month=selected_month,
                           type=type,
                           years=years,
                           months=MONTHS,
                           selected_auth_status=selected_auth_status,
                           auth_status=AUTH_STATUS,
                           )


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico',
                               mimetype='image/vnd.microsoft.icon')
