"""
Policy Aggregate

Represents a policy in the control library.
"""

import uuid
from typing import Optional
from datetime import date
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    PolicyCreated,
    PolicyPublished,
    PolicyRetired,
)


class Policy(AggregateRoot):
    """
    Policy aggregate root.
    
    Represents a policy with embedded ID arrays for relationships.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        RETIRED = "retired", "Retired"
    
    # Basic fields
    title = models.CharField(max_length=255, db_index=True)
    version = models.CharField(max_length=50, default="1.0", db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    ownerUserIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of owner user IDs"
    )
    relatedControlIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of related control IDs"
    )
    applicableOrgUnitIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of applicable organizational unit IDs"
    )
    
    # Dates
    publication_date = models.DateField(null=True, blank=True, db_index=True)
    review_cadence_days = models.IntegerField(null=True, blank=True, help_text="Days between reviews")
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "control_library_policies"
        verbose_name = "Policy"
        verbose_name_plural = "Policies"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["title", "version"]),
            models.Index(fields=["publication_date"]),
        ]
    
    def create(self, title: str, version: str = "1.0", description: str = None,
               publication_date: Optional[date] = None, review_cadence_days: Optional[int] = None):
        """
        Create a new policy.
        
        Domain method that enforces business rules and raises events.
        """
        self.title = title
        self.version = version
        self.description = description
        self.publication_date = publication_date
        self.review_cadence_days = review_cadence_days
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = PolicyCreated()
        event.payload = {
            "title": title,
            "version": version,
        }
        self._raise_event(event)
    
    def publish(self, publication_date: Optional[date] = None):
        """Publish the policy"""
        if self.lifecycle_state != self.LifecycleState.PUBLISHED:
            if publication_date:
                self.publication_date = publication_date
            elif not self.publication_date:
                from django.utils import timezone
                self.publication_date = timezone.now().date()
            
            self.lifecycle_state = self.LifecycleState.PUBLISHED
            
            event = PolicyPublished()
            event.payload = {
                "policy_id": str(self.id),
                "title": self.title,
                "version": self.version,
                "publication_date": str(self.publication_date),
            }
            self._raise_event(event)
    
    def retire(self):
        """Retire the policy"""
        if self.lifecycle_state != self.LifecycleState.RETIRED:
            self.lifecycle_state = self.LifecycleState.RETIRED
            
            event = PolicyRetired()
            event.payload = {
                "policy_id": str(self.id),
                "title": self.title,
                "version": self.version,
            }
            self._raise_event(event)
    
    def assign_owner(self, user_id: uuid.UUID):
        """Assign an owner to this policy"""
        if user_id not in self.ownerUserIds:
            self.ownerUserIds.append(user_id)
    
    def add_related_control(self, control_id: uuid.UUID):
        """Add a related control to this policy"""
        if control_id not in self.relatedControlIds:
            self.relatedControlIds.append(control_id)
    
    def add_applicable_org_unit(self, org_unit_id: uuid.UUID):
        """Add an applicable organizational unit"""
        if org_unit_id not in self.applicableOrgUnitIds:
            self.applicableOrgUnitIds.append(org_unit_id)
    
    def __str__(self):
        return f"{self.title} v{self.version}"

