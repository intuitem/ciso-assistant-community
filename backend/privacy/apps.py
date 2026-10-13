from django.apps import AppConfig


class PrivacyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "privacy"

    def ready(self):
        # Registers the `processing.dpia_required` and `processing.dpia` targets.
        from privacy import dpia, screening  # noqa: F401
