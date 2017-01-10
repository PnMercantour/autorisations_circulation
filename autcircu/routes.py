
from flask import Flask, render_template, send_from_directory

from .conf import app

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/autorisations")
def listing():
    return render_template('listing.html')

@app.route('/favicon.ico')
def favicon():
    print('test')
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'img/favicon.ico',
                               mimetype='image/vnd.microsoft.icon')
