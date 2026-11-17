from django.apps import AppConfig


class TprmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tprm"

    def ready(self):
        # Registers the `entity.tier` apply-on-accept target.
        from tprm import tier_target  # noqa: F401
