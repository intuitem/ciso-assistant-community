"""
BusinessRisk Aggregate

Represents a risk associated with business processes.
"""

import uuid
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    BusinessRiskCreated,
    BusinessRiskAssessed,
    BusinessRiskTreated,
    BusinessRiskAccepted,
    BusinessRiskClosed,
)


class BusinessRisk(AggregateRoot):
    """
    Business Risk aggregate root.
    
    Represents a risk associated with business processes and organizational units.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ASSESSED = "assessed", "Assessed"
        TREATED = "treated", "Treated"
        ACCEPTED = "accepted", "Accepted"
        CLOSED = "closed", "Closed"
    
    # Basic fields
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    processIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of process IDs"
    )
    orgUnitIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of organizational unit IDs"
    )
    controlImplementationIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of control implementation IDs"
    )
    exceptionIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of risk exception IDs"
    )
    
    # Risk scoring (stored as JSON for value object)
    scoring = models.JSONField(
        default=dict,
        blank=True,
        help_text="Risk scoring: likelihood, impact, inherent_score, residual_score, rationale"
    )
    
    # Treatment plan reference
    treatmentPlanId = models.UUIDField(null=True, blank=True, db_index=True)

    # Additional fields
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "risk_registers_business_risks"
        verbose_name = "Business Risk"
        verbose_name_plural = "Business Risks"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["title"]),
            models.Index(fields=["treatmentPlanId"]),
        ]
    
    def create(self, title: str, description: str = None):
        """
        Create a new business risk.
        
        Domain method that enforces business rules and raises events.
        """
        self.title = title
        self.description = description
        self.lifecycle_state = self.LifecycleState.DRAFT
        self.scoring = {
            "likelihood": 1,
            "impact": 1,
            "inherent_score": 1,
            "residual_score": 1,
            "rationale": None,
        }
        
        event = BusinessRiskCreated()
        event.payload = {
            "risk_id": str(self.id),
            "title": title,
        }
        self._raise_event(event)
    
    def assess(self, likelihood: int, impact: int, inherent_score: int,
               residual_score: int, rationale: str = None):
        """Assess the risk with scoring"""
        if not (1 <= likelihood <= 5):
            raise ValueError("Likelihood must be between 1 and 5")
        if not (1 <= impact <= 5):
            raise ValueError("Impact must be between 1 and 5")
        
        self.scoring = {
            "likelihood": likelihood,
            "impact": impact,
            "inherent_score": inherent_score,
            "residual_score": residual_score,
            "rationale": rationale,
        }
        
        if self.lifecycle_state == self.LifecycleState.DRAFT:
            self.lifecycle_state = self.LifecycleState.ASSESSED
            
            event = BusinessRiskAssessed()
            event.payload = {
                "risk_id": str(self.id),
                "likelihood": likelihood,
                "impact": impact,
                "inherent_score": inherent_score,
                "residual_score": residual_score,
            }
            self._raise_event(event)
    
    def treat(self, treatment_plan_id: uuid.UUID = None):
        """Mark the risk as treated"""
        if self.lifecycle_state != self.LifecycleState.TREATED:
            if treatment_plan_id:
                self.treatmentPlanId = treatment_plan_id

            self.lifecycle_state = self.LifecycleState.TREATED

            event = BusinessRiskTreated()
            event.payload = {
                "risk_id": str(self.id),
                "treatment_plan_id": str(treatment_plan_id) if treatment_plan_id else None,
            }
            self._raise_event(event)
    
    def accept(self):
        """Accept the risk"""
        if self.lifecycle_state != self.LifecycleState.ACCEPTED:
            self.lifecycle_state = self.LifecycleState.ACCEPTED
            
            event = BusinessRiskAccepted()
            event.payload = {
                "risk_id": str(self.id),
            }
            self._raise_event(event)
    
    def close(self):
        """Close the risk"""
        if self.lifecycle_state != self.LifecycleState.CLOSED:
            self.lifecycle_state = self.LifecycleState.CLOSED
            
            event = BusinessRiskClosed()
            event.payload = {
                "risk_id": str(self.id),
            }
            self._raise_event(event)
    
    def add_process(self, process_id: uuid.UUID):
        """Add a process to this risk"""
        if process_id not in self.processIds:
            self.processIds.append(process_id)
    
    def add_org_unit(self, org_unit_id: uuid.UUID):
        """Add an organizational unit to this risk"""
        if org_unit_id not in self.orgUnitIds:
            self.orgUnitIds.append(org_unit_id)
    
    def add_control_implementation(self, implementation_id: uuid.UUID):
        """Add a control implementation to this risk"""
        if implementation_id not in self.controlImplementationIds:
            self.controlImplementationIds.append(implementation_id)
    
    def add_exception(self, exception_id: uuid.UUID):
        """Add a risk exception to this risk"""
        if exception_id not in self.exceptionIds:
            self.exceptionIds.append(exception_id)
    
    def __str__(self):
        return self.title

