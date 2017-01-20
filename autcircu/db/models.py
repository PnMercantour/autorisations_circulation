
from uuid import uuid4

from datetime import date

from sqlalchemy_utils import (ChoiceType, UUIDType, JSONType, Timestamp,
                              generic_repr, ScalarListType)

from pypnusershub.db.models import db
from pypnusershub.db.tools import init_schema

# TODO: create a schema for it
# TODO: check if we can generate the UUID on the DB side


def in_one_year():
    now = date.today()
    return now.replace(year=now.year + 1)


request_to_place = db.Table('request_to_place',
    db.Column('auth_request_id', db.ForeignKey('auth_request.id')),
    db.Column('restricted_place_id', db.ForeignKey('restricted_place.id')),
    db.PrimaryKeyConstraint('auth_request_id', 'restricted_place_id')
)


@generic_repr
class RequestMotive(db.Model, Timestamp):

    __tablename__ = 'request_motive'

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    name = db.Column(db.Unicode(256), nullable=False)


@generic_repr
class RestrictedPlace(db.Model, Timestamp):

    __tablename__ = 'restricted_place'

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    name = db.Column(db.Unicode(256), nullable=False)


@generic_repr
class LetterTemplate(db.Model, Timestamp):

    __tablename__ = 'letter_template'

    TYPES = [
        ('decision', 'Decision'),
        ('arrete', 'Arrêté')
    ]

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    type = db.Column(ChoiceType(TYPES), nullable=False, default="decision")
    content = db.Column(db.UnicodeText)


@generic_repr
class AuthRequest(db.Model, Timestamp):

    __tablename__ = 'auth_request'

    GENDERS = [
        ('m', 'Homme'),
        ('f', 'Femme')
    ]

    TYPES = [
        ('pro', 'Professionnelle'),
        ('salese', 'Salèze'),
        ('other', 'Autre')
    ]

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    type = db.Column(ChoiceType(TYPES), nullable=False, default='other')

    request_date = db.Column(db.Date, nullable=False, default=date.today)
    motive = db.Column(db.ForeignKey('request_motive.id'))

    author_gender = db.Column(ChoiceType(GENDERS), nullable=False)
    author_name = db.Column(db.Unicode(128), nullable=False)
    author_address = db.Column(db.Unicode(256))
    author_phone = db.Column(db.Unicode(32))
    proof_documents = db.Column(JSONType)

    places = db.relationship('RestrictedPlace', secondary=request_to_place,
                             backref='requests')

    auth_start_date = db.Column(db.Date, nullable=False, default=date.today)
    auth_end_date = db.Column(db.Date, nullable=False, default=in_one_year)
    rules = db.Column(db.UnicodeText)

    vehicules = db.Column(ScalarListType(str))
    group_vehicules_on_doc = db.Column(db.Boolean, default=False,
                                       nullable=False)

    # TODO: privode boostrap templates and places, and add default value here
    template = db.Column(db.ForeignKey('letter_template.id'), nullable=False)
    custom_template = db.Column(db.UnicodeText)


def init_db(app, db=db):
    """ Create the schema and the tables if they don't exist """

    init_schema(app.config['SQLALCHEMY_DATABASE_URI'])
    with app.app_context():
        db.create_all()
