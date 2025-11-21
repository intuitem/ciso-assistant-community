from webhooks.registry import webhook_registry
from .models import AppliedControl, Asset


webhook_registry.register(AppliedControl)
webhook_registry.register(Asset)
