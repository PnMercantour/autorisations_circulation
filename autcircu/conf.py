
import locale
import warnings

from textwrap import dedent

from pathlib import Path

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

PROJECT_DIR = Path(__file__).parent.parent.absolute()
VAR_DIR = PROJECT_DIR / 'var'
DB_PATH = VAR_DIR / 'db.sqlite'

app = Flask('autcircu')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(DB_PATH)
# Retire l'alerte indiquant que ce paramètre est déprécié
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
