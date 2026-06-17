from django.utils.dateparse import parse_datetime
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response

from global_settings.utils import ff_is_enabled

from .models import WebhookEndpoint, WebhookEventType
from .serializers import AuditSinkSerializer, WebhookEndpointSerializer
from .tasks import replay_audit_to_sink
from core.views import BaseModelViewSet


class WebhookEndpointViewSet(BaseModelViewSet):
    """
    API endpoint to create, list, retrieve, update, and delete
    Webhook Endpoints.
    """

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    model = WebhookEndpoint
    ordering_fields = ["is_active", "created_at", "name", "url"]
    ordering = ["-is_active", "-created_at"]

    def get_serializer_class(self, **kwargs):
        return WebhookEndpointSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        """
        Users can only see their own integration webhook endpoints. Audit sinks
        (kind=AUDIT_SINK) are admin-managed and excluded from this list.
        """
        return WebhookEndpoint.objects.filter(
            owner=self.request.user.actor,
            kind=WebhookEndpoint.Kind.INTEGRATION,
        )

    def perform_create(self, serializer):
        """
        Automatically assign the current user as the owner.
        """
        serializer.save(
            owner=self.request.user.actor,
            kind=WebhookEndpoint.Kind.INTEGRATION,
        )


class AuditSinkViewSet(BaseModelViewSet):
    """
    Admin-managed audit-log forwarding destinations (kind=AUDIT_SINK). Folder/IAM
    scoped via BaseModelViewSet (administrator-only, like all webhookendpoint
    perms) — not owner-scoped like integration webhooks.
    """

    model = WebhookEndpoint
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering_fields = ["is_active", "created_at", "name", "url"]
    ordering = ["-is_active", "-created_at"]

    def get_serializer_class(self, **kwargs):
        return AuditSinkSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        return super().get_queryset().filter(kind=WebhookEndpoint.Kind.AUDIT_SINK)

    def perform_create(self, serializer):
        serializer.save(
            owner=self.request.user.actor,
            kind=WebhookEndpoint.Kind.AUDIT_SINK,
        )

    @action(detail=True, methods=["post"])
    def replay(self, request, pk=None):
        """
        Re-emit historical audit events to this sink. Body: {since, until?} (ISO
        timestamps). Backfills a sink that was down — see replay_audit_to_sink.
        """
        if not ff_is_enabled("audit_log_forwarding"):
            return Response(
                {"error": "auditLogForwardingDisabled"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        endpoint = self.get_object()

        since = parse_datetime(request.data.get("since") or "")
        if not since:
            return Response(
                {"error": "sinceRequiredIso8601"}, status=status.HTTP_400_BAD_REQUEST
            )
        until = parse_datetime(request.data.get("until") or "")
        return Response(replay_audit_to_sink(endpoint, since, until))


class WebhookEventTypeView(APIView):
    """
    A read-only endpoint for the UI to fetch all possible
    event types from the registry.
    """

    def get(self, request, format=None):
        """
        Returns a list of all registered event type strings.
        """
        all_types = WebhookEventType.objects.values_list("name", flat=True).order_by(
            "name"
        )
        return Response(all_types)
