from django.apps import AppConfig
from django.db.models.signals import post_migrate
import os

from .startup import startup, sync_builtin_role_permissions


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"

    def ready(self):
        # This import runs the @webhook_registry.register decorator
        import core.webhooks
        import core.mappings.signals

        # avoid post_migrate handler if we are in the main, as it interferes with restore
        if not os.environ.get("RUN_MAIN"):
            post_migrate.connect(startup, sender=self)
            # No sender filter: this fires after every app's post_migrate so
            # the *last* invocation picks up permissions for apps positioned
            # after `core` in INSTALLED_APPS (e.g. `integrations`,
            # `webhooks`). See sync_builtin_role_permissions docstring.
            post_migrate.connect(sync_builtin_role_permissions)
