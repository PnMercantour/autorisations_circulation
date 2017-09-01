from io import BytesIO
from datetime import datetime

import flask_excel

import weasyprint

from flask import request, send_file, g, make_response, jsonify

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
        }[auth.get('author_gender', '')]
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


@app.route('/exports/authorizations/<auth_id>', methods=['POST', 'GET'])
@check_auth(2)
def generate_auth_doc(auth_id):
    auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
    if not auth_req.valid:
        msg = jsonify(message="Les brouillons ne peuvent être imprimés")
        return abort(make_response(msg, 400))

    legal_contact = g.user.role.legal_contact
    if not legal_contact or not legal_contact.content:
        msg = jsonify(
            message=(
                "Votre compte n'a pas de coordonnées de contact associées "
                "et ne peut donc imprimer un document. Veuilez demander à un "
                "administrateur de vous les rajouter."
            )
        )
        return abort(make_response(msg, 400))

    template = auth_req.template
    if not template:
        template_filter = AuthDocTemplate.default_for == "letter_other"
        if auth_req.category == "salese":
            template_filter = AuthDocTemplate.default_for == "letter_salese"
        if auth_req.category == "agropasto":
            template_filter = AuthDocTemplate.default_for == "letter_agropasto"

        template = get_object_or_abort(AuthDocTemplate, template_filter)

    prefix = auth_req.author_prefix
    if prefix:
        prefix += " "

    places = [place.name for place in auth_req.places]
    vehicules = list(auth_req.vehicules)

    auth_start_date = auth_req.auth_start_date.strftime('%d/%m/%Y')
    auth_end_date = auth_req.auth_end_date.strftime('%d/%m/%Y')
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

    data = odt_renderer.render(
        template.abs_path,
        author_prefix=prefix,
        auth_req=auth_req,
        request_date=auth_req.request_date.strftime('%d/%m/%Y'),
        feminin=auth_req.author_gender == "f",
        auth_start_date=auth_start_date,
        auth_end_date=auth_end_date,
        places=places,
        places_count=len(places),
        vehicules=vehicules,
        vehicules_count=len(vehicules),
        doc_creation_date=datetime.now().strftime("%d %B %Y"),
        legal_contact=legal_contact.content,
        cards=cards
    )

    filename = f'{auth_req.author_name} - {datetime.now():%d/%m/%Y}.odt'
    return send_file(
        BytesIO(data),
        attachment_filename=filename,
        as_attachment=True
    )

