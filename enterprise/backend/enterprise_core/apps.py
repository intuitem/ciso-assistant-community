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
    from structlog import get_logger

    logger = get_logger(__name__)

    try:
        ClientSettings.objects.get_or_create()

        administrator_permissions = Permission.objects.filter(
            codename__in=ADMINISTRATOR_PERMISSIONS
        )

        administrator, created = Role.objects.get_or_create(
            name="BI-RL-ADM", defaults={"builtin": True}
        )
        # Use set() to avoid duplicates instead of individual add() calls
        existing_perms = set(administrator.permissions.values_list("id", flat=True))
        new_perms = set(administrator_permissions.values_list("id", flat=True))
        if not new_perms.issubset(existing_perms):
            administrator.permissions.add(*administrator_permissions)
            logger.info("Added enterprise permissions to administrator role")
        if created:
            logger.info("Created administrator role BI-RL-ADM")
    except Exception as e:
        logger.error("Error in enterprise startup", exc_info=e)


class EnterpriseCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "enterprise_core"
    label = "enterprise_core"

    def ready(self):
        # avoid post_migrate handler if we are in the main, as it interferes with restore
        if not os.environ.get("RUN_MAIN"):
            post_migrate.connect(startup, sender=self)
