import functools
import operator
import calendar
from datetime import datetime

from flask import (
    request,
    jsonify,
    Response
)

from pypnusershub.routes import check_auth

from werkzeug.exceptions import abort, BadRequest

from sqlalchemy import extract
from sqlalchemy.orm import joinedload

from .main import MONTHS_VALUES, AUTH_STATUS
from ..db.models import AuthRequest, RestrictedPlace, db
from ..conf import app
from ..db.utils import get_object_or_abort


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

    auth_requests = (auth_requests.order_by(AuthRequest.updated.desc())
                                  .all())

    auth_requests = [obj.serialize() for obj in auth_requests]

    # small hack to avoid having the very long Salèse name displayed
    # in the listing
    for req in auth_requests:
        for place in req['places']:
            if "Piste de Salèse" in place['name']:
                place['name'] = "Piste de Salèse"
    return jsonify(auth_requests)


@app.route('/api/v1/authorizations/<auth_id>', methods=['DELETE'])
@check_auth(2)
def api_delete_authorization(auth_id):
    auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
    if auth_req.valid:
        return abort(400, "You can delete non draft authorization.")
    db.session.delete(auth_req)
    db.session.commit()
    return Response('ok')


def parseJSDate(string):
    """ Parse a JS date string and return a Python date() object or None"""
    if not string:
        return None
    return datetime.strptime(string.split('T')[0], '%Y-%m-%d').date()


@app.route('/api/v1/authorizations', methods=['POST'])
@app.route('/api/v1/authorizations/<auth_id>', methods=['PUT'])
@check_auth(2)
def api_put_authorizations(auth_id=None):
    """ Create a new authorization or update a new one

        We should use some kind of automatic validation for this on the server
        side, but it's unlikely somebody will try to disable JS in the parc and
        so to keep the implementation simple (which is a requirement),
        we will just save the data here without integrity validation and
        trust client side validation.

        @check_auth still ensure permissions are respected, and SQLAlchemy
        will automatically sanitize SQL so we should be ok security wise.
    """
    if auth_id is not None:
        auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
    else:
        auth_req = AuthRequest()

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
    auth_req.template_id = request.json.get('template') or None

    db.session.add(auth_req)
    db.session.commit()
    return jsonify(auth_req.serialize())
