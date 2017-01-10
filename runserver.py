from autcircu.routes import app
from autcircu.models import db
db.create_all()
app.run()
