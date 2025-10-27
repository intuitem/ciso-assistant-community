from django.apps import AppConfig
from django.db.models.signals import post_migrate
import os
import importlib

from .startup import startup


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"

    def ready(self):
        # Avoid post_migrate handler if we are in the main, as it interferes with restore
        if not os.environ.get("RUN_MAIN"):
            post_migrate.connect(startup, sender=self)
        # Import webhooks to register webhook notification handlers
        importlib.import_module(f"{self.name}.webhooks")
