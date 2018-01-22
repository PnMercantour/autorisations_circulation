"""
    Prod server.
"""

from auth_circu.routes import app  # noqa
from auth_circu.db.utils import init_db  # noqa

app.config['INIT_APP_WITH_DB'] = True

init_db(app)

