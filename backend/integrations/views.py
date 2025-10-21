import json
import logging
import uuid

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from integrations.models import IntegrationConfiguration
from integrations.tasks import process_webhook_event

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class IntegrationWebhookView(View):
    """
    Receives, authenticates, and dispatches incoming webhooks
    from integration providers.

    This view is designed to be provider-agnostic. It uses a shared secret
    for authentication.
    """

    def post(
        self, request: HttpRequest, config_id: uuid.UUID, *args, **kwargs
    ) -> HttpResponse:
        # Find the configuration
        try:
            config = get_object_or_404(
                IntegrationConfiguration, pk=config_id, is_active=True
            )
        except Exception:
            logger.warning(
                f"Webhook received for unknown or inactive config ID: {config_id}"
            )
            return JsonResponse(
                {"error": "Configuration not found or inactive"}, status=404
            )

        # Authenticate the webhook
        # We use a shared secret token in a URL query parameter
        # Jira Webhook URL: https://.../webhook/<uuid>/?token=<secret>
        provided_token = request.GET.get("token")
        if not provided_token or not config.webhook_secret:
            logger.warning(f"Webhook for config {config_id} missing token or secret.")
            return JsonResponse({"error": "Authentication required"}, status=401)

        # Use a constant-time comparison for security
        import hmac

        if not hmac.compare_digest(provided_token, config.webhook_secret):
            logger.warning(f"Webhook for config {config_id} provided invalid token.")
            return JsonResponse({"error": "Invalid token"}, status=403)

        # Parse the payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning(f"Webhook for config {config_id} sent invalid JSON.")
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)

        # Extract provider-specific event type
        # For Jira, this is in the 'webhookEvent' field
        event_type = payload.get("webhookEvent")
        if not event_type:
            logger.warning(
                f"Webhook payload for config {config_id} missing 'webhookEvent' field."
            )
            return JsonResponse({"error": "Missing event type"}, status=400)

        # Dispatch to async task
        # We pass the config.id, not the object, as it's serializable.
        process_webhook_event.schedule(
            args=(config.id, event_type, payload),
            delay=1,  # Small delay to ensure DB transaction commits
        )

        # Return 202 Accepted immediately
        # This tells Jira we've received the event and it shouldn't retry.
        logger.info(f"Webhook event '{event_type}' for config {config_id} accepted.")
        return HttpResponse(status=202)
