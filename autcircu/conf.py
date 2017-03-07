
import locale
import warnings

from textwrap import dedent

from flask import Flask

LOCALE = ('fr_FR', 'UTF-8')

try:
    locale.setlocale(locale.LC_ALL, LOCALE)
except locale.Error:
    warnings.warn(dedent(f"""
        Unable to set the locale to "{LOCALE}". The default value
        ("{locale.getdefaultlocale()}") will be used. It means some of
        the text may not be translated properly, particularly dates.
        Either install the proper locale on your OS or change
        the locale settings in conf.py.
    """))

app = Flask('autcircu')

# TODO: make a config file for those and secret key
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'postgresql://mercantour:mercantour'
    '@127.0.0.1:5432/mercantour'
)

# Retire l'alerte indiquant que ce paramètre est déprécié
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Force the PN's UserHub authentification module to register their DP
# on our app.
# This will call models.db.init_app(app), but you still need to do
# with app.app_context():
#    db.create_all()
# if you wish to create the databases
app.config['INIT_APP_WITH_DB'] = True

app.config['SECRET_KEY'] = 'test'
app.config['COOKIE_AUTORENEW'] = True
app.config['COOKIE_EXPIRATION'] = 60 * 60 * 8  # 8 hours

app.config['AUTHCIRCU_USERSHUB_APP_ID'] = 20
app.config['BAD_LOGIN_STATUS_CODE'] = 400
