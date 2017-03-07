
from autcircu.routes import app
from autcircu.db.utils import init_db

init_db(app)
app.run()
