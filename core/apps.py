from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = _("Core")



