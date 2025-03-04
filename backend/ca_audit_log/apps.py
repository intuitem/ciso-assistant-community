from django.apps import AppConfig


class CaAuditLogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ca_audit_log"

    def ready(self):
        # Import the signals module to connect the signal handlers
        import ca_audit_log.signals
