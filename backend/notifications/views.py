import structlog
from django.db import models
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.views import BATCH_SIZE_LIMIT, BaseModelViewSet
from notifications.models import Notification
from notifications.registry import NOTIFICATION_REGISTRY
from notifications.permissions import IsRecipient

logger = structlog.getLogger(__name__)


class NotificationViewSet(BaseModelViewSet):
    """
    The inbox. Scoped on `recipient` alone — `folder` is metadata here, not an
    access gate, so all three of the inherited folder-RBAC enforcement points are
    replaced rather than composed with (docs/notification_center_shaping.md §5).
    """

    model = Notification
    serializers_module = "notifications.serializers"
    permission_classes = [IsAuthenticated, IsRecipient]
    filterset_fields = ["is_read", "type", "folder", "content_type"]
    # Titles are rendered client-side, so there is no text column to search. `type`
    # keeps the search box functional (it matches the type key); the real filters are
    # read state and category.
    search_fields = ["type"]
    ordering = ["-created_at"]

    def get_queryset(self) -> models.query.QuerySet:
        # Deliberately not super().get_queryset(): that filters on the folders the
        # user holds view_notification in, which returns nothing for a recipient
        # who holds no role in the target's domain.
        queryset = Notification.objects.filter(recipient=self.request.user)

        # `category` groups types; it is not a column, so it expands here rather than
        # in filterset_fields. Keeps the vocabulary in the registry (docs §7).
        if category := self.request.query_params.get("category"):
            queryset = queryset.filter(
                type__in=[
                    key
                    for key, entry in NOTIFICATION_REGISTRY.items()
                    if entry["category"] == category
                ]
            )
        return queryset

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    @action(detail=False, name="Read state choices")
    def is_read(self, request):
        """Options for the batch bar's read/unread action. A plain boolean has no
        choices of its own, and the batch modal needs a labelled pair."""
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

    @action(detail=False, name="Unread count")
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(is_read=False).count()})

    @action(detail=False, methods=["post"], url_path="batch-action")
    def batch_action(self, request):
        """
        Narrower than the inherited version, which re-checks every object against
        folder RBAC independently of the queryset. Here the recipient-scoped queryset
        is the whole permission check: an id the caller does not own is simply absent.
        """
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

        # Same response shape as BaseModelViewSet.batch_action: the batch bar reads
        # `succeeded`/`failed` as lists and reports their lengths.
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
                # The modal posts the config's value, so it arrives as the string
                # "true"/"false". bool("false") is True, which would silently mark
                # everything read when the user asked for the opposite.
                raw = request.data.get("value")
                is_read = (
                    raw if isinstance(raw, bool) else str(raw).strip().lower() == "true"
                )
                queryset.update(is_read=is_read)

        logger.info(
            "Notification batch action",
            action=action_type,
            requested=len(ids),
            succeeded=len(succeeded),
            failed=len(failed),
            user=request.user.id,
        )
        return Response({"succeeded": succeeded, "failed": failed})
