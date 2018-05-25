
from uuid import uuid4
from datetime import date, datetime
from csv import DictReader

from sqlalchemy.orm import load_only, relationship, backref
from sqlalchemy.event import listens_for

from sqlalchemy_utils import (
    ChoiceType,
    UUIDType,
    JSONType,
    Timestamp,
    ScalarListType
)

from auth_circu.conf import UPLOAD_DIR
from pypnusershub.db.models import db
from pypnusershub.utils import text_resource_stream


def in_one_year():
    now = date.today()
    return now.replace(year=now.year + 1)


class LegalContact(db.Model, Timestamp):

    __tablename__ = 't_legal_contact'
    __table_args__ = {'schema': 'auth_circu'}

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    content = db.Column(db.Unicode(256), nullable=False)
    user_id = db.Column(db.ForeignKey('utilisateurs.t_roles.id_role'))
    user = relationship(
        "User",
        backref=backref("legal_contact", uselist=False)
    )


class RequestMotive(db.Model, Timestamp):

    __tablename__ = 't_request_motive'
    __table_args__ = {'schema': 'auth_circu'}

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    name = db.Column(db.Unicode(256), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    def serialize(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "active": self.active
        }

    def __repr__(self):
        return f"<RequestMotive {self.name!r}>"

    def __unicode__(self):
        return self.name


class RestrictedPlace(db.Model, Timestamp):

    __tablename__ = 't_restricted_place'
    __table_args__ = {'schema': 'auth_circu'}

    CATEGORIES = [
        ('legacy', 'Donnée importée'),
        ('up', 'Unité Pastorale'),
        ('piste', 'Piste')
    ]

    # Dynamically create a list of allowed ST
    with text_resource_stream('restricted_places.csv', 'auth_circu.db') as data:
        ST = sorted(set(row['st'] for row in DictReader(data)))
        ST = [(name, name) for name in ST]

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    name = db.Column(db.Unicode(256), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    # french short for "service territorial"
    st = db.Column(ChoiceType(ST))
    category = db.Column(
        ChoiceType(CATEGORIES),
        nullable=False,
    )

    def serialize(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'active': self.active,
            'category': self.category.code,
            'st': self.st.value if self.st else ''
        }

    def __repr__(self):
        return f"<RestrictedPlace {self.name!r}>"

    def __unicode__(self):
        return self.name


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


class AuthDocTemplate(db.Model, Timestamp):

    __tablename__ = 't_auth_doc_template'
    __table_args__ = {'schema': 'auth_circu'}

    DEFAULT_FORMATS = [
        ('address_a4', 'Adresse format A4'),
        ('address_envelope', 'Adresse format enveloppe'),
        ('letter_salese', 'Lettre pour autorisation Salèse'),
        ('letter_agropasto', 'Lettre pour autorisation Agro-pastorale'),
        ('letter_other', 'Lettre pour autres autorisations'),
        ('', 'Aucun'),
    ]

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    name = db.Column(db.Unicode(64), nullable=False)
    path = db.Column(db.Unicode(256), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    default_for = db.Column(
        ChoiceType(DEFAULT_FORMATS),
        default='',
    )

    @property
    def abs_path(self):
        return str(UPLOAD_DIR / self.path)

    def __repr__(self):
        return f"<AuthDocTemplate id='{self.id}'>"

    def __unicode__(self):
        return self.name

    def serialize(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "path": self.path,
            "active": self.active,
            "default_for": self.default_for.code,
        }


@listens_for(AuthDocTemplate, 'after_insert')
@listens_for(AuthDocTemplate, 'after_update')
def receive_after_insert(mapper, connection, target):
    """ Make sure the target stays unique """
    if target.default_for:
        filter = (
            (AuthDocTemplate.default_for == target.default_for) &
            (AuthDocTemplate.id != target.id)
        )

        AuthDocTemplate.query.filter(filter).update({'default_for': None})

        # Forbid the deactivation of a template that is a default template
        if not target.active:
            (AuthDocTemplate.query
                            .filter(AuthDocTemplate.id == target.id)
                            .update({'active': True}))


def generate_auth_number(year=None, baseline=1):
    """ Generate an auth request number """
    year = str(year or date.today().year)

    # get the request with the highest number for this year
    last_req = (AuthRequest.query
                           .filter(AuthRequest.number.like(f'{year}%'))
                           .order_by(AuthRequest.number.desc())
                           .options(load_only("number"))
                           .first())

    # extract it if it exists or start the counter at 1
    num = baseline
    if last_req:
        num = int(last_req.number.split('C')[-1] or (baseline - 1)) + 1

    return f"{year}-C{num:04}"


class AuthRequest(db.Model, Timestamp):

    __tablename__ = 't_auth_request'
    __table_args__ = {'schema': 'auth_circu'}

    GENDERS = [
        ('na', 'N/A'),
        ('m', 'Homme'),
        ('f', 'Femme')
    ]

    CATEGORIES = [
        ('agropasto', 'Agro-pastorale'),
        ('salese', 'Salèse'),
        ('legacy', 'Importée'),
        ('other', 'Autre')
    ]

    id = db.Column(UUIDType, default=uuid4, primary_key=True)
    category = db.Column(
        ChoiceType(CATEGORIES),
        nullable=False,
        default='other'
    )
    number = db.Column(
        db.String(15),
        nullable=False,
        default=generate_auth_number
    )

    request_date = db.Column(db.Date, default=date.today)

    motive_id = db.Column(db.ForeignKey('auth_circu.t_request_motive.id'))
    motive = relationship("RequestMotive", backref="requests")

    author_gender = db.Column(ChoiceType(GENDERS))
    author_name = db.Column(db.Unicode(128))
    author_address = db.Column(db.Unicode(256))
    author_phone = db.Column(db.Unicode(32))
    proof_documents = db.Column(JSONType)

    places = db.relationship(
        'RestrictedPlace',
        secondary=request_to_place,
        backref='requests'
    )

    auth_start_date = db.Column(db.Date)
    auth_end_date = db.Column(db.Date)
    rules = db.Column(db.UnicodeText, default="")

    vehicules = db.Column(ScalarListType(str))
    group_vehicules_on_doc = db.Column(db.Boolean, default=False,
                                       nullable=False)

    # TODO: provide boostrap templates and places, and add default value here
    template_id = db.Column(db.ForeignKey('auth_circu.t_auth_doc_template.id'))
    template = relationship("AuthDocTemplate", backref="requests")

    active = db.Column(db.Boolean, default=True, nullable=False)
    valid = db.Column(db.Boolean)

    @property
    def author_prefix(self):
        if self.author_gender == "m":
            return "M."
        if self.author_gender == "f":
            return "Mme."
        return ""

    def serialize(self):

        if self.request_date:
            request_date = f'{self.request_date:%d/%m/%Y}'
        else:
            request_date = None

        if self.auth_start_date:
            auth_start_date = f'{self.auth_start_date:%d/%m/%Y}'
        else:
            auth_start_date = None

        if self.auth_end_date:
            auth_end_date = f'{self.auth_end_date:%d/%m/%Y}'
        else:
            auth_end_date = None

        created = getattr(self, 'created') or datetime.now()

        return {
            'id': str(self.id),
            'category': getattr(self.category, 'code', self.category),
            'number': self.number,
            'request_date': request_date,
            'motive': self.motive.serialize() if self.motive else None,
            'author_gender': getattr(self.author_gender, 'code', None),
            'author_name': self.author_name,
            'author_address': self.author_address,
            'author_phone': self.author_phone,
            'proof_documents': self.proof_documents or [],
            'places': [place.serialize() for place in self.places],
            'auth_start_date': auth_start_date,
            'auth_end_date': auth_end_date,
            'rules': self.rules,
            'vehicules': self.vehicules or [],
            'group_vehicules_on_doc': self.group_vehicules_on_doc,
            'created': f'{created:%d/%m/%Y}',
            'active': self.active,
            'valid': self.valid,
            'template': str(self.template_id)
        }

    def __repr__(self):
        return f"<AuthRequest id='{self.id}'>"

    def __unicode__(self):
        return self.number
