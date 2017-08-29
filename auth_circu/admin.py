
from pypnusershub.db.models import db
from pypnusershub.routes import check_auth

from flask_admin.contrib.sqla import ModelView, filters
from flask_admin.contrib.sqla.form import AdminModelConverter
from flask_admin import Admin
from flask_admin.menu import MenuLink
from flask_admin import form
from flask_admin.model.form import converts

from .db.models import (
    RequestMotive, RestrictedPlace, AuthDocTemplate, LegalContact
)

from .conf import UPLOAD_DIR


class SQLAUtilsModelConverter(AdminModelConverter):
    """ Allow fields from SQLA-utils to be used in the admin """

    @converts('sqlalchemy_utils.types.choice.ChoiceType')
    def conv_ChoiceType(self, column, field_args, **extra):
        choices = column.type.choices

        def coerce(val):
            if isinstance(val, str):
                return val
            return val.code

        return form.Select2Field(
            choices=[(k, v) for k, v in choices],
            coerce=coerce,
            **field_args
        )


class AuthenticatedModelView(ModelView):
    """ Common features for all our admin configurations classes """
    model_form_converter = SQLAUtilsModelConverter
    column_exclude_list = form_excluded_columns = ('created', 'updated')
    can_delete = False

    @check_auth(
        3,
        redirect_on_expiration="/?next=/admin",
        redirect_on_invalid_token="/?next=/admin"
    )
    def _handle_view(self, name, **kwargs):
        return super()._handle_view(name, **kwargs)


class RequestMotiveView(AuthenticatedModelView):
    column_exclude_list = form_excluded_columns = (
        'created',
        'updated',
        'requests'
    )
    column_labels = form_labels = {
        'name': 'Nom',
        'active': 'Actif',
    }


class LegalContactView(AuthenticatedModelView):
    column_exclude_list = form_excluded_columns = (
        'created',
        'updated',
    )
    column_labels = form_labels = {
        'user': 'Utilisateur',
        'content': 'Contenu'
    }


class AuthDocTemplateView(AuthenticatedModelView):
    form_excluded_columns = ('created', 'updated')
    column_exclude_list = form_excluded_columns + ('path',)
    form_overrides = {
        'path': form.FileUploadField
    }
    form_args = {
        'path': {
            'base_path': UPLOAD_DIR,
            'allow_overwrite': False
        },
    }
    form_widget_args = {
        'path': {
            'readonly': True
        },
    }
    column_searchable_list = ['name']
    column_labels = {
        'name': 'Nom',
        'active': 'Actif',
        'path': 'Fichier',
        'default_for': 'Template par défaut de'
    }
    form_columns = ['name', 'path', 'active', 'default_for']

    def format_default_for(v, c, m, p):
        return m.default_for.value if m.default_for else ''

    column_formatters = {
        "default_for": format_default_for
    }


class RestrictedPlaceView(AuthenticatedModelView):
    column_searchable_list = ['name']
    column_default_sort = ('category', True)
    column_formatters = {
        "category": lambda v, c, m, p: m.category.value
    }
    column_filters = (
        filters.FilterInList(
            column=RestrictedPlace.category,
            name='Category',
            options=RestrictedPlace.CATEGORIES
        ),
    )
    column_labels = {
        'name': 'Nom',
        'category': 'Categorie',
        'active': 'Actif'
    }
    form_columns = ['name', 'category', 'active']


def setup_admin(app):

    # Automatic admin
    admin = Admin(
        app,
        name='Admin de la BDD des autorisations',
        index_view=RestrictedPlaceView(
            RestrictedPlace,
            db.session,
            endpoint='admin',
            url="/admin",
            static_folder="static"
        )
    )

    admin.add_view(RequestMotiveView(RequestMotive, db.session))
    admin.add_view(AuthDocTemplateView(AuthDocTemplate, db.session))
    admin.add_view(LegalContactView(LegalContact, db.session))
    admin.add_link(
        MenuLink(name='Retour aux autorisations', url='/authorizations')
    )
