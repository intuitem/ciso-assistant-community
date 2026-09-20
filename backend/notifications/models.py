from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel
from iam.models import Folder, User


class Notification(AbstractBaseModel):
    """
    A row in a user's inbox. `type` is the notification type, identical to the
    email template key, and the registry entry for it declares how the row
    behaves (see docs/notification_center_shaping.md).

    Deliberately not registered with auditlog: this is the highest-volume table
    in the product and `is_read` is telemetry, never evidence.
    """

    # Access is `recipient` and nothing else (docs §5); folder RBAC is replaced
    # rather than composed with, so the IAM is genuinely not implemented here.
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

    # The variables the row's title renders from. The title itself is not stored: it
    # is a presentation concern, rendered client-side from the message catalogs in
    # whatever language the viewer is using. Storing it would freeze the language at
    # write time and duplicate 25 locales' worth of strings the product already has.
    context = models.JSONField(default=dict, blank=True, verbose_name=_("Context"))

    is_read = models.BooleanField(default=False, verbose_name=_("Read"))
    # When it was read, for people who want to see it; never load-bearing. `updated_at`
    # cannot stand in: a nightly sweep touches that on every condition row.
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
        """The domain this notification is about, read from the target rather than
        stored.

        A denormalised copy went stale the moment an object moved domain, and nothing
        here gates on it — so deriving costs a lookup and removes a whole class of
        drift. `Folder.get_folder` tries `["folder"]` first, so this also makes the
        generic helper work on a Notification.

        Not queryable: a GenericForeignKey cannot be joined, so ordering by it is not
        possible and filtering resolves the other way round (see NotificationViewSet).
        """
        target = self.target
        return Folder.get_folder(target) if target is not None else None

    @classmethod
    def set_read(cls, queryset, is_read: bool) -> int:
        """Flip read state on a queryset, keeping `read_at` honest.

        The single place this transition happens, because it happens on three paths —
        the detail PATCH, the batch bar, and an event re-firing — and a rule applied in
        two of three would be worse than no rule.

        Only a transition stamps: marking an already-read row read again leaves its
        original timestamp alone, which is what "when did I read this" means.
        """
        if is_read:
            return queryset.filter(is_read=False).update(
                is_read=True, read_at=timezone.now()
            )
        return queryset.update(is_read=False, read_at=None)

    def get_scope(self):
        """Uniqueness scope, overridden because `folder` here is a property.

        AbstractBaseModel.get_scope checks `hasattr(self, "folder")` and then filters
        on it, which would build a query against a column this model does not have.
        There is nothing to scope anyway: uniqueness is the database constraint on
        (recipient, type, content_type, object_id), not a name within a domain — and
        this runs on every save of the highest-volume table in the product.
        """
        return self.__class__.objects.none()

    def __str__(self) -> str:
        return f"{self.type} ({self.recipient_id})"
