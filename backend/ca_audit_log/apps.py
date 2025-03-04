import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CaAuditLogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ca_audit_log"

    def ready(self):
        logger.info("Initializing CaAuditLogConfig")
        # Import the signals module to connect the signal handlers
        try:
            import ca_audit_log.signals

            logger.info("Imported signals module successfully")
        except Exception as e:
            logger.error(f"Error importing signals: {e}", exc_info=True)

        # Register models to audit
        try:
            from ca_audit_log.registry import audit_registry
            from core.models import AppliedControl

            # Register models with specific operations to audit
            audit_registry.register(
                AppliedControl
            )  # Track all operations (C, U, D by default)
            logger.info(f"Registered AppliedControl with audit registry")

            # Debug output of registry contents
            logger.info(f"Audit registry contents: {audit_registry._registry}")
        except Exception as e:
            logger.error(f"Error registering models: {e}", exc_info=True)
