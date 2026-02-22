import json
import uuid

import structlog
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from iam.models import Folder, RoleAssignment
from integrations.models import (
    IntegrationConfiguration,
    IntegrationProvider,
    SyncMapping,
)
from integrations.registry import IntegrationRegistry
from integrations.serializers import (
    ConnectionTestSerializer,
    IntegrationConfigurationSerializer,
    IntegrationProviderSerializer,
    SyncMappingSerializer,
)
from integrations.tasks import process_webhook_event

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
        provider = validated_data.get("provider")

        # Create a temporary, unsaved IntegrationConfiguration instance for the client
        temp_config = IntegrationConfiguration(
            provider=IntegrationProvider.objects.filter(name=provider).first(),
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
        except Exception:
            # An exception occurred, e.g., network error, invalid URL
            logger.error(
                "Test connection for provider raised an exception",
                provider=provider,
                exc_info=True,
            )
            return Response(
                {"status": "error", "message": "An unexpected error occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class IntegrationProviderListView(generics.ListAPIView):
    """
    An API endpoint to list all available (and active) Integration Providers.
    """

    queryset = IntegrationProvider.objects.filter(is_active=True)
    serializer_class = IntegrationProviderSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["provider_type", "name"]


class IntegrationConfigurationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for creating, viewing, updating, and deleting Integration Configurations.
    """

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    queryset = IntegrationConfiguration.objects.select_related(
        "provider", "folder"
    ).all()
    serializer_class = IntegrationConfigurationSerializer

    filterset_fields = ["provider", "provider__name", "provider__provider_type"]

    def get_queryset(self):
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
        except Exception:
            logger.error(
                "Test connection for config raised an exception",
                config_id=pk,
                exc_info=True,
            )
            return Response(
                {"status": "error", "message": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get"], url_path="remote-objects")
    def list_remote_objects(self, request, pk=None):
        instance = IntegrationConfiguration.objects.get(pk=pk)
        try:
            client = IntegrationRegistry.get_client(instance)
            remote_objects = client.list_remote_objects()
            return Response(remote_objects, status=status.HTTP_200_OK)
        except Exception:
            logger.error(
                "Listing remote objects for config raised an exception",
                config_id=pk,
                exc_info=True,
            )
            return Response(
                {"status": "error", "message": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="rpc")
    def execute_rpc(self, request, pk=None):
        """
        Generic endpoint for interactive integration commands.
        Payload: { "action": "get_tables", "params": { ... } }
        """
        config = self.get_object()

        action_name = request.data.get("action")
        params = request.data.get("params", {})

        if not action_name:
            return Response(
                {"error": "Action is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            orchestrator = IntegrationRegistry.get_orchestrator(config)

            result = orchestrator.execute_action(action_name, params)

            return Response({"result": result})

        except NotImplementedError:
            return Response(
                {
                    "error": f"Action '{action_name}' not supported by provider '{config.provider}'"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError:
            logger.warning(
                "ValueError while executing integration RPC action",
                action_name=action_name,
                config_id=config.pk,
                exc_info=True,
            )
            return Response(
                {"error": "Invalid request parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            # Catch connectivity errors from the client
            logger.error(
                "RPC execution for integration config raised an exception",
                config_id=pk,
                action_name=action_name,
                exc_info=True,
            )
            return Response(
                {
                    "error": "An unexpected error occurred while executing the requested action."
                },
                status=status.HTTP_502_BAD_GATEWAY,
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
            viewable_objects, _, _ = RoleAssignment.get_accessible_object_ids(
                folder=Folder.get_root_folder(),
                user=request.user,
                object_type=IntegrationConfiguration,
            )
            if config_id not in viewable_objects:
                return Response(status=status.HTTP_403_FORBIDDEN)
            config = get_object_or_404(
                IntegrationConfiguration, pk=config_id, is_active=True
            )
        except Exception:
            logger.warning(
                f"Webhook received for unknown or inactive config ID: {config_id}"
            )
            return JsonResponse({"error": "Configuration not found"}, status=404)

        # Instantiate the correct orchestrator
        try:
            orchestrator = IntegrationRegistry.get_orchestrator(config)
        except Exception as e:
            logger.error(f"Failed to load orchestrator for config {config_id}: {e}")
            return JsonResponse({"error": "Internal configuration error"}, status=500)

        # Delegate authentication/validation
        # The orchestrator checks headers, secrets, signatures etc.
        try:
            if not orchestrator.validate_webhook_request(request):
                return JsonResponse({"error": "Authentication failed"}, status=401)
        except Exception:
            logger.warning(
                "Webhook validation failed", config_id=config_id, exc_info=True
            )
            return JsonResponse({"error": "Webhook validation failed"}, status=403)

        # Parse payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)

        # Extract event type
        event_type = orchestrator.extract_webhook_event_type(payload)
        if not event_type:
            return JsonResponse({"error": "Could not determine event type"}, status=400)

        # 5. Dispatch to Huey
        process_webhook_event.schedule(args=(config.id, event_type, payload), delay=1)

        return HttpResponse(status=202)


class SyncMappingDeleteView(generics.DestroyAPIView):
    """
    An API endpoint to delete a SyncMapping.
    """

    serializer_class = SyncMappingSerializer

    def get_queryset(self):
        return SyncMapping.objects.all()
