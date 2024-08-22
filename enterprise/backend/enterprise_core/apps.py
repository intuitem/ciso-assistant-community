from django.apps import AppConfig
from django.db.models.signals import post_migrate
import os

ADMINISTRATOR_PERMISSIONS = [
    "view_clientsettings",
    "change_clientsettings",
]


def startup(sender, **kwargs):
    from .models import ClientSettings
    from iam.models import Role
    from django.contrib.auth.models import Permission

    ClientSettings.objects.get_or_create()
    administrator_permissions = Permission.objects.filter(
        codename__in=ADMINISTRATOR_PERMISSIONS
    )
    administrator = Role.objects.get(name="BI-RL-ADM", builtin=True)
    for p in administrator_permissions:
        administrator.permissions.add(p)


class EnterpriseCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "enterprise_core"
    label = "enterprise_core"

    def ready(self):
        # avoid post_migrate handler if we are in the main, as it interferes with restore
        if not os.environ.get("RUN_MAIN"):
            post_migrate.connect(startup, sender=self)
