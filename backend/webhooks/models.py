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

    class Kind(models.TextChoices):
        INTEGRATION = "integration", "Integration"
        AUDIT_SINK = "audit_sink", "Audit sink"

    class Transport(models.TextChoices):
        HTTP = "http", "HTTP"
        KAFKA = "kafka", "Kafka"
        SYSLOG = "syslog", "Syslog"

    class BodyFormat(models.TextChoices):
        CISO_NATIVE = "ciso_native", "CISO Assistant (HMAC-signed)"
        OCSF = "ocsf", "OCSF"
        RAW = "raw", "Raw LogEntry"
        CEF = "cef", "CEF"
        LEEF = "leef", "LEEF"

    payload_format = models.CharField(
        verbose_name="Payload Format",
        max_length=10,
        choices=PayloadFormats.choices,
        default=PayloadFormats.FULL,
        help_text="The format of the webhook payload sent to this endpoint.",
    )

    # An "audit_sink" forwards the audit log (LogEntry stream) to an external
    # SIEM; an "integration" is the user-facing model-event webhook. Audit sinks
    # are admin/org-managed and hidden from the user webhook list.
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.INTEGRATION,
    )
    transport = models.CharField(
        max_length=10,
        choices=Transport.choices,
        default=Transport.HTTP,
        help_text="Delivery transport (audit sinks only). Kafka is not yet implemented.",
    )
    body_format = models.CharField(
        max_length=20,
        choices=BodyFormat.choices,
        default=BodyFormat.OCSF,
        help_text="Canonical event schema for audit sinks.",
    )
    headers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Static headers added to each request, e.g. "
        '{"Authorization": "Splunk <token>"}. Used for audit-sink auth.',
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
        max_length=512,
        blank=True,
        default="",
        help_text="Consumer URL (HTTP transport).",
    )

    kafka_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Kafka transport: {bootstrap_servers, topic, config:{...}}.",
    )

    syslog_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Syslog transport: {host, port, protocol: tcp|udp|tls}.",
    )

    secret = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="HMAC signing secret (integration webhooks only).",
    )

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
        if self.transport != self.Transport.HTTP:
            return
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
