from django.apps import AppConfig


class WebhooksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "webhooks"

    def ready(self):
        from . import signals  # noqa: F401  connects the audit-log forwarding receiver
