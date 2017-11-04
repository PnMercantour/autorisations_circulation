"""
    Prod server.
"""

from auth_circu.routes import app  # noqa
from auth_circu.db.utils import init_db  # noqa

init_db(app)

