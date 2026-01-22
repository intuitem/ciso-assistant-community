"""
RiskTreatmentPlan Supporting Entity

Represents a treatment plan for a risk.
"""

import uuid
from typing import List, Optional
from datetime import date
from django.db import models
from django.utils import timezone

from core.domain.aggregate import AggregateRoot
from ..domain_events import (
    RiskTreatmentPlanCreated,
    RiskTreatmentPlanActivated,
    RiskTreatmentPlanCompleted,
    RiskTreatmentPlanAbandoned,
)


class RiskTreatmentPlan(AggregateRoot):
    """
    Risk Treatment Plan supporting entity.
    
    Represents a plan to treat a risk with tasks.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"
    
    class Strategy(models.TextChoices):
        AVOID = "avoid", "Avoid"
        MITIGATE = "mitigate", "Mitigate"
        TRANSFER = "transfer", "Transfer"
        ACCEPT = "accept", "Accept"
    
    # Risk reference
    riskId = models.UUIDField(db_index=True, help_text="ID of the risk this plan treats")
    
    # Basic fields
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    
    # Strategy and lifecycle
    strategy = models.CharField(
        max_length=20,
        choices=Strategy.choices,
        db_index=True
    )
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Tasks (stored as JSON array of task objects)
    tasks = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of treatment tasks: {title, ownerUserId, dueDate, status, evidenceIds[]}"
    )
    
    # Dates
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Additional fields
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = "risk_registers_risk_treatment_plans"
        verbose_name = "Risk Treatment Plan"
        verbose_name_plural = "Risk Treatment Plans"
        indexes = [
            models.Index(fields=["riskId", "lifecycle_state"]),
            models.Index(fields=["strategy"]),
        ]
    
    def create(self, risk_id: uuid.UUID, name: str, strategy: str,
               description: str = None, tasks: List[dict] = None):
        """
        Create a new risk treatment plan.
        
        Domain method that enforces business rules and raises events.
        """
        self.riskId = risk_id
        self.name = name
        self.description = description
        self.strategy = strategy
        self.tasks = tasks or []
        self.lifecycle_state = self.LifecycleState.DRAFT
        
        event = RiskTreatmentPlanCreated()
        event.payload = {
            "plan_id": str(self.id),
            "risk_id": str(risk_id),
            "strategy": strategy,
        }
        self._raise_event(event)
    
    def activate(self):
        """Activate the treatment plan"""
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            self.lifecycle_state = self.LifecycleState.ACTIVE
            if not self.started_at:
                self.started_at = timezone.now()
            
            event = RiskTreatmentPlanActivated()
            event.payload = {
                "plan_id": str(self.id),
                "risk_id": str(self.riskId),
            }
            self._raise_event(event)
    
    def complete(self):
        """Mark the treatment plan as completed"""
        if self.lifecycle_state != self.LifecycleState.COMPLETED:
            self.lifecycle_state = self.LifecycleState.COMPLETED
            self.completed_at = timezone.now()
            
            event = RiskTreatmentPlanCompleted()
            event.payload = {
                "plan_id": str(self.id),
                "risk_id": str(self.riskId),
            }
            self._raise_event(event)
    
    def abandon(self):
        """Abandon the treatment plan"""
        if self.lifecycle_state != self.LifecycleState.ABANDONED:
            self.lifecycle_state = self.LifecycleState.ABANDONED
            
            event = RiskTreatmentPlanAbandoned()
            event.payload = {
                "plan_id": str(self.id),
                "risk_id": str(self.riskId),
            }
            self._raise_event(event)
    
    def add_task(self, title: str, owner_user_id: uuid.UUID, due_date: Optional[date] = None,
                 status: str = "Open", evidence_ids: List[uuid.UUID] = None):
        """
        Add a task to the treatment plan.
        
        Args:
            title: Task title
            owner_user_id: Owner user ID
            due_date: Optional due date
            status: Task status (Open, InProgress, Done, Blocked)
            evidence_ids: Optional list of evidence IDs
        """
        task = {
            "id": str(uuid.uuid4()),
            "title": title,
            "ownerUserId": str(owner_user_id),
            "dueDate": due_date.isoformat() if due_date else None,
            "status": status,
            "evidenceIds": [str(eid) for eid in (evidence_ids or [])],
        }
        self.tasks.append(task)
    
    def update_task_status(self, task_id: str, status: str):
        """Update a task's status"""
        for task in self.tasks:
            if task.get("id") == task_id:
                task["status"] = status
                break
    
    def __str__(self):
        return f"{self.name} ({self.strategy})"

