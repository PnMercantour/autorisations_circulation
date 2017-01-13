import os

from datetime import datetime

import pypnusershub.routes

from flask import render_template, send_from_directory, request

from .conf import app

app.register_blueprint(pypnusershub.routes.routes, url_prefix='/auth/')


MONTHS = [(0, 'tout mois')]
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
    return render_template('home.html')


@app.route("/authorizations/new")
def auth_form():
    return render_template('auth_form.html')


@app.route("/authorizations")
def listing():

    now = datetime.utcnow()
    selected_year = to_int(request.args.get('year'), now.year)
    selected_month = to_int(request.args.get('month'), now.month)

    # TODO: by default "emitted" for admin, and "active" for agents
    default_status = 'emitted'
    selected_auth_status = request.args.get('auth_status',
                                            default_status).lower()
    if selected_auth_status not in AUTH_STATUS:
        selected_auth_status = default_status

    return render_template('listing.html',
                           selected_year=selected_year,
                           selected_month=selected_month,
                           end_year=now.year,
                           start_year=2000,  # TODO: get year from db
                           type=type,
                           months=MONTHS,
                           selected_auth_status=selected_auth_status,
                           auth_status=AUTH_STATUS,
                           )


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico',
                               mimetype='image/vnd.microsoft.icon')
