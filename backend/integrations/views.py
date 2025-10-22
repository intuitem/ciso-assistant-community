import hashlib
import json
import structlog
import uuid
import hmac

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions
from rest_framework.decorators import permission_classes

from integrations.models import IntegrationConfiguration
from integrations.tasks import process_webhook_event

logger = structlog.get_logger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class IntegrationWebhookView(View):
    """
    Receives, authenticates, and dispatches incoming webhooks
    from integration providers.

    This view is designed to be provider-agnostic. It uses a shared secret
    for authentication.
    """

    @permission_classes([permissions.AllowAny])
    def post(
        self, request: HttpRequest, config_id: uuid.UUID, *args, **kwargs
    ) -> HttpResponse:
        try:
            config = get_object_or_404(
                IntegrationConfiguration, pk=config_id, is_active=True
            )
        except Exception:
            logger.warning(
                f"Webhook received for unknown or inactive config ID: {config_id}"
            )
            return JsonResponse({"error": "Configuration not found"}, status=404)

        # Authenticate the webhook using HMAC Signature

        # Get the signature from the header (Jira uses X-Hub-Signature)
        signature_header = request.headers.get("X-Hub-Signature")

        if not signature_header:
            logger.warning(
                f"Webhook for config {config_id} missing X-Hub-Signature-256 header."
            )
            return JsonResponse(
                {"error": "Authentication required: Missing signature"}, status=401
            )

        if not config.webhook_secret:
            logger.error(f"Webhook secret not configured for config {config_id}.")
            return JsonResponse({"error": "Internal configuration error"}, status=500)

        # Extract the signature hash
        try:
            method, provided_signature = signature_header.split("=", 1)
            if method.lower() != "sha256":
                logger.warning(
                    "Unsupported signature method for config",
                    method=method,
                    config_id=config_id,
                )
                return JsonResponse(
                    {"error": "Unsupported signature method"}, status=400
                )
        except ValueError:
            logger.warning(f"Invalid signature header format for config {config_id}.")
            return JsonResponse({"error": "Invalid signature format"}, status=400)

        # Calculate the expected signature
        expected_signature = hmac.new(
            config.webhook_secret.encode("utf-8"),
            request.body,  # request.body is bytes
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures using a constant-time comparison
        if not hmac.compare_digest(provided_signature, expected_signature):
            logger.warning(f"Webhook signature mismatch for config {config_id}.")
            return JsonResponse({"error": "Invalid signature"}, status=403)

        # --- Signature is valid ---

        # Parse the payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning(f"Webhook for config {config_id} sent invalid JSON.")
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)

        # Extract provider-specific event type
        event_type = payload.get("webhookEvent")
        if not event_type:
            logger.warning(
                f"Webhook payload for config {config_id} missing 'webhookEvent' field."
            )
            return JsonResponse({"error": "Missing event type"}, status=400)

        # Dispatch to async task
        process_webhook_event.schedule(args=(config.id, event_type, payload), delay=1)

        logger.info(
            f"Webhook event '{event_type}' for config {config_id} accepted (signature validated)."
        )
        return HttpResponse(status=202)
