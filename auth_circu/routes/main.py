import os
import uuid
import json

from datetime import datetime, date

import flask_excel

import pypnusershub.routes

from sqlalchemy.orm.session import make_transient

from flask import (
    render_template,
    send_from_directory,
    request,
    redirect,
    g,
)

from pypnusershub.db.tools import AccessRightsError, user_from_token
from pypnusershub.routes import check_auth

from ..conf import app
from ..db.models import (
    AuthRequest, RequestMotive, RestrictedPlace, db, AuthDocTemplate
)
from ..db.utils import get_object_or_abort, model_to_json
from ..admin import setup_admin

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
@app.route("/authorizations/<auth_id>")
@check_auth(2, redirect_on_expiration="/", redirect_on_invalid_token="/")
def auth_form(auth_id=None):

    if auth_id:
        auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
        category = auth_req.category
        selected_template = auth_req.template
    else:
        category = request.args.get('category', 'other')
        selected_template = None

    if category == "agropasto":
        place_filter = RestrictedPlace.category != "legacy"
    else:
        place_filter = RestrictedPlace.category == "piste"

    motives = RequestMotive.query.order_by(RequestMotive.created.asc())

    templates = (AuthDocTemplate.query
                             .filter(
                                 AuthDocTemplate.active == True  # noqa
                             ).order_by(AuthDocTemplate.updated.desc()))

    places = (RestrictedPlace.query
                             .filter(
                                 place_filter &
                                 (RestrictedPlace.active == True)  # noqa
                             ).order_by(RestrictedPlace.name.asc()))

    return render_template(
        'auth_form.html',
        motives=motives,
        category=request.args.get('category', 'other'),
        places=json.dumps([place.serialize() for place in places]),
        auth_request=model_to_json(auth_req) if auth_id else None,
        auth_num=auth_req.number if auth_id else None,
        templates=templates,
        selected_template=selected_template
    )


@app.route("/authorizations/<auth_id>/clone")
@check_auth(2, redirect_on_expiration="/", redirect_on_invalid_token="/")
def clone_auth(auth_id):
    # get previous auth to clone, copy it, clear it for references, and
    # backup relations

    with db.session.begin():
        auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
        places = auth_req.places
        db.session.expunge(auth_req)
        make_transient(auth_req)

        auth_req.request_date = date.today()
        auth_req.id = uuid.uuid4()
        auth_req.valid = False
        auth_req.number = None
        auth_req.places = places

        if auth_req.category == "legacy":
            for place in places:
                if 'salese' in place.name.replace('è', 'e').lower():
                    auth_req.category = "salese"
                    break
            else:
                auth_req.category = "other"

        db.session.add(auth_req)


    # force previous places to be copied as well
    with db.session.begin():
        auth_req = AuthRequest.query.get(auth_req.id)
        auth_req.places = places
        db.session.add(auth_req)

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
