from webhooks.registry import webhook_registry
from webhooks.config import WebhookConfigBase
from .models import AppliedControl  # Assuming this is the correct import


@webhook_registry.register(AppliedControl)
class AppliedControlWebhookConfig(WebhookConfigBase):
    """
    Webhook configuration for the AppliedControl model.
    """

    def get_event_type(self, instance, action):
        """
        Returns "appliedcontrol.created", "appliedcontrol.updated", etc.
        """
        return f"appliedcontrol.{action}"

    def get_payload(self, instance):
        """
        Returns the "thin" payload with just the ID.
        """
        return {"id": str(instance.id)}

    def get_event_types(self):
        """
        Returns all possible events for the UI.
        """
        return [
            "appliedcontrol.created",
            "appliedcontrol.updated",
            "appliedcontrol.deleted",
        ]
