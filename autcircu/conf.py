
import os
import sys
import locale
import warnings
import configparser

from pathlib import Path
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

# load config file
config_file = os.environ.get("AUTH_CIRCU_CONFIG_FILE", "")

need_config_file = not any((
    'generate_config_file' in sys.argv,
    '--help' in sys.argv,
    '-h' in sys.argv,
))

if not config_file and need_config_file:

    config_file = Path('./settings.ini')
    if not config_file.is_file():
        sys.exit(
            'Please provide a config file with the --config-file option '
            'in runserver or using the "AUTH_CIRCU_CONFIG_FILE" env var. '
            'You can generate one using the generate_config_file subcommand.'
            )

if need_config_file:
    try:
        open(config_file).read()
    except (IOError, OSError) as e:
        sys.exit(f'Unable to read the config file "{config_file}": {e}')

    try:
        conf = configparser.ConfigParser()
        conf.read(config_file)
    except (configparser.MissingSectionHeaderError,
            configparser.ParsingError) as e:
        sys.exit(f'"{config_file}" is a malformed config file: {e}')

    try:
        security_conf = conf['security']
    except KeyError:
        sys.exit(f'"{config_file}" does not contain a "security" section')

    try:
        sql_db_uri = security_conf['DATABASE_URI']
    except KeyError:
        sys.exit(f'"{config_file}" does not contain an '
                  '"DATABASE_URI" entry')

    try:
        secret_key = security_conf['SECRET_KEY']
    except KeyError:
        sys.exit(f'"{config_file}" does not contain an "SECRET_KEY" entry')

    try:
        usershub_app_id = int(security_conf.get('AUTHCIRCU_USERSHUB_APP_ID', 20))
    except ValueError:
        sys.exit(f'"AUTHCIRCU_USERSHUB_APP_ID" should be a number')


    app.config['SQLALCHEMY_DATABASE_URI'] = sql_db_uri

    # Retire l'alerte indiquant que ce paramètre est déprécié
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Force the PN's UserHub authentification module to register their DP
    # on our app.
    # This will call models.db.init_app(app), but you still need to do
    # with app.app_context():
    #    db.create_all()
    # if you wish to create the databases
    app.config['INIT_APP_WITH_DB'] = True

    app.config['SECRET_KEY'] = secret_key
    app.config['COOKIE_AUTORENEW'] = True
    app.config['COOKIE_EXPIRATION'] = 60 * 60 * 8  # 8 hours

    app.config['AUTHCIRCU_USERSHUB_APP_ID'] = usershub_app_id
    app.config['BAD_LOGIN_STATUS_CODE'] = 400
