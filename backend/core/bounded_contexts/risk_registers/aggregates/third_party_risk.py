"""
ThirdPartyRisk Aggregate

Represents a risk associated with third parties.
"""

import uuid
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    ThirdPartyRiskCreated,
    ThirdPartyRiskAssessed,
    ThirdPartyRiskTreated,
    ThirdPartyRiskAccepted,
    ThirdPartyRiskClosed,
)


class ThirdPartyRisk(AggregateRoot):
    """
    Third Party Risk aggregate root.
    
    Represents a risk associated with third parties and services.
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
    thirdPartyIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of third party IDs"
    )
    serviceIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of service IDs"
    )
    controlImplementationIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of control implementation IDs"
    )
    assessmentRunIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of assessment run IDs"
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
        db_table = "risk_registers_third_party_risks"
        verbose_name = "Third Party Risk"
        verbose_name_plural = "Third Party Risks"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["title"]),
            models.Index(fields=["treatmentPlanId"]),
        ]
    
    def create(self, title: str, description: str = None):
        """
        Create a new third party risk.
        
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
        
        event = ThirdPartyRiskCreated()
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
            
            event = ThirdPartyRiskAssessed()
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

            event = ThirdPartyRiskTreated()
            event.payload = {
                "risk_id": str(self.id),
                "treatment_plan_id": str(treatment_plan_id) if treatment_plan_id else None,
            }
            self._raise_event(event)
    
    def accept(self):
        """Accept the risk"""
        if self.lifecycle_state != self.LifecycleState.ACCEPTED:
            self.lifecycle_state = self.LifecycleState.ACCEPTED
            
            event = ThirdPartyRiskAccepted()
            event.payload = {
                "risk_id": str(self.id),
            }
            self._raise_event(event)
    
    def close(self):
        """Close the risk"""
        if self.lifecycle_state != self.LifecycleState.CLOSED:
            self.lifecycle_state = self.LifecycleState.CLOSED
            
            event = ThirdPartyRiskClosed()
            event.payload = {
                "risk_id": str(self.id),
            }
            self._raise_event(event)
    
    def add_third_party(self, third_party_id: uuid.UUID):
        """Add a third party to this risk"""
        if third_party_id not in self.thirdPartyIds:
            self.thirdPartyIds.append(third_party_id)
    
    def add_service(self, service_id: uuid.UUID):
        """Add a service to this risk"""
        if service_id not in self.serviceIds:
            self.serviceIds.append(service_id)
    
    def add_control_implementation(self, implementation_id: uuid.UUID):
        """Add a control implementation to this risk"""
        if implementation_id not in self.controlImplementationIds:
            self.controlImplementationIds.append(implementation_id)
    
    def add_assessment_run(self, assessment_run_id: uuid.UUID):
        """Add an assessment run to this risk"""
        if assessment_run_id not in self.assessmentRunIds:
            self.assessmentRunIds.append(assessment_run_id)
    
    def add_exception(self, exception_id: uuid.UUID):
        """Add a risk exception to this risk"""
        if exception_id not in self.exceptionIds:
            self.exceptionIds.append(exception_id)
    
    def __str__(self):
        return self.title

