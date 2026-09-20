import structlog
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from core.permissions import FeatureFlagRequired, IsGlobalAdmin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.views import BATCH_SIZE_LIMIT, BaseModelViewSet
from notifications.models import Notification
from notifications.channels import matrix, set_channel
from notifications.registry import NOTIFICATION_REGISTRY
from notifications.permissions import IsRecipient

logger = structlog.getLogger(__name__)


class NotificationViewSet(BaseModelViewSet):
    """The inbox. Scoped on `recipient` alone: `folder` is metadata, not an access
    gate, so the inherited folder-RBAC enforcement points are replaced (docs §5)."""

    model = Notification
    serializers_module = "notifications.serializers"
    permission_classes = [IsAuthenticated, IsRecipient, FeatureFlagRequired]
    feature_flag = "notification_centre"
    filterset_fields = ["is_read", "read_at", "type", "content_type"]
    # Titles render client-side, so there is no text column to search.
    search_fields = ["type"]
    # `folder` is derived, so it can be filtered (below) but never ordered by.
    ordering_fields = ["created_at", "updated_at", "read_at", "is_read", "type"]
    ordering = ["-created_at"]

    def get_queryset(self) -> models.query.QuerySet:
        # Not super().get_queryset(): that filters on the folders the user holds
        # view_notification in, which is empty for a recipient with no role there.
        queryset = Notification.objects.filter(recipient=self.request.user)

        # `category` is not a column, so it expands from the registry here.
        if category := self.request.query_params.get("category"):
            queryset = queryset.filter(
                type__in=[
                    key
                    for key, entry in NOTIFICATION_REGISTRY.items()
                    if entry["category"] == category
                ]
            )

        if folders := self.request.query_params.getlist("folder"):
            queryset = self._filter_by_folder(queryset, folders)

        return queryset

    def _filter_by_folder(self, queryset, folders):
        """Narrow to notifications whose *target* lives in one of these domains.

        The folder is derived, so this resolves backwards: per content type, ask that
        model which objects are in the domain, then match ids. One query per content
        type, and only on an explicit filter.
        """
        matched = Q(pk__in=[])
        content_type_ids = queryset.values_list("content_type", flat=True).distinct()
        for content_type_id in content_type_ids:
            model = ContentType.objects.get_for_id(content_type_id).model_class()
            if model is None or not hasattr(model, "folder"):
                continue
            ids = model.objects.filter(folder__in=folders).values_list("pk", flat=True)
            matched |= Q(content_type=content_type_id, object_id__in=list(ids))
        return queryset.filter(matched)

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    @action(detail=False, name="Read state choices")
    def is_read(self, request):
        """A plain boolean has no choices of its own; the batch modal needs a pair."""
        return Response({"true": "read", "false": "unread"})

    @action(detail=False, name="Category choices")
    def category(self, request):
        return Response(
            {
                key: key
                for key in sorted(
                    {
                        entry["category"]
                        for entry in NOTIFICATION_REGISTRY.values()
                        if "in_app" in entry["channels"]
                    }
                )
            }
        )

    def _unread_count(self) -> int:
        return self.get_queryset().filter(is_read=False).count()

    @action(detail=False, name="Unread count")
    def unread_count(self, request):
        return Response({"count": self._unread_count()})

    def partial_update(self, request, *args, **kwargs):
        """Answer with the new unread count: marking a row read from inside the inbox
        does not navigate, so the badge has no other cue until the next poll."""
        response = super().partial_update(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            response.data["unread_count"] = self._unread_count()
        return response

    @action(detail=False, methods=["post"], url_path="batch-action")
    def batch_action(self, request):
        """Narrower than the inherited version: the recipient-scoped queryset is the
        whole permission check, so an id the caller does not own is simply absent."""
        action_type = request.data.get("action")
        ids = request.data.get("ids", [])

        if action_type not in ("delete", "change_field"):
            return Response(
                {"error": "Invalid action type"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not ids:
            return Response(
                {"error": "No ids provided"}, status=status.HTTP_400_BAD_REQUEST
            )
        if len(ids) > BATCH_SIZE_LIMIT:
            return Response(
                {"error": "too many ids", "max": BATCH_SIZE_LIMIT},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action_type == "change_field" and request.data.get("field") != "is_read":
            return Response(
                {"error": "field not editable"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Same response shape as BaseModelViewSet.batch_action: lists, not counts.
        rows = {str(n.id): n for n in self.get_queryset().filter(id__in=ids)}
        succeeded = [{"id": str(n.id), "name": str(n)} for n in rows.values()]
        failed = [
            {"id": str(i), "error": "Object not found or access denied"}
            for i in ids
            if str(i) not in rows
        ]

        if rows:
            queryset = self.get_queryset().filter(id__in=list(rows))
            if action_type == "delete":
                queryset.delete()
            else:
                # The modal posts "true"/"false" as a string, and bool("false") is True.
                raw = request.data.get("value")
                is_read = (
                    raw if isinstance(raw, bool) else str(raw).strip().lower() == "true"
                )
                Notification.set_read(queryset, is_read)

        logger.info(
            "Notification batch action",
            action=action_type,
            requested=len(ids),
            succeeded=len(succeeded),
            failed=len(failed),
            user=request.user.id,
        )
        return Response(
            {
                "succeeded": succeeded,
                "failed": failed,
                "unread_count": self._unread_count(),
            }
        )


class NotificationChannelsView(APIView):
    """The admin channel matrix (§7)."""

    permission_classes = [IsAuthenticated, IsGlobalAdmin]

    def get(self, request):
        return Response(matrix())

    def post(self, request):
        try:
            set_channel(
                request.data.get("type"),
                request.data.get("channel"),
                bool(request.data.get("enabled")),
            )
        except ValueError as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(matrix())
