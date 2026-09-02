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

    from global_settings.models import GlobalSettings

    ff, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    # A legacy row may carry value=None; normalise before membership checks so
    # enterprise boot never crashes. The "not in" test still preserves an
    # admin's explicit False.
    if not isinstance(ff.value, dict):
        ff.value = {}
    value_changed = False
    for enterprise_flag in ("idp_groups", "service_accounts"):
        if enterprise_flag not in ff.value:
            ff.value[enterprise_flag] = False
            value_changed = True
    if value_changed:
        ff.save(update_fields=["value"])

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
        import enterprise_core.signals

        # avoid post_migrate handler if we are in the main, as it interferes with restore
        if not os.environ.get("RUN_MAIN"):
            post_migrate.connect(startup, sender=self)
