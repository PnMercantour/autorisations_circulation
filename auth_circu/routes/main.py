import os
import uuid
import json

from datetime import datetime, date

import jinja2

import flask_excel

import pypnusershub.routes

from sqlalchemy.orm.session import make_transient

from flask import render_template, send_from_directory, request, redirect, g, Response

from werkzeug.exceptions import BadRequest

from pypnusershub.db.tools import AccessRightsError, user_from_token
from pypnusershub.routes import check_auth

from secretary import Renderer

from ..conf import app
from ..db.models import AuthRequest, RequestMotive, RestrictedPlace, db, AuthDocTemplate
from ..db.utils import get_object_or_abort, model_to_json
from ..admin import setup_admin

setup_admin(app)

# Auth
app.register_blueprint(pypnusershub.routes.routes, url_prefix="/auth")

# ODS export intégration
flask_excel.init_excel(app)

# Some constants we use in the later views
MONTHS = [("all-months", "tout mois")]
MONTHS.extend((i, datetime(2008, i, 1).strftime("%B")) for i in range(1, 13))
MONTHS_VALUES = [str(key) for key, val in MONTHS]


AUTH_STATUS = {"both": "émises ou valides", "emitted": "émises", "active": "valides"}

odt_renderer = Renderer()


def to_int(obj, default):
    try:
        return int(obj)
    except (TypeError, ValueError):
        return default


@app.context_processor
def inject_user():
    return dict(user=getattr(g, "user", None))


@app.route("/")
def home():
    try:
        # redirect on the auth listing page if the user is authenticated
        user_from_token(request.cookies["token"])
    except (AccessRightsError, KeyError):
        return render_template(
            "home.html", usershub_app_id=app.config["AUTHCIRCU_USERSHUB_APP_ID"]
        )
    return redirect("/authorizations", code=302)


@app.route("/authorizations/new")
@app.route("/authorizations/<auth_id>")
@check_auth(2, redirect_on_expiration="/", redirect_on_invalid_token="/")
def auth_form(auth_id=None):

    if auth_id:
        auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
        category = auth_req.category
        selected_template = auth_req.template
    else:
        category = request.args.get("category", "other")
        selected_template = None

    if category == "agropasto":
        place_filter = RestrictedPlace.category == "up"
    else:
        place_filter = RestrictedPlace.category == "piste"

    motives = RequestMotive.query.order_by(RequestMotive.created.asc())

    templates = AuthDocTemplate.query.filter(
        AuthDocTemplate.active == True  # noqa
    ).order_by(AuthDocTemplate.updated.desc())

    places = RestrictedPlace.query.filter(
        place_filter & (RestrictedPlace.active == True)  # noqa
    ).order_by(RestrictedPlace.name.asc())

    return render_template(
        "auth_form.html",
        motives=motives,
        category=category,
        places=json.dumps([place.serialize() for place in places]),
        auth_request=model_to_json(auth_req) if auth_id else None,
        auth_num=auth_req.number if auth_id else None,
        templates=templates,
        selected_template=selected_template,
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
                if "salese" in place.name.replace("è", "e").lower():
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

    return redirect("/authorizations/" + str(auth_req.id), code=302)


# if you change this route, change it in script.js too
@app.route("/authorizations")
@check_auth(1, redirect_on_expiration="/", redirect_on_invalid_token="/")
def listing():

    now = datetime.utcnow()
    # Find the oldest year to start from
    oldest_auth = (
        AuthRequest.query.filter(
            (AuthRequest.auth_start_date != None) & (AuthRequest.active == True)  # noqa
        )
        .order_by(AuthRequest.auth_start_date.asc())
        .first()
    )

    oldest_auth_date = getattr(oldest_auth, "auth_start_date", None)

    oldest_request = (
        AuthRequest.query.filter(
            (AuthRequest.request_date != None) & (AuthRequest.active == True)  # noqa
        )
        .order_by(AuthRequest.request_date.asc())
        .first()
    )

    oldest_request_date = getattr(oldest_request, "request_date", None)

    if oldest_request_date and oldest_auth_date:
        oldest_date = min((oldest_auth_date, oldest_request_date))
    else:
        oldest_date = oldest_request_date or oldest_auth_date or datetime.now()

    # listing of years you can select auth from
    years = [("last-5-years", "depuis 5 ans")]
    upper_bound = oldest_date.year - 1
    years.extend(((i, f"de {i}")) for i in range(now.year, upper_bound, -1))

    # get the status of auth to list
    default_status = "emitted"
    if g.user.id_droit_max <= 1:  # field agents are more interested in this
        default_status = "active"

    selected_auth_status = request.args.get("auth_status", default_status).lower()
    if selected_auth_status not in AUTH_STATUS:
        selected_auth_status = default_status

    return render_template(
        "listing.html",
        selected_year=now.year,
        selected_month=now.month,
        years=years,
        months=MONTHS,
        selected_auth_status=selected_auth_status,
        auth_status=AUTH_STATUS,
        searched_terms=request.args.get("search", ""),
    )


@app.route("/favicon.ico")
def favicon():
    """ Serve favicon on dev server. Override this with nginx or apache """
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "img/favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/test-template/")
@check_auth(6, redirect_on_expiration="/", redirect_on_invalid_token="/")
def test_template():
    """ Let the user upload a template for testing """
    return render_template("test_template.html")


@app.route("/test-template/", methods=["POST"])
def test_template_upload():
    if "file" not in request.files:
        raise BadRequest("There must be a 'file' parameter")

    file = request.files["file"]
    category = request.form["category"]

    auth_requests = AuthRequest.query.filter_by(category=category)

    if category != "legacy":
        auth_requests = auth_requests.filter_by(valid=True)

    auth_req = auth_requests.order_by(AuthRequest.created.desc()).first()

    if not auth_req:
        return Response("Il n'y a pas d'autorisation de ce type dans la base", status=400)

    prefix = auth_req.author_prefix
    if prefix:
        prefix += " "

    places = [place.name for place in auth_req.places]
    vehicules = list(auth_req.vehicules)

    start_date = auth_req.auth_start_date or datetime.now()
    auth_start_date = start_date.strftime("%d/%m/%Y")
    end_date = auth_req.auth_end_date or start_date
    auth_end_date = end_date.strftime("%d/%m/%Y")

    # agro pasto letters don't display the day for those dates
    if auth_req.category == "agropasto":
        auth_start_date = auth_start_date[3:]
        auth_end_date = auth_end_date[3:]

    # generate an easy to manipulate data structure for building the
    # authorizations cards. It's easier to do that here than in the template:
    # we can now always act like we have several cards even if we have only
    # one and always loop.
    if auth_req.group_vehicules_on_doc:
        cards = [vehicules]
    else:
        cards = [[v] for v in vehicules]
    try:
        data = odt_renderer.render(
            file.stream,
            author_prefix=prefix,
            auth_req=auth_req,
            request_date=auth_req.request_date.strftime("%d/%m/%Y"),
            feminin=auth_req.author_gender == "f",
            auth_start_date=auth_start_date,
            auth_end_date=auth_end_date,
            places=places,
            places_count=len(places),
            vehicules=vehicules,
            vehicules_count=len(vehicules),
            doc_creation_date=datetime.now().strftime("%d %B %Y"),
            legal_contact="Faux contact légal",
            cards=cards,
        )
    except jinja2.exceptions.TemplateSyntaxError as e:
        return Response(str(e), status=400)

    return "OK"


@app.errorhandler(404)
@app.errorhandler(403)
def redirect_to_listing(e):
    return redirect("/authorizations", code=302)
