"""
AssetRisk Aggregate

Represents a risk associated with assets.
"""

import uuid
from typing import Optional
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from core.domain.fields import EmbeddedIdArrayField
from ..domain_events import (
    AssetRiskCreated,
    AssetRiskAssessed,
    AssetRiskTreated,
    AssetRiskAccepted,
    AssetRiskClosed,
)


class AssetRisk(AggregateRoot):
    """
    Asset Risk aggregate root.
    
    Represents a risk associated with one or more assets.
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
    
    # Threat and vulnerability
    threat = models.TextField(blank=True, null=True, help_text="Threat description")
    vulnerability = models.TextField(blank=True, null=True, help_text="Vulnerability description")
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Embedded ID arrays (replacing ManyToMany)
    assetIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of asset IDs"
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
    relatedRiskIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="Array of related risk IDs"
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
        db_table = "risk_registers_asset_risks"
        verbose_name = "Asset Risk"
        verbose_name_plural = "Asset Risks"
        indexes = [
            models.Index(fields=["lifecycle_state"]),
            models.Index(fields=["title"]),
            models.Index(fields=["treatmentPlanId"]),
        ]
    
    def create(self, title: str, description: str = None, threat: str = None,
               vulnerability: str = None):
        """
        Create a new asset risk.
        
        Domain method that enforces business rules and raises events.
        """
        self.title = title
        self.description = description
        self.threat = threat
        self.vulnerability = vulnerability
        self.lifecycle_state = self.LifecycleState.DRAFT
        self.scoring = {
            "likelihood": 1,
            "impact": 1,
            "inherent_score": 1,
            "residual_score": 1,
            "rationale": None,
        }
        
        event = AssetRiskCreated()
        event.payload = {
            "risk_id": str(self.id),
            "title": title,
        }
        self._raise_event(event)
    
    def assess(self, likelihood: int, impact: int, inherent_score: int,
               residual_score: int, rationale: str = None):
        """
        Assess the risk with scoring.
        
        Args:
            likelihood: Likelihood rating (1-5)
            impact: Impact rating (1-5)
            inherent_score: Inherent risk score
            residual_score: Residual risk score
            rationale: Optional rationale
        """
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
            
            event = AssetRiskAssessed()
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
            
            event = AssetRiskTreated()
            event.payload = {
                "risk_id": str(self.id),
                "treatment_plan_id": str(treatment_plan_id) if treatment_plan_id else None,
            }
            self._raise_event(event)
    
    def accept(self):
        """Accept the risk"""
        if self.lifecycle_state != self.LifecycleState.ACCEPTED:
            self.lifecycle_state = self.LifecycleState.ACCEPTED
            
            event = AssetRiskAccepted()
            event.payload = {
                "risk_id": str(self.id),
            }
            self._raise_event(event)
    
    def close(self):
        """Close the risk"""
        if self.lifecycle_state != self.LifecycleState.CLOSED:
            self.lifecycle_state = self.LifecycleState.CLOSED
            
            event = AssetRiskClosed()
            event.payload = {
                "risk_id": str(self.id),
            }
            self._raise_event(event)
    
    def add_asset(self, asset_id: uuid.UUID):
        """Add an asset to this risk"""
        if asset_id not in self.assetIds:
            self.assetIds.append(asset_id)
    
    def add_control_implementation(self, implementation_id: uuid.UUID):
        """Add a control implementation to this risk"""
        if implementation_id not in self.controlImplementationIds:
            self.controlImplementationIds.append(implementation_id)
    
    def add_exception(self, exception_id: uuid.UUID):
        """Add a risk exception to this risk"""
        if exception_id not in self.exceptionIds:
            self.exceptionIds.append(exception_id)
    
    def add_related_risk(self, risk_id: uuid.UUID):
        """Add a related risk"""
        if risk_id not in self.relatedRiskIds:
            self.relatedRiskIds.append(risk_id)
    
    def __str__(self):
        return self.title

