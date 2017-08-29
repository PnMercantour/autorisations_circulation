from io import BytesIO
from datetime import datetime

import flask_excel

import weasyprint

from flask import request, send_file, g

from secretary import Renderer

from werkzeug.exceptions import BadRequest, abort

from pypnusershub.routes import check_auth

from ..conf import app
from ..db.models import AuthDocTemplate, AuthRequest
from ..db.utils import get_object_or_abort


odt_renderer = Renderer()


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
        return send_file(
            pdf,
            attachment_filename=f'autorisations - {now}.pdf',
            as_attachment=True
        )


@app.route('/exports/authorizations/<auth_id>/address')
@check_auth(2)
def address_a4(auth_id):
    auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
    if not auth_req.valid:
        return abort(400, "Can't get doc for a draft authorization.")
    paper_format = request.args.get('format', 'address_a4')

    template = (AuthDocTemplate.query
                               .filter(
                                   AuthDocTemplate.default_for == paper_format
                                )
                               .one())

    name = auth_req.author_name
    prefix = auth_req.author_prefix + " " if auth_req.author_prefix else ""
    data = odt_renderer.render(
        template.path,
        author_prefix=prefix,
        author_name=name,
        author_address=auth_req.author_address
    )

    filename = f'{name} - {datetime.now():%d/%m/%Y}.addresse.odt'
    return send_file(
        BytesIO(data),
        attachment_filename=filename,
        as_attachment=True
    )


@app.route('/exports/authorizations/<auth_id>')
@check_auth(2)
def generate_auth_doc(auth_id):
    auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
    if not auth_req.valid:
        return abort(400, "Can't get doc for a draft authorization.")

    legal_contact = g.user.role.legal_contact
    if not legal_contact or not legal_contact.content:
        return abort(400, "Your account doesn't have a legal contact.")

    cover_format = request.args.get('cover_format', 'a4')
    template_filter = AuthDocTemplate.default_for == "letter_other"
    if auth_req.category == "salese":
        template_filter = AuthDocTemplate.default_for == "letter_salese"
    if auth_req.category == "agropasto":
        template_filter = AuthDocTemplate.default_for == "letter_agropasto"

    template = get_object_or_abort(AuthDocTemplate, template_filter)

    prefix = auth_req.author_prefix
    if prefix:
        prefix += " "

    places = list(auth_req.places)
    vehicules = list(auth_req.vehicules)
    data = odt_renderer.render(
        template.path,
        author_prefix=prefix,
        auth_req=auth_req,
        request_date=auth_req.request_date.strftime('%d/%m/%Y'),
        feminin=auth_req.author_gender == "f",
        auth_start_date=auth_req.auth_start_date.strftime('%d/%m/%Y'),
        auth_end_date=auth_req.auth_end_date.strftime('%d/%m/%Y'),
        places=places,
        places_count=len(places),
        vehicules=vehicules,
        vehicules_count=len(vehicules),
        doc_creation_date=datetime.now().strftime("%d %B %Y"),
        legal_contact=legal_contact.content
    )

    filename = f'{auth_req.author_name} - {datetime.now():%d/%m/%Y}.odt'
    return send_file(
        BytesIO(data),
        attachment_filename=filename,
        as_attachment=True
    )
