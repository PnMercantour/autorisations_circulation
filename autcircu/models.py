
import unicodedata

from uuid import uuid4
from csv import DictReader

from datetime import date, datetime

from sqlalchemy.orm import deferred, load_only
from sqlalchemy import create_engine

from sqlalchemy_utils import (ChoiceType, UUIDType, JSONType, Timestamp,
                              generic_repr, ScalarListType)

from pypnusershub.db.models import db
from pypnusershub.db.tools import init_schema, delete_schema
from pypnusershub.utils import text_resource_stream

# TODO: create a schema for it
# TODO: check if we can generate the UUID on the DB side


def in_one_year():
    now = date.today()
    return now.replace(year=now.year + 1)


@generic_repr
class RequestMotive(db.Model, Timestamp):

    __tablename__ = 't_request_motive'
    __table_args__ = {'schema': 'auth_circu'}

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    name = db.Column(db.Unicode(256), nullable=False)


@generic_repr
class RestrictedPlace(db.Model, Timestamp):

    __tablename__ = 't_restricted_place'
    __table_args__ = {'schema': 'auth_circu'}

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    name = db.Column(db.Unicode(256), nullable=False)


request_to_place = db.Table('t_request_to_place',
    db.Column('auth_request_id',
              db.ForeignKey('auth_circu.t_auth_request.id')),
    db.Column('restricted_place_id',
              db.ForeignKey('auth_circu.t_restricted_place.id')),
    db.PrimaryKeyConstraint('auth_request_id', 'restricted_place_id')
)


@generic_repr
class LetterTemplate(db.Model, Timestamp):

    __tablename__ = 't_letter_template'
    __table_args__ = {'schema': 'auth_circu'}

    TYPES = [
        ('decision', 'Decision'),
        ('arrete', 'Arrêté')
    ]

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    type = db.Column(ChoiceType(TYPES), nullable=False, default="decision")
    content = db.Column(db.UnicodeText)


@generic_repr
class AuthRequest(db.Model, Timestamp):

    __tablename__ = 't_auth_request'
    __table_args__ = {'schema': 'auth_circu'}

    GENDERS = [
        ('na', 'N/A'),
        ('m', 'Homme'),
        ('f', 'Femme')
    ]

    TYPES = [
        ('pro', 'Professionnelle'),
        ('salese', 'Salèse'),
        ('other', 'Autre')
    ]

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    type = db.Column(ChoiceType(TYPES), nullable=False, default='other')
    number = db.Column(db.String(10), nullable=False)

    request_date = db.Column(db.Date, default=date.today)
    motive = db.Column(db.ForeignKey('auth_circu.t_request_motive.id'))

    author_gender = db.Column(ChoiceType(GENDERS), nullable=False)
    author_name = db.Column(db.Unicode(128))
    author_address = db.Column(db.Unicode(256))
    author_phone = db.Column(db.Unicode(32))
    proof_documents = db.Column(JSONType)

    places = db.relationship('RestrictedPlace', secondary=request_to_place,
                             backref='requests')

    auth_start_date = db.Column(db.Date, default=date.today)
    auth_end_date = db.Column(db.Date, default=in_one_year)
    rules = db.Column(db.UnicodeText)

    vehicules = db.Column(ScalarListType(str))
    group_vehicules_on_doc = db.Column(db.Boolean, default=False,
                                       nullable=False)

    # TODO: privode boostrap templates and places, and add default value here
    template = db.Column(db.ForeignKey('auth_circu.t_letter_template.id'))
    custom_template = deferred(db.Column(db.UnicodeText))


    @classmethod
    def generate_number(cls, year=None, baseline=1):
        year = str(year or date.today().year)

        # get the request with the highest number for this year
        last_req = (AuthRequest.query
                               .filter(AuthRequest.number.like(f'{year}%'))
                               .order_by(AuthRequest.number.desc())
                               .options(load_only("number"))
                               .first())

        # extract it if it exists or start the counter at 1
        if last_req:
            num = int(last_req.number.split('c')[-1]) + 1
        else:
            num = baseline

        return f"{year}-c{num:04}"


def start_app_context():
    from autcircu.conf import app
    # trigger the blueprint registering which binds pypnusershub'db
    from autcircu import routes
    return app.app_context().push()


