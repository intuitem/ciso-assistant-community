from django.db import transaction
from django.db.models import Q, Count

from global_settings.utils import ff_is_enabled
from iam.models import Folder

from .models import WebhookEndpoint
from .registry import webhook_registry
from .tasks import send_webhook_request


def dispatch_webhook_event(instance, action, serializer=None):
    """
    Main service function called by views.

    - 'instance' is the model object (e.g., an AppliedControl)
    - 'action' is a string (e.g., "created", "updated", "deleted")
    """
    if not ff_is_enabled("outgoing_webhooks"):
        return
    # Check if the model is registered
    config = webhook_registry.get_config(instance)

    if not config:
        return  # This model isn't tracked, do nothing

    event_type = config.get_event_type(instance, action)

    # Find all active endpoints subscribed to this event
    folder = Folder.get_folder(instance)
    endpoints = (
        WebhookEndpoint.objects.annotate(folder_count=Count("target_folders"))
        .filter(
            Q(folder_count=0) | Q(target_folders=folder),
            is_active=True,
            event_types__name=event_type,
        )
        .distinct()
    )

    payloads = {}
    for endpoint in endpoints:
        _serializer = (
            serializer
            if endpoint.payload_format == WebhookEndpoint.PayloadFormats.FULL
            else None
        )
        payloads[str(endpoint.id)] = config.get_payload(instance, _serializer)

    # Enqueue tasks
    for endpoint in endpoints:
        transaction.on_commit(
            (
                lambda e_id=str(endpoint.id): send_webhook_request.schedule(
                    args=(e_id, event_type, payloads[e_id]), delay=1
                )
            )
        )
