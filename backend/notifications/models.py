from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel
from iam.models import Folder, User


class Notification(AbstractBaseModel):
    """A row in a user's inbox. `type` is the notification type, identical to the
    email template key; its registry entry declares how the row behaves (docs).

    Not registered with auditlog: highest-volume table in the product, and `is_read`
    is telemetry, never evidence.
    """

    # Access is `recipient` and nothing else (docs §5): folder RBAC is replaced here,
    # not composed with.
    IAM_SCOPE_FIELD = Folder.IAM_NOT_IMPLEMENTED

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )
    type = models.CharField(max_length=100, db_index=True, verbose_name=_("Type"))

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, verbose_name=_("Target type")
    )
    object_id = models.UUIDField(verbose_name=_("Target id"))
    target = GenericForeignKey("content_type", "object_id")

    # The variables the title renders from. The title itself is not stored: rendering
    # it client-side keeps it in the viewer's language, not the firing one.
    context = models.JSONField(default=dict, blank=True, verbose_name=_("Context"))

    # How many inbox rows the same fire wrote for this target: "am I the only one on
    # this". Counts Users who got a row, so a team's shared mailbox is not in it, and
    # neither are third-party recipients. Refreshed on every re-fire.
    recipient_count = models.PositiveIntegerField(
        default=1, verbose_name=_("Recipients")
    )

    is_read = models.BooleanField(default=False, verbose_name=_("Read"))
    # `updated_at` cannot stand in: a nightly sweep touches it on every condition row.
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Read at"))

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

    @property
    def folder(self):
        """The target's domain, derived rather than stored -- nothing gates on it, and
        a copy would go stale the moment the object moved domain.

        Not queryable: a GenericForeignKey cannot be joined, so ordering is impossible
        and filtering resolves the other way round (see NotificationViewSet).
        """
        target = self.target
        return Folder.get_folder(target) if target is not None else None

    @classmethod
    def set_read(cls, queryset, is_read: bool) -> int:
        """Flip read state, stamping `read_at` only on an actual transition: marking an
        already-read row read again keeps its original timestamp.

        One place for it because three paths do it -- detail PATCH, batch bar, event
        re-fire.
        """
        if is_read:
            return queryset.filter(is_read=False).update(
                is_read=True, read_at=timezone.now()
            )
        return queryset.update(is_read=False, read_at=None)

    def get_scope(self):
        """Overridden because `folder` here is a property: AbstractBaseModel.get_scope
        would filter on a column this model does not have. Uniqueness is the database
        constraint, not a name within a domain.
        """
        return self.__class__.objects.none()

    def __str__(self) -> str:
        return f"{self.type} ({self.recipient_id})"
