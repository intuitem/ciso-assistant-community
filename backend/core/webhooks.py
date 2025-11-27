from webhooks.registry import webhook_registry
from .models import (
    AppliedControl,
    Asset,
    Finding,
    Incident,
    RiskAcceptance,
    SecurityException,
    TimelineEntry,
    Vulnerability,
)


webhook_registry.register(AppliedControl)
webhook_registry.register(Asset)
webhook_registry.register(Incident)
webhook_registry.register(TimelineEntry)
webhook_registry.register(RiskAcceptance)
webhook_registry.register(SecurityException)
webhook_registry.register(Finding)
webhook_registry.register(Vulnerability)
