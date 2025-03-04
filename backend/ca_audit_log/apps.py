from django.apps import AppConfig


class CaAuditLogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ca_audit_log"

    def ready(self):
        from ca_audit_log.registry import audit_registry
        from core.models import AppliedControl

        # Register models with specific operations to audit
        audit_registry.register(
            AppliedControl
        )  # Track all operations (C, U, D by default)