def init_db(app, db=db):
    """ Create the schema and the tables if they don't exist """

    # init pypnusershub's db
    init_schema(app.config['SQLALCHEMY_DATABASE_URI'])

    # init aut circu's db
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    with engine.connect():
        engine.execute("CREATE SCHEMA IF NOT EXISTS auth_circu")
        engine.execute("COMMIT")

    start_app_context()
    db.create_all()


def delete_db(app, db=db):
    delete_schema(app.config['SQLALCHEMY_DATABASE_URI'])
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    with engine.connect():
        engine.execute("DROP SCHEMA IF EXISTS auth_circu CASCADE")
        engine.execute("COMMIT")


def reset_schema(con_uri):
    delete_schema(con_uri)
    init_schema(con_uri)


def populate_db(db=db):

    # temporarly avoid settings default dates
    AuthRequest.__table__.columns['auth_start_date'].default = None
    AuthRequest.__table__.columns['auth_end_date'].default = None
    AuthRequest.__table__.columns['request_date'].default = None

    def normalize(s):
        """ Return a normalize string so that you can compare duplicate """
        # convert to lower case ascii chars
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')
        s = s.decode('ascii').strip().lower()

        # remove non alphanumerical characters
        ''.join(e for e in s.casefold() if e.isalnum())

        # remove spaces
        return ' '.join(s.split())

    all_places = {}

    with text_resource_stream('legacy_auth_export.csv', 'autcircu.db') as data:

        for row in DictReader(data):

            # Default type is "other", we should not have 'pro' as they are
            # a new thing, and we switch to salèze if we see it in the places
            request_type = "other"

            # Remove useless spaces.
            row = {key: value.strip() for key, value in row.items()}

            name = "{NOM} {PRENOM}".format_map(row).strip()
            address = "{ADRESSE} {CODE POSTAL} {COMMUNE}".format_map(row)\
                                                         .strip()

            # Fetch all authorised vehicules.
            vehicules = set()
            for i in range(1, 5):
                immat = row[f"IMMATRICULATION {i}"]
                if immat:
                    vehicules.add(immat)

            # Fetch all the places, avoiding duplates.
            # Also check if we are asking an auth for Salèse.
            places = []
            for i in range(1, 3):
                place = row[f"PISTE {i}"]
                if place:

                    norm_str = normalize(place)

                    if norm_str not in all_places:
                        restricted_place = RestrictedPlace(name=place)
                        all_places[norm_str] = restricted_place
                        db.session.add(restricted_place)
                    else:
                        restricted_place = all_places[norm_str]

                    if "salese" in norm_str:
                        request_type = 'salese'

                    places.append(restricted_place)

            # Get the gender of the person making the request
            # TODO: what do we display in the template for N/A ?
            gender = row['CIVILITE']
            if not gender:
                gender = "na"
            elif 'mme' in gender.casefold():
                gender = 'f'
            else:
                gender = 'm'

            # Parse the starting and ending date
            try:
                start_date = datetime.strptime(row['DEBUT DECISION'],
                                               '%d/%m/%y').date()
            except (ValueError, TypeError):
                start_date = None

            try:
                end_date = datetime.strptime(row['FIN DECISION'],
                                               '%d/%m/%y').date()
            except (ValueError, TypeError):
                end_date = None

            number = row['NUMERO AUTORISATION']
            if not number:
                if start_date:
                    number = AuthRequest.generate_number(start_date.year)
                else:
                    number = AuthRequest.generate_number('????')

            # TODO: put a "note" ?
            auth_req = AuthRequest(
                number=number,
                type=request_type,
                author_name=name or None,
                author_gender=gender,
                author_address=address or None,
                author_phone=row['TELEPHONE'] or None,
                auth_start_date=start_date,
                auth_end_date=end_date,
                vehicules=list(vehicules),
                proof_documents={
                    "legacy_info": row['JUSTIFICATIF'],
                    "expiration": row['DATE JUSTIFICATIF'],
                    "doc_type": None
                }
            )

            for place in places:
                auth_req.places.append(place)

            db.session.add(auth_req)
            yield auth_req

        db.session.commit()
