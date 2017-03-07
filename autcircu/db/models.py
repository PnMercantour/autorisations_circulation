
from uuid import uuid4
from datetime import date

from sqlalchemy.orm import load_only, deferred

from sqlalchemy_utils import (ChoiceType, UUIDType, JSONType, Timestamp,
                              generic_repr, ScalarListType)

from pypnusershub.db.models import db


# TODO: check if we can generate the UUID on the DB side


def in_one_year():
    now = date.today()
    return now.replace(year=now.year + 1)


class RequestMotive(db.Model, Timestamp):

    __tablename__ = 't_request_motive'
    __table_args__ = {'schema': 'auth_circu'}

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    name = db.Column(db.Unicode(256), nullable=False)

    def __repr__(self):
        return f"<RequestMotive {self.name!r}>"


class RestrictedPlace(db.Model, Timestamp):

    __tablename__ = 't_restricted_place'
    __table_args__ = {'schema': 'auth_circu'}

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    name = db.Column(db.Unicode(256), nullable=False)

    def __repr__(self):
        return f"<RestrictedPlace {self.name!r}>"


request_to_place = db.Table(
    't_request_to_place',
    db.Column(
        'auth_request_id',
        db.ForeignKey('auth_circu.t_auth_request.id')
    ),
    db.Column(
        'restricted_place_id',
        db.ForeignKey('auth_circu.t_restricted_place.id')
    ),
    db.PrimaryKeyConstraint('auth_request_id', 'restricted_place_id')
)


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

    def __repr__(self):
        return f"<LetterTemplate id='{self.id}'>"


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

    def __repr__(self):
        return f"<AuthRequest id='{self.id}'>"
