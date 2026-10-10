from django.apps import AppConfig


class MetrologyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "metrology"

    def ready(self):
        from . import signals  # noqa: F401 (connects the receivers)
