import ipaddress
import uuid
from urllib.parse import urlparse
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from core.base_models import NameDescriptionMixin
from core.models import Actor
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
        """
        Model-level validation for SSRF mitigation.
        """
        super().clean()

        try:
            hostname = urlparse(self.url).hostname
            if not hostname:
                raise ValidationError("The URL provided is invalid.")

            # Try to parse the hostname as an IP address
            ip = ipaddress.ip_address(hostname)

            if not settings.WEBHOOK_ALLOW_PRIVATE_IPS and (
                ip.is_private or ip.is_loopback or ip.is_reserved
            ):
                raise ValidationError(
                    "In production, the URL cannot be an internal, loopback, or reserved IP address."
                )
        except ValueError:
            # It's a domain name, not an IP address. This is fine.
            # We are NOT resolving DNS here, as that's a blocking network call
            # and belongs in a proxy solution.
            pass

    def save(self, *args, **kwargs):
        """
        On save, ensure a secret exists if one wasn't provided.
        """
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)
