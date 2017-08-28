import tempfile

from io import BytesIO
from datetime import datetime

import flask_excel

import weasyprint

from flask import (
    request,
    send_file,
)

from py3o.template import Template

from werkzeug.exceptions import BadRequest, abort

from pypnusershub.routes import check_auth

from ..conf import app
from ..db.models import AuthDocTemplate, AuthRequest
from ..db.utils import get_object_or_abort


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


@app.route('/exports/authorizations/<auth_id>/address_a4')
@check_auth(2)
def address_a4(auth_id):
    auth_req = get_object_or_abort(AuthRequest, AuthRequest.id == auth_id)
    if not auth_req.valid:
        return abort(400, "Can't get doc for a draft authorization.")

    template = (AuthDocTemplate.query
                               .filter(
                                   AuthDocTemplate.default_for == 'address_a4'
                                )
                               .one())

    with tempfile.NamedTemporaryFile() as f:

        name = auth_req.author_name
        t = Template(template.path, f.name)
        t.render({
            'author_gender': auth_req.author_prefix,
            'author_name': name,
            'author_address': auth_req.author_address.split('\n'),
        })

        filename = f'{name} - {datetime.now():%d/%m/%Y}.addresse_a4.odt'
        return send_file(
            BytesIO(f.read()),
            attachment_filename=filename,
            as_attachment=True
        )
