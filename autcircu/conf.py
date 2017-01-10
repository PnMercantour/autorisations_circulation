
from pathlib import Path

from flask import Flask

PROJECT_DIR = Path(__file__).parent.parent.absolute()
VAR_DIR = PROJECT_DIR / 'var'
DB_PATH = VAR_DIR / 'db.sqlite'

app = Flask('autcircu')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + str(DB_PATH)
# Retire l'alerte indiquant que ce paramètre est déprécié
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
