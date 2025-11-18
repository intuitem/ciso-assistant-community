from django.db import transaction
from .models import WebhookEndpoint
from .registry import webhook_registry
from .tasks import send_webhook_request


def dispatch_webhook_event(instance, action):
    """
    Main service function called by views.

    - 'instance' is the model object (e.g., an AppliedControl)
    - 'action' is a string (e.g., "created", "updated", "deleted")
    """

    # Check if the model is registered
    config = webhook_registry.get_config(instance)

    if not config:
        return  # This model isn't tracked, do nothing

    # Get the event details from its config
    event_type = config.get_event_type(instance, action)
    data_payload = config.get_payload(instance)

    # Find all active endpoints subscribed to this event
    endpoints = WebhookEndpoint.objects.filter(
        is_active=True, event_types__name=event_type
    )

    # Enqueue tasks
    for endpoint in endpoints:
        transaction.on_commit(
            (
                lambda e_id=endpoint.id: send_webhook_request.schedule(
                    args=(e_id, event_type, data_payload), delay=1
                )
            )
        )
