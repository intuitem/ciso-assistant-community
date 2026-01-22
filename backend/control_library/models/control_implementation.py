"""
Control Implementation Aggregate

Aggregate for managing control implementations within specific contexts,
including evidence, assessment results, and implementation status.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class ControlImplementation(AggregateRoot):
    """
    Control Implementation aggregate for managing control implementations.

    Tracks how controls are implemented in specific contexts (systems,
    processes, assets), including evidence, assessments, and status.
    """

    # Basic identification
    implementation_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique implementation identifier"
    )

    control_id = models.UUIDField(
        db_index=True,
        help_text="ID of the control being implemented"
    )

    framework_id = models.UUIDField(
        db_index=True,
        help_text="ID of the framework"
    )

    # Context information
    context_type = models.CharField(
        max_length=50,
        help_text="Type of context (system, process, asset, service)"
    )

    context_id = models.UUIDField(
        db_index=True,
        help_text="ID of the context entity"
    )

    context_name = models.CharField(
        max_length=255,
        help_text="Name of the context entity"
    )

    # Implementation details
    implementation_statement = models.TextField(
        blank=True,
        null=True,
        help_text="Specific implementation statement"
    )

    implementation_details = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed implementation description"
    )

    responsible_party = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Party responsible for implementation"
    )

    # Implementation status
    STATUS_CHOICES = [
        ('not_implemented', 'Not Implemented'),
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('implemented', 'Implemented'),
        ('verified', 'Verified'),
        ('not_applicable', 'Not Applicable'),
        ('compensated', 'Compensated'),
        ('inherited', 'Inherited'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_implemented',
        help_text="Implementation status"
    )

    # Implementation dates
    planned_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned implementation date"
    )

    implemented_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual implementation date"
    )

    verified_date = models.DateField(
        null=True,
        blank=True,
        help_text="Verification date"
    )

    # Assessment and compliance
    compliance_status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Compliance status (compliant, non-compliant, etc.)"
    )

    compliance_score = models.IntegerField(
        default=0,
        help_text="Compliance score (0-100)"
    )

    assessment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last assessment date"
    )

    assessor = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Person/entity who performed assessment"
    )

    assessment_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Assessment notes and findings"
    )

    # Evidence management
    evidence_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of evidence supporting this implementation"
    )

    primary_evidence_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of primary evidence"
    )

    # Risk and impact
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('very_low', 'Very Low'),
            ('low', 'Low'),
            ('moderate', 'Moderate'),
            ('high', 'High'),
            ('very_high', 'Very High'),
            ('critical', 'Critical'),
        ],
        default='moderate',
        help_text="Risk level if not implemented"
    )

    business_impact = models.TextField(
        blank=True,
        null=True,
        help_text="Business impact of non-implementation"
    )

    # Cost and effort
    implementation_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated implementation cost"
    )

    implementation_effort = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Implementation effort (Low, Medium, High)"
    )

    maintenance_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual maintenance cost"
    )

    # Inheritance and compensation
    inherited_from = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Source of inheritance (if applicable)"
    )

    compensating_controls = models.JSONField(
        default=list,
        blank=True,
        help_text="Compensating controls (if applicable)"
    )

    # Review and maintenance
    review_frequency = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Review frequency (e.g., 'Annual', 'Quarterly')"
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled review date"
    )

    last_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last review date"
    )

    # Exceptions and deviations
    has_exception = models.BooleanField(
        default=False,
        help_text="Whether an exception/deviation exists"
    )

    exception_justification = models.TextField(
        blank=True,
        null=True,
        help_text="Exception/deviation justification"
    )

    exception_approved = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether exception is approved"
    )

    exception_expiry = models.DateField(
        null=True,
        blank=True,
        help_text="Exception expiry date"
    )

    # Automation and monitoring
    automated_monitoring = models.BooleanField(
        default=False,
        help_text="Whether implementation is automatically monitored"
    )

    monitoring_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Monitoring configuration and details"
    )

    alert_rules = models.JSONField(
        default=list,
        blank=True,
        help_text="Alert rules for this implementation"
    )

    # Integration with other systems
    system_integration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Integration details with other systems"
    )

    # Metadata and tags
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Implementation tags"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    # Usage tracking
    access_count = models.IntegerField(
        default=0,
        help_text="Number of times accessed/reviewed"
    )

    class Meta:
        db_table = "control_implementations"
        indexes = [
            models.Index(fields=['control_id', 'context_id'], name='impl_control_context_idx'),
            models.Index(fields=['framework_id'], name='impl_framework_idx'),
            models.Index(fields=['context_type', 'context_id'], name='impl_context_type_idx'),
            models.Index(fields=['status'], name='impl_status_idx'),
            models.Index(fields=['compliance_status'], name='impl_compliance_idx'),
            models.Index(fields=['risk_level'], name='impl_risk_idx'),
            models.Index(fields=['next_review_date'], name='impl_review_idx'),
            models.Index(fields=['exception_expiry'], name='impl_exception_idx'),
            models.Index(fields=['created_at'], name='impl_created_idx'),
        ]
        ordering = ['-created_at']
        unique_together = [['control_id', 'context_id']]

    def create_implementation(
        self,
        implementation_id: str,
        control_id: uuid.UUID,
        framework_id: uuid.UUID,
        context_type: str,
        context_id: uuid.UUID,
        context_name: str,
        responsible_party: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new control implementation"""
        self.implementation_id = implementation_id
        self.control_id = control_id
        self.framework_id = framework_id
        self.context_type = context_type
        self.context_id = context_id
        self.context_name = context_name
        self.responsible_party = responsible_party
        self.tags = tags if tags is not None else []

        from .domain_events import ControlImplementationCreated
        self._raise_event(ControlImplementationCreated(
            aggregate_id=self.id,
            implementation_id=implementation_id,
            control_id=str(control_id),
            context_type=context_type,
            context_name=context_name
        ))

    def update_status(self, new_status: str, notes: Optional[str] = None):
        """Update implementation status"""
        old_status = self.status
        self.status = new_status

        # Set appropriate dates based on status
        if new_status == 'implemented' and not self.implemented_date:
            self.implemented_date = timezone.now().date()
        elif new_status == 'verified' and not self.verified_date:
            self.verified_date = timezone.now().date()

        from .domain_events import ControlImplementationStatusChanged
        self._raise_event(ControlImplementationStatusChanged(
            aggregate_id=self.id,
            implementation_id=self.implementation_id,
            old_status=old_status,
            new_status=new_status,
            notes=notes
        ))

    def assess_compliance(self, compliance_status: str, compliance_score: int, assessor: str, notes: Optional[str] = None):
        """Assess implementation compliance"""
        old_status = self.compliance_status
        old_score = self.compliance_score

        self.compliance_status = compliance_status
        self.compliance_score = compliance_score
        self.assessment_date = timezone.now().date()
        self.assessor = assessor
        self.assessment_notes = notes

        from .domain_events import ControlImplementationAssessed
        self._raise_event(ControlImplementationAssessed(
            aggregate_id=self.id,
            implementation_id=self.implementation_id,
            old_status=old_status,
            new_status=compliance_status,
            old_score=old_score,
            new_score=compliance_score,
            assessor=assessor
        ))

    def add_evidence(self, evidence_id: str, evidence_type: str = 'general'):
        """Add evidence to the implementation"""
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)

            # Set as primary if it's the first evidence
            if not self.primary_evidence_id:
                self.primary_evidence_id = uuid.UUID(evidence_id)

            from .domain_events import ControlImplementationEvidenceAdded
            self._raise_event(ControlImplementationEvidenceAdded(
                aggregate_id=self.id,
                implementation_id=self.implementation_id,
                evidence_id=evidence_id,
                evidence_type=evidence_type
            ))

    def remove_evidence(self, evidence_id: str):
        """Remove evidence from the implementation"""
        if evidence_id in self.evidence_ids:
            self.evidence_ids.remove(evidence_id)

            # Clear primary evidence if it was removed
            if str(self.primary_evidence_id) == evidence_id:
                self.primary_evidence_id = None

    def set_primary_evidence(self, evidence_id: str):
        """Set primary evidence"""
        if evidence_id in self.evidence_ids:
            self.primary_evidence_id = uuid.UUID(evidence_id)

    def request_exception(self, justification: str, expiry_date: Optional[timezone.date] = None):
        """Request an exception/deviation"""
        self.has_exception = True
        self.exception_justification = justification
        self.exception_expiry = expiry_date
        self.exception_approved = False

        from .domain_events import ControlImplementationExceptionRequested
        self._raise_event(ControlImplementationExceptionRequested(
            aggregate_id=self.id,
            implementation_id=self.implementation_id,
            justification=justification,
            expiry_date=str(expiry_date) if expiry_date else None
        ))

    def approve_exception(self):
        """Approve the exception"""
        if self.has_exception and not self.exception_approved:
            self.exception_approved = True

            from .domain_events import ControlImplementationExceptionApproved
            self._raise_event(ControlImplementationExceptionApproved(
                aggregate_id=self.id,
                implementation_id=self.implementation_id
            ))

    def reject_exception(self, reason: str):
        """Reject the exception"""
        if self.has_exception and self.exception_approved is False:
            self.has_exception = False
            self.exception_justification = f"Rejected: {reason}"

            from .domain_events import ControlImplementationExceptionRejected
            self._raise_event(ControlImplementationExceptionRejected(
                aggregate_id=self.id,
                implementation_id=self.implementation_id,
                reason=reason
            ))

    def schedule_review(self, review_date: timezone.date):
        """Schedule next review"""
        self.next_review_date = review_date

        from .domain_events import ControlImplementationReviewScheduled
        self._raise_event(ControlImplementationReviewScheduled(
            aggregate_id=self.id,
            implementation_id=self.implementation_id,
            review_date=str(review_date)
        ))

    def conduct_review(self, review_date: Optional[timezone.date] = None, notes: Optional[str] = None):
        """Conduct implementation review"""
        self.last_review_date = review_date or timezone.now().date()
        self.next_review_date = None  # Clear scheduled review

        from .domain_events import ControlImplementationReviewed
        self._raise_event(ControlImplementationReviewed(
            aggregate_id=self.id,
            implementation_id=self.implementation_id,
            review_date=str(self.last_review_date),
            notes=notes
        ))

    def update_monitoring(self, monitoring_details: Dict[str, Any], alert_rules: Optional[List[Dict[str, Any]]] = None):
        """Update monitoring configuration"""
        self.automated_monitoring = True
        self.monitoring_details = monitoring_details
        if alert_rules is not None:
            self.alert_rules = alert_rules

        from .domain_events import ControlImplementationMonitoringUpdated
        self._raise_event(ControlImplementationMonitoringUpdated(
            aggregate_id=self.id,
            implementation_id=self.implementation_id,
            monitoring_enabled=True
        ))

    def record_access(self):
        """Record access/review of implementation"""
        self.access_count += 1

    @property
    def is_implemented(self) -> bool:
        """Check if implementation is complete"""
        return self.status in ['implemented', 'verified', 'inherited', 'compensated']

    @property
    def is_compliant(self) -> bool:
        """Check if implementation is compliant"""
        return self.compliance_status == 'compliant'

    @property
    def is_overdue_for_review(self) -> bool:
        """Check if overdue for review"""
        if not self.next_review_date:
            return False
        return timezone.now().date() > self.next_review_date

    @property
    def has_valid_exception(self) -> bool:
        """Check if has valid exception"""
        if not self.has_exception or not self.exception_approved:
            return False
        if not self.exception_expiry:
            return True
        return timezone.now().date() <= self.exception_expiry

    @property
    def days_to_exception_expiry(self) -> Optional[int]:
        """Get days until exception expires"""
        if not self.exception_expiry:
            return None
        return (self.exception_expiry - timezone.now().date()).days

    @property
    def evidence_count(self) -> int:
        """Get number of evidence items"""
        return len(self.evidence_ids)

    @property
    def implementation_age_days(self) -> Optional[int]:
        """Get implementation age in days"""
        if not self.implemented_date:
            return None
        return (timezone.now().date() - self.implemented_date).days

    def get_evidence_summary(self) -> Dict[str, Any]:
        """Get evidence summary"""
        return {
            'total_evidence': self.evidence_count,
            'has_primary_evidence': self.primary_evidence_id is not None,
            'evidence_ids': self.evidence_ids
        }

    def __str__(self):
        return f"ControlImplementation({self.implementation_id}: {self.context_name} - {self.status})"
