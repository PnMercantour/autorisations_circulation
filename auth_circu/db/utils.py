
import json
import random
import string
import unicodedata
from csv import DictReader, reader
from datetime import datetime

from pypnusershub.db.models import Application, ApplicationRight, User, \
    UserApplicationRight, db
from pypnusershub.db.tools import delete_schema, init_schema, load_fixtures
from pypnusershub.utils import text_resource_stream
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import exc
from sqlalchemy_utils import models
from werkzeug.exceptions import abort

import auth_circu


def generate_secret_key(size=50):
    punc = string.punctuation
    for letter in "%#;=:[]":
        punc = punc.replace(letter, '')
    pool = string.ascii_letters + string.digits + punc
    return "".join(random.SystemRandom().choice(pool) for i in range(size))


def start_app_context():
    from auth_circu.conf import app
    # trigger the blueprint registering which binds pypnusershub'db
    from auth_circu import routes  # noqa
    return app.app_context().push()


def init_db(app, db=db, debug_db=False):
    """ Create the schema and the tables if they don't exist """

    # init pypnusershub's db
    # init_schema(app.config['SQLALCHEMY_DATABASE_URI'])

    start_app_context()
    if not ApplicationRight.query.filter().count():
        load_fixtures(app.config['SQLALCHEMY_DATABASE_URI'])

    # init aut circu's db
    engine = create_engine(
        app.config['SQLALCHEMY_DATABASE_URI'],
    )

    with engine.connect():
        engine.execute("CREATE SCHEMA IF NOT EXISTS auth_circu")
        engine.execute("COMMIT")

    db.create_all()

    # ensure we have our application registered in the database
    with db.session.begin():
        application, created = get_or_create(
            db.session,
            Application,
            commit=True,
            id_application=app.config['AUTHCIRCU_USERSHUB_APP_ID'],
            create_method_kwargs={
                'nom_application': 'Autorisations de circulation',
                'desc_application': (
                    'Gestion des autorisations de circulation des '
                    'véhicules à moteur dans le PN du mercantour'
                )
            }
        )


def create_test_user(app, username, password, access_rights=6, db=db):
    """ Create a local user for testing. UsersHub is not notified """

    user = User.query.filter(User.identifiant == username).one_or_none()
    if user:
        raise ValueError(f"A user with username '{username}' already exists")

    with db.session.begin():

        user = User(identifiant=username, groupe=False)
        user.password = password
        db.session.add(user)
        db.session.flush()  # to get the new user id

        user_rights = UserApplicationRight(
            id_role=user.id_role,
            id_droit=access_rights,
            id_application=app.config['AUTHCIRCU_USERSHUB_APP_ID'],
        )
        db.session.add(user_rights)


def delete_db(app, db=db):
    delete_schema(app.config['SQLALCHEMY_DATABASE_URI'])
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    with engine.connect():
        engine.execute("DROP SCHEMA IF EXISTS auth_circu CASCADE")
        engine.execute("COMMIT")


def reset_schema(con_uri):
    delete_schema(con_uri)
    init_schema(con_uri)


def get_or_create(session,
                  model,
                  create_method='',
                  create_method_kwargs=None,
                  commit=False, # not used anymore
                  **kwargs):
    """ Get an existing object from the DB or create one """
    try:
        return session.query(model).filter_by(**kwargs).one(), True
    except exc.NoResultFound:
        kwargs.update(create_method_kwargs or {})
        try:
            created = getattr(model, create_method, model)(**kwargs)
            session.add(created)
            return created, False
        except IntegrityError:
            return session.query(model).filter_by(**kwargs).one(), True


