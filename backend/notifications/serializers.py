from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from core.serializers import BaseModelSerializer
from notifications.models import Notification
from notifications.registry import NOTIFICATION_REGISTRY


class NotificationReadSerializer(BaseModelSerializer):
    target_model = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "category",
            "context",
            "content_type",
            "target_model",
            "object_id",
            "is_read",
            "created_at",
            "updated_at",
        ]

    def get_category(self, obj) -> str | None:
        """A property of the type, not of the row (docs §6), so it is read from the
        registry rather than stored — recategorising stays a dict edit."""
        entry = NOTIFICATION_REGISTRY.get(obj.type)
        return entry["category"] if entry else None

    def get_target_model(self, obj) -> str:
        """Django model name, which the frontend maps to a route segment through
        urlModelForDjangoName() in crud.ts. get_for_id is process-cached, so this
        costs no query."""
        return ContentType.objects.get_for_id(obj.content_type_id).model


class NotificationWriteSerializer(BaseModelSerializer):
    """`is_read` is the whole write surface. Notifications are system-generated:
    a writable `recipient` would let a user forge one for someone else."""

    class Meta:
        model = Notification
        fields = ["is_read"]

    def _check_object_perm(self, *args, **kwargs) -> None:
        """No-op: the inbox is scoped on `recipient`, not on the target's folder.

        BaseModelSerializer checks `change_/delete_notification` against
        Folder.get_folder(obj) on update and destroy, which 403s a user marking
        their own notification read in a domain where they hold no role. The
        recipient-scoped queryset in NotificationViewSet is the access check.
        """
