"""
PolicyAcknowledgement Association

First-class association representing a user's acknowledgement of a policy.
"""

import uuid
from datetime import datetime
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from ..domain_events import (
    PolicyAcknowledged,
)


class PolicyAcknowledgement(AggregateRoot):
    """
    Policy Acknowledgement association.
    
    First-class entity representing a user's acknowledgement of a policy
    with version, date, and method tracking.
    """
    
    class Method(models.TextChoices):
        CLICKWRAP = "clickwrap", "Clickwrap"
        TRAINING = "training", "Training"
        DOC_SIGN = "doc_sign", "Document Signing"
    
    # Policy and user
    policyId = models.UUIDField(db_index=True)
    policy_version = models.CharField(max_length=50, db_index=True)
    userId = models.UUIDField(db_index=True)
    
    # Acknowledgement details
    acknowledged_at = models.DateTimeField(default=timezone.now, db_index=True)
    method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.CLICKWRAP,
        db_index=True
    )
    
    # Additional fields
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "control_library_policy_acknowledgements"
        verbose_name = "Policy Acknowledgement"
        verbose_name_plural = "Policy Acknowledgements"
        indexes = [
            models.Index(fields=["policyId", "userId"]),
            models.Index(fields=["acknowledged_at"]),
        ]
        unique_together = [
            ["policyId", "policy_version", "userId"]
        ]
    
    def acknowledge(self, policy_id: uuid.UUID, policy_version: str, user_id: uuid.UUID,
                    method: str = None, acknowledged_at: Optional[datetime] = None,
                    notes: str = None):
        """
        Create a policy acknowledgement.
        
        Domain method that enforces business rules and raises events.
        """
        self.policyId = policy_id
        self.policy_version = policy_version
        self.userId = user_id
        self.method = method or self.Method.CLICKWRAP
        self.acknowledged_at = acknowledged_at or timezone.now()
        self.notes = notes
        
        event = PolicyAcknowledged()
        event.payload = {
            "acknowledgement_id": str(self.id),
            "policy_id": str(policy_id),
            "policy_version": policy_version,
            "user_id": str(user_id),
            "method": self.method,
        }
        self._raise_event(event)
    
    def __str__(self):
        return f"Policy {self.policyId} v{self.policy_version} acknowledged by User {self.userId}"

