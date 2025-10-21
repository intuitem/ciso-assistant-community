from django.contrib.contenttypes.models import ContentType
from django.db import models

from core.base_models import AbstractBaseModel
from iam.models import FolderMixin


class IntegrationProvider(AbstractBaseModel):
    """Registry of available integration types"""

    class ProviderType(models.TextChoices):
        ITSM = "itsm"

    name = models.CharField(max_length=100)  # 'jira', 'servicenow', etc.
    provider_type = models.CharField(max_length=20, choices=ProviderType.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["name", "provider_type"]


class IntegrationConfiguration(AbstractBaseModel, FolderMixin):
    """Instance of an integration for a specific folder"""

    provider = models.ForeignKey(IntegrationProvider, on_delete=models.CASCADE)

    credentials = models.JSONField(default=dict)

    # Provider-specific settings
    settings = models.JSONField(default=dict)

    # Webhook configuration
    webhook_secret = models.CharField(max_length=255)
    webhook_url = models.URLField(blank=True)  # For registering with remote system

    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["provider", "folder"]


class SyncMapping(AbstractBaseModel):
    """Maps local objects to remote objects"""

    class SyncStatus(models.TextChoices):
        SYNCED = "synced"
        PENDING = "pending"
        FAILED = "failed"
        CONFLICT = "conflict"

    class SyncDirection(models.TextChoices):
        PUSH = "push"
        PULL = "pull"

    configuration = models.ForeignKey(
        IntegrationConfiguration, on_delete=models.CASCADE
    )

    # Local object reference
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE
    )  # e.g. core.AppliedControl
    local_object_id = models.UUIDField()

    # Remote object reference
    remote_id = models.CharField(max_length=255)  # Jira issue key, etc.
    remote_data = models.JSONField(default=dict)  # Cache of remote state

    # Sync metadata
    sync_status = models.CharField(
        max_length=20, choices=SyncStatus.choices, default=SyncStatus.SYNCED
    )
    last_synced_at = models.DateTimeField(auto_now=True)
    last_sync_direction = models.CharField(
        max_length=10, choices=SyncDirection.choices
    )  # 'push', 'pull'
    version = models.IntegerField(default=1)  # For optimistic locking
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ["configuration", "content_type", "local_object_id"]
        indexes = [
            models.Index(fields=["configuration", "remote_id"]),
        ]


class SyncEvent(models.Model):
    """Audit trail of sync operations"""

    class TriggeredBy(models.TextChoices):
        USER = "user"
        WEBHOOK = "webhook"
        SCHEDULED = "scheduled"

    mapping = models.ForeignKey(SyncMapping, on_delete=models.CASCADE)
    direction = models.CharField(
        max_length=10, choices=SyncMapping.SyncDirection.choices
    )

    changes = models.JSONField()  # What changed
    triggered_by = models.CharField(
        max_length=50, choices=TriggeredBy.choices
    )  # 'user', 'webhook', 'scheduled'

    success = models.BooleanField(default=True)
    error_details = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