def populate_db(data_file, db=db):

    # temporarly avoid settings default dates
    columns = auth_circu.db.models.AuthRequest.__table__.columns
    columns['auth_start_date'].default = None
    columns['auth_end_date'].default = None
    columns['request_date'].default = None

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

    with open(data_file, encoding="utf8") as data:

        with db.session.begin():

            for row in DictReader(data):

                # Remove useless spaces.
                row = {key: (value or "").strip() for key, value in row.items()}

                name = "{NOM} {PRENOM}".format_map(row).strip()
                address = "{ADRESSE}\n{CODE POSTAL} {COMMUNE}".format_map(row)\
                                                            .strip()

                # Fetch all authorised vehicules.
                vehicules = set()
                for i in range(1, 5):
                    immat = row[f"IMMATRICULATION {i}"] or ""
                    immat = immat.upper().replace(' OU', '')
                    immat = immat.replace('-', "").replace(' ', '')
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
                            restricted_place = auth_circu.db.models.RestrictedPlace(
                                name=place,
                                category="legacy"
                            )
                            all_places[norm_str] = restricted_place
                            db.session.add(restricted_place)
                        else:
                            restricted_place = all_places[norm_str]

                        places.append(restricted_place)

                # Get the gender of the person making the request
                gender = row['CIVILITE']
                if not gender:
                    gender = "na"
                elif 'mme' in gender.casefold():
                    gender = 'f'
                else:
                    gender = 'm'

                # Parse the starting and ending date
                try:
                    start_date = datetime.strptime(
                        row['DEBUT DECISION'],
                        '%d/%m/%y'
                    ).date()
                except (ValueError, TypeError, KeyError):
                    start_date = None

                try:
                    end_date = datetime.strptime(
                        row['FIN DECISION'],
                        '%d/%m/%y'
                    ).date()
                except (ValueError, TypeError, KeyError):
                    end_date = None

                try:
                    year = int(row.get('ANNEE AUTORISATION') or 0)
                except ValueError:
                    continue
                if year:
                    start_date = datetime(year, 1, 1)
                    end_date = datetime(year, 12, 31)

                number = row['NUMERO AUTORISATION']
                base = start_date.year if start_date else '????'
                if number:
                    if len(number) > 10:
                        number = auth_circu.db.models.generate_auth_number(base)
                        number = number.replace('C', 'iC')
                    else:
                        number = f"{base}-iC{int(number):04}"
                else:
                    number = auth_circu.db.models.generate_auth_number(base)

                proof_docs = []
                justificatif = row.get('JUSTIFICATIF')
                date_justificatif = row.get('DATE JUSTIFICATIF')
                if justificatif or date_justificatif:
                    proof_docs = [{
                            "legacy_info": justificatif,
                            "expiration": date_justificatif,
                            "doc_type": None
                    }]

                # TODO: put a "note" ?
                auth_req = auth_circu.db.models.AuthRequest(
                    valid=None,
                    active=True,
                    number=number,
                    category='legacy',
                    author_name=name or None,
                    author_gender=gender,
                    author_address=address or None,
                    author_phone=row['TELEPHONE'] or None,
                    auth_start_date=start_date,
                    auth_end_date=end_date,
                    vehicules=list(vehicules),
                    proof_documents=proof_docs
                )

                auth_req.request_date = (
                    auth_req.auth_start_date or
                    auth_req.auth_end_date or
                    datetime.today()
                )

                for place in places:
                    auth_req.places.append(place)

                db.session.add(auth_req)
                yield auth_req

        yield from import_restricted_place(db)

        yield from import_motives(db)


def get_object(model, *filters, default=None):
    """ Return SQLA object or a default value """
    try:
        return model.query.filter(*filters).one()
    except (exc.NoResultFound, exc.MultipleResultsFound):
        return default


def get_object_or_abort(model, *filters, code=404):
    """ Return SQLA object or a abort the request """
    obj = get_object(model, *filters)
    if obj is None:
        return abort(404)
    return obj


def model_to_json(obj):
    """ Take a serializable model and turn it to JSON
        Keys are converted to proper naming convention
    """
    res = {}
    # convert key from snake_case to camelCase
    for key, val in obj.serialize().items():
        head, *tail = key.split('_')
        res[head + ''.join(chunk.title() for chunk in tail)] = val
    return json.dumps(res)


def import_restricted_place(db):

    # add known restricted places
    with db.session.begin():
        with text_resource_stream('restricted_places.csv', 'auth_circu.db') as data:
            for row in DictReader(data):
                place = auth_circu.db.models.RestrictedPlace(
                    name=row['name'].strip().replace('_', ' '),
                    category=row['category'].strip(),
                    st=row['st'].strip(),
                    active=True,
                )
                db.session.add(place)
                yield row


def reset_restricted_places(db):
    auth_circu.db.models.RestrictedPlace.query.delete()
    list(import_restricted_place(db))


def import_motives(db):

    # add known motives
    with db.session.begin():
        # add known request motives
        with text_resource_stream('motives.csv', 'auth_circu.db') as data:
            for row in reader(data):
                motive = auth_circu.db.models.RequestMotive(
                    name=row[0].strip(),
                    active=True,
                )
                db.session.add(motive)
                yield row

def reset_motives(db):
    auth_circu.db.models.RequestMotive.query.delete()
    list(import_motives(db))
