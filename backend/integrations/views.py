import hashlib
import hmac
import json
import uuid

import structlog
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.models import IntegrationConfiguration, IntegrationProvider
from integrations.tasks import process_webhook_event

from .registry import IntegrationRegistry
from .serializers import (
    ConnectionTestSerializer,
    IntegrationConfigurationSerializer,
    IntegrationProviderSerializer,
)

logger = structlog.get_logger(__name__)


class ConnectionTestView(APIView):
    """
    An endpoint to test connection credentials without saving them.
    Accepts a POST request with provider_id and credentials.
    """

    def post(self, request, *args, **kwargs):
        serializer = ConnectionTestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        provider = validated_data.get("provider_id")

        # Create a temporary, unsaved IntegrationConfiguration instance for the client
        temp_config = IntegrationConfiguration(
            provider=provider,
            credentials=validated_data.get("credentials"),
            settings=validated_data.get("settings", {}),
        )

        try:
            # Use the registry to get the correct client implementation
            client = IntegrationRegistry.get_client(temp_config)
            is_connected = client.test_connection()

            if is_connected:
                return Response(
                    {"status": "success", "message": "Connection successful."},
                    status=status.HTTP_200_OK,
                )
            else:
                # The test_connection method returned False, implying a credential error
                return Response(
                    {
                        "status": "failure",
                        "message": "Connection failed. Please check credentials.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            # An exception occurred, e.g., network error, invalid URL
            logger.error(
                f"Test connection for provider {provider.name} raised an exception: {e}",
                exc_info=True,
            )
            return Response(
                {"status": "error", "message": f"An unexpected error occurred: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class IntegrationProviderListView(generics.ListAPIView):
    """
    An API endpoint to list all available (and active) Integration Providers.
    """

    queryset = IntegrationProvider.objects.filter(is_active=True)
    serializer_class = IntegrationProviderSerializer


class IntegrationConfigurationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for creating, viewing, updating, and deleting Integration Configurations.
    """

    queryset = IntegrationConfiguration.objects.select_related(
        "provider", "folder"
    ).all()
    serializer_class = IntegrationConfigurationSerializer

    def get_queryset(self):
        """
        **PLACEHOLDER FOR PERMISSIONS**:
        This is where you would filter the configurations based on the
        requesting user's access to the associated Folder.

        For example:
        user_folders = Folder.objects.filter(owner=self.request.user)
        return super().get_queryset().filter(folder__in=user_folders)
        """
        return super().get_queryset()

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        """
        Custom action to test the connection for a saved integration configuration.
        URL: /api/integrations/configs/{id}/test-connection/
        """
        logger.info(f"Testing connection for integration config: {pk}")
        instance = IntegrationConfiguration.objects.get(pk=pk)

        try:
            # Use the registry to get the correct client implementation
            client = IntegrationRegistry.get_client(instance)
            is_connected = client.test_connection()

            if is_connected:
                return Response(
                    {"status": "success", "message": "Connection successful."},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "status": "failure",
                        "message": "Connection failed. Please check credentials.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            logger.error(
                f"Test connection for config {pk} raised an exception: {e}",
                exc_info=True,
            )
            return Response(
                {"status": "error", "message": f"An unexpected error occurred: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
                f"Webhook for config {config_id} missing X-Hub-Signature header."
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
