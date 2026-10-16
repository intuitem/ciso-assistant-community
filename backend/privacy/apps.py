from django.apps import AppConfig


class PrivacyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "privacy"

    def ready(self):
        # Registers the processing targets and the facts forms can show.
        from privacy import dpia, facts, screening  # noqa: F401
