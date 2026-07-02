from django.apps import AppConfig
from django.core.management import call_command
from django.db.models.signals import post_migrate


def _sync_builtin_templates(sender, **kwargs):
    # Idempotent seed of built-in document templates; runs once per migrate
    # (not per-process, unlike AppConfig.ready()).
    try:
        call_command("sync_document_templates")
    except Exception:
        # Never block migrations on template seeding.
        pass


class DocManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "doc_management"
    verbose_name = "Document Management"

    def ready(self):
        post_migrate.connect(_sync_builtin_templates, sender=self)
