from webhooks.registry import webhook_registry
from .models import (
    AppliedControl,
    Finding,
    Evidence,
    EvidenceRevision,
)


webhook_registry.register(AppliedControl)
webhook_registry.register(Finding)
webhook_registry.register(Evidence)
webhook_registry.register(EvidenceRevision)
