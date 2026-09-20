from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.db.models import ForeignKey, OneToOneField
from rest_framework import serializers

from core.serializers import BaseModelSerializer
from iam.models import Folder
from notifications.models import Notification
from notifications.registry import NOTIFICATION_REGISTRY


def _folder_path(model) -> str | None:
    """The select_related path that pre-loads what Folder.get_folder will read.
    A model that reaches its domain some other way falls back to the per-object walk."""
    for candidate in ("folder", "parent_folder", "perimeter", "entity", "processing"):
        try:
            field = model._meta.get_field(candidate)
        except FieldDoesNotExist:
            continue
        if isinstance(field, (ForeignKey, OneToOneField)):
            return (
                candidate
                if candidate in ("folder", "parent_folder")
                else f"{candidate}__folder"
            )
    return None


class NotificationReadSerializer(BaseModelSerializer):
    target_model = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    folder = serializers.SerializerMethodField()

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
            "read_at",
            "folder",
            "created_at",
            "updated_at",
        ]

    def get_category(self, obj) -> str | None:
        """Read from the registry, not stored: a property of the type, not the row."""
        entry = NOTIFICATION_REGISTRY.get(obj.type)
        return entry["category"] if entry else None

    def get_folder(self, obj) -> dict | None:
        """The target's domain, derived rather than stored (see Notification.folder).
        Targets resolve once per page: a GenericForeignKey cannot be select_related."""
        target = self._targets().get((obj.content_type_id, obj.object_id))
        if target is None:
            return None
        folder = Folder.get_folder(target)
        return {"id": str(folder.id), "str": str(folder)} if folder else None

    def _targets(self) -> dict:
        if not hasattr(self, "_target_cache"):
            rows = self.instance if self.parent is None else self.parent.instance
            rows = (
                [] if rows is None else (rows if hasattr(rows, "__iter__") else [rows])
            )
            by_type: dict = {}
            for row in rows:
                by_type.setdefault(row.content_type_id, set()).add(row.object_id)
            resolved: dict = {}
            for content_type_id, ids in by_type.items():
                model = ContentType.objects.get_for_id(content_type_id).model_class()
                if model is None:
                    continue
                queryset = model.objects.filter(pk__in=ids)
                if path := _folder_path(model):
                    # Without this, get_folder walks obj.folder once per row -- and the
                    # inbox is not paginated (PAGE_SIZE 5000).
                    queryset = queryset.select_related(path)
                for obj in queryset:
                    resolved[(content_type_id, obj.pk)] = obj
            self._target_cache = resolved
        return self._target_cache

    def get_target_model(self, obj) -> str:
        """Django model name; crud.ts maps it to a route through
        urlModelForDjangoName(). get_for_id is process-cached, so this costs no query."""
        return ContentType.objects.get_for_id(obj.content_type_id).model


class NotificationWriteSerializer(BaseModelSerializer):
    """`is_read` is the whole write surface. Notifications are system-generated:
    a writable `recipient` would let a user forge one for someone else."""

    class Meta:
        model = Notification
        fields = ["is_read"]

    def update(self, instance, validated_data):
        """Through set_read so `read_at` is stamped exactly as for the batch bar."""
        if "is_read" in validated_data:
            Notification.set_read(
                Notification.objects.filter(pk=instance.pk), validated_data["is_read"]
            )
            instance.refresh_from_db()
            validated_data.pop("is_read")
        return super().update(instance, validated_data)

    def _check_object_perm(self, *args, **kwargs) -> None:
        """No-op: the inbox is scoped on `recipient`, not on the target's folder. The
        inherited check would 403 a user marking their own notification read in a
        domain where they hold no role; the recipient-scoped queryset is the check."""
