from django.apps import AppConfig


class AutomationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "automation"

    def ready(self):
        # Internal-event trigger producer: mirror auditlog LogEntry
        # rows into workflow event dispatch, same hook as webhooks/signals.py.
        from auditlog.models import LogEntry
        from django.db.models.signals import post_save

        from .workflows.events import forward_log_entry

        post_save.connect(
            forward_log_entry,
            sender=LogEntry,
            dispatch_uid="automation_internal_event_producer",
        )
