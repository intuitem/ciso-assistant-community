import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CaAuditLogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ca_audit_log"

    def ready(self):
        try:
            import ca_audit_log.signals

            logger.info("Imported signals module successfully")
        except Exception as e:
            logger.error(f"Error importing signals: {e}", exc_info=True)

        # Register models to audit. Note to self: add the TrackFieldChanges Mixin to the model when relevant
        try:
            from ca_audit_log.registry import audit_registry
            from core.models import (
                AppliedControl,
                RequirementAssessment,
                RiskScenario,
                Finding,
            )

            # Register models with specific operations to audit
            audit_registry.register(AppliedControl)
            audit_registry.register(RequirementAssessment, ["C", "U"])
            audit_registry.register(RiskScenario)
            audit_registry.register(Finding)
        except Exception as e:
            logger.error(f"Error registering models: {e}", exc_info=True)
