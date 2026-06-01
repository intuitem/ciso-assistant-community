import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from core.base_models import NameDescriptionMixin
from core.models import Actor
from core.net_safety import BlockedRequestError, assert_public_url
from iam.models import Folder, FolderMixin


class WebhookEventType(models.Model):
    """
    Represents a single, subscribable event type (e.g., "appliedcontrol.created").
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="The event type string, e.g., 'appliedcontrol.created'",
    )

    def __str__(self):
        return self.name


class WebhookEndpoint(NameDescriptionMixin, FolderMixin):
    """
    Represents a single consumer endpoint for receiving webhooks.
    """

    class PayloadFormats(models.TextChoices):
        THIN = "thin", "Thin"
        FULL = "full", "Full"

    payload_format = models.CharField(
        verbose_name="Payload Format",
        max_length=10,
        choices=PayloadFormats.choices,
        default=PayloadFormats.FULL,
        help_text="The format of the webhook payload sent to this endpoint.",
    )

    owner = models.ForeignKey(
        Actor,
        related_name="webhook_endpoints",
        on_delete=models.CASCADE,
        help_text="The actor that owns this endpoint.",
        blank=True,
        null=True,
    )

    url = models.URLField(
        max_length=512, help_text="The consumer URL to send webhook events to."
    )

    secret = models.CharField(max_length=100, help_text="HMAC signing secret.")

    event_types = models.ManyToManyField(
        WebhookEventType,
        blank=True,
        help_text="A list of event types this endpoint subscribes to.",
    )

    target_folders = models.ManyToManyField(
        Folder,
        blank=True,
        help_text="Folders to which this webhook endpoint is scoped. If empty, the endpoint applies to all folders the owner has access to.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Global toggle to enable/disable sending events to this endpoint.",
    )

    def __str__(self):
        return f"{self.owner} - {self.url}"

    def clean(self):
        super().clean()
        if getattr(settings, "WEBHOOK_ALLOW_PRIVATE_IPS", False):
            return
        try:
            assert_public_url(self.url, allowed_schemes=("http", "https"))
        except BlockedRequestError:
            raise ValidationError(
                {
                    "url": "URL must point to a public host "
                    "(no private, loopback, or internal addresses)."
                }
            )

    def save(self, *args, **kwargs):
        """
        On save, ensure a secret exists if one wasn't provided.
        """
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)
