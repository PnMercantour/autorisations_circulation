
from pypnusershub.routes import check_auth

from flask_admin.contrib.sqla import ModelView


# Create customized model view class
class AuthenticatedModelView(ModelView):

    column_exclude_list = form_excluded_columns = ('created', 'updated')

    @check_auth(
        3,
        redirect_on_expiration="/?next=/admin",
        redirect_on_invalid_token="/?next=/admin"
    )
    def _handle_view(self, name, **kwargs):
        return super()._handle_view(name, **kwargs)
