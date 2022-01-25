from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _



class GeneralConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'general'
    verbose_name = _("General")
