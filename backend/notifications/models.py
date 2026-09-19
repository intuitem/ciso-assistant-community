from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel
from iam.models import FolderMixin, User


class Notification(AbstractBaseModel, FolderMixin):
    """
    A row in a user's inbox. `type` is the notification type, identical to the
    email template key, and the registry entry for it declares how the row
    behaves (see docs/notification_center_shaping.md).

    Deliberately not registered with auditlog: this is the highest-volume table
    in the product and `is_read` is telemetry, never evidence.
    """

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )
    type = models.CharField(max_length=100, db_index=True, verbose_name=_("Type"))
    title = models.CharField(max_length=255, verbose_name=_("Title"))

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, verbose_name=_("Target type")
    )
    object_id = models.UUIDField(verbose_name=_("Target id"))
    target = GenericForeignKey("content_type", "object_id")

    # The variables the title renders from, so the frontend can re-render it in the
    # viewer's current language instead of the one frozen at write time. `title` stays
    # as the written-once fallback: it keeps server-side search working and still
    # renders if a type or its message is unknown to the client.
    context = models.JSONField(default=dict, blank=True, verbose_name=_("Context"))

    is_read = models.BooleanField(default=False, verbose_name=_("Read"))

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "type", "content_type", "object_id"],
                name="notification_unique_per_target",
            )
        ]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return self.title
