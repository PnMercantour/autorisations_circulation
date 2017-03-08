
import os
import argparse


parser = argparse.ArgumentParser(description='Run the development server')
parser.add_argument('--config-file', help='Path to the config file')

args = parser.parse_args()
os.environ.setdefault('AUTH_CIRCU_CONFIG_FILE', args.config_file or "")

from autcircu.routes import app  # noqa
from autcircu.db.utils import init_db  # noqa

init_db(app)
app.run()
