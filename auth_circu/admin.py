
from pathlib import Path


from pypnusershub.db.models import db
from pypnusershub.routes import check_auth

from flask_admin.contrib.sqla import ModelView, filters
from flask_admin.contrib.sqla.form import AdminModelConverter
from flask_admin import Admin
from flask_admin.contrib.fileadmin import FileAdmin
from flask_admin.menu import MenuLink
from flask_admin import form
from flask_admin.model.form import converts

from .db.models import RequestMotive, RestrictedPlace


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
        'category': 'Categorie'
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

    admin.add_view(AuthenticatedModelView(RequestMotive, db.session))
    admin.add_link(
        MenuLink(name='Retour aux autorisations', url='/authorizations')
    )
    path = Path(__file__).parent.parent / 'auth_templates'
    admin.add_view(FileAdmin(path, '/authtemplates/', name='Modèles'))
