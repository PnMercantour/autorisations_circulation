
from autcircu.routes import app
from autcircu.models import init_db

init_db(app)
app.run()
