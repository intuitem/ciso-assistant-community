from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json


class AuditLog(models.Model):
    """
    Generic audit log model that tracks CRUD operations on monitored models.
    """

    OPERATION_CHOICES = (
        ("C", "Create"),
        ("U", "Update"),
        ("D", "Delete"),
    )

    # Auto-incrementing ID that can serve as a 64-bit counter
    id = models.BigAutoField(primary_key=True)

    # Timestamp when the operation occurred
    timestamp = models.DateTimeField(auto_now_add=True)

    # User who performed the operation
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Operation type (CRUD)
    operation = models.CharField(max_length=1, choices=OPERATION_CHOICES)

    # Generic foreign key to the affected object
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(
        max_length=255
    )  # Using CharField to support various ID types
    content_object = GenericForeignKey("content_type", "object_id")

    # Additional event data stored as JSON
    event_data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user"]),
            models.Index(fields=["operation"]),
        ]

    def __str__(self):
        operation_display = dict(self.OPERATION_CHOICES).get(
            self.operation, self.operation
        )
        model_name = (
            self.content_type.model_class().__name__ if self.content_type else "Unknown"
        )
        return f"{operation_display} on {model_name} #{self.object_id} by {self.user} at {self.timestamp}"
