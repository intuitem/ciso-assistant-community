"""
POAM Item Aggregate

Aggregate for managing Plan of Action and Milestones (POA&M) items,
including weaknesses, milestones, and remediation tracking.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class POAMItem(AggregateRoot):
    """
    POAM Item aggregate for managing security weaknesses and remediation plans.

    Tracks security findings, remediation milestones, responsible parties,
    and compliance status.
    """

    # Basic identification
    weakness_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique identifier for the weakness (e.g., V-12345, APP-001)"
    )

    title = models.CharField(
        max_length=500,
        help_text="Title/description of the weakness"
    )

    description = models.TextField(
        help_text="Detailed description of the weakness"
    )

    # Source information
    SOURCE_TYPES = [
        ('assessment', 'Security Assessment'),
        ('audit', 'Security Audit'),
        ('inspection', 'Security Inspection'),
        ('scan', 'Vulnerability Scan'),
        ('incident', 'Security Incident'),
        ('manual', 'Manual Entry'),
        ('other', 'Other'),
    ]

    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        default='assessment',
        help_text="Source of the weakness identification"
    )

    source_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Reference to source document/report"
    )

    # Relationships
    system_group_id = models.UUIDField(
        db_index=True,
        help_text="Associated system group"
    )

    assessment_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Associated compliance assessment"
    )

    vulnerability_finding_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Associated vulnerability finding"
    )

    control_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Associated security control (e.g., AC-2, IA-5)"
    )

    cci_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Associated CCI IDs"
    )

    # Risk and severity
    SEVERITY_LEVELS = [
        ('very_low', 'Very Low'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('very_high', 'Very High'),
    ]

    risk_level = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='moderate',
        help_text="Risk/severity level of the weakness"
    )

    impact_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of potential impact"
    )

    likelihood = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='moderate',
        help_text="Likelihood of exploitation"
    )

    # Status and lifecycle
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('deferred', 'Deferred'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current status of the POA&M item"
    )

    # Dates
    identified_date = models.DateField(
        default=timezone.now,
        help_text="Date the weakness was identified"
    )

    submitted_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the POA&M was submitted"
    )

    approved_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the POA&M was approved"
    )

    estimated_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Estimated completion date"
    )

    actual_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual completion date"
    )

    # Responsible parties
    responsible_organization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Organization responsible for remediation"
    )

    point_of_contact = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Primary point of contact"
    )

    contact_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Contact email address"
    )

    contact_phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )

    # Remediation details
    remediation_plan = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed remediation plan"
    )

    resources_required = models.TextField(
        blank=True,
        null=True,
        help_text="Resources required for remediation"
    )

    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated cost for remediation"
    )

    # Milestones (stored as JSON)
    milestones = models.JSONField(
        default=list,
        blank=True,
        help_text="List of remediation milestones with dates and descriptions"
    )

    # Deviation information (if applicable)
    has_deviation = models.BooleanField(
        default=False,
        help_text="Whether a deviation request exists"
    )

    deviation_justification = models.TextField(
        blank=True,
        null=True,
        help_text="Justification for deviation if applicable"
    )

    deviation_approved = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether deviation was approved"
    )

    deviation_approval_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date deviation was approved"
    )

    # Evidence and documentation
    evidence_before = models.JSONField(
        default=list,
        blank=True,
        help_text="Evidence of weakness before remediation"
    )

    evidence_after = models.JSONField(
        default=list,
        blank=True,
        help_text="Evidence of remediation completion"
    )

    supporting_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional supporting documents"
    )

    # Comments and notes
    comments = models.TextField(
        blank=True,
        null=True,
        help_text="General comments and notes"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="POA&M tags for organization"
    )

    # Tracking
    last_reviewed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last status review"
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled review"
    )

    # Recurring weakness flag
    is_recurring = models.BooleanField(
        default=False,
        help_text="Whether this weakness has occurred before"
    )

    class Meta:
        db_table = "poam_items"
        indexes = [
            models.Index(fields=['system_group_id', 'status'], name='poam_system_status_idx'),
            models.Index(fields=['assessment_id'], name='poam_assessment_idx'),
            models.Index(fields=['vulnerability_finding_id'], name='poam_finding_idx'),
            models.Index(fields=['control_id'], name='poam_control_idx'),
            models.Index(fields=['status'], name='poam_status_idx'),
            models.Index(fields=['risk_level'], name='poam_risk_level_idx'),
            models.Index(fields=['estimated_completion_date'], name='poam_completion_date_idx'),
            models.Index(fields=['weakness_id'], name='poam_weakness_id_idx'),
        ]
        ordering = ['-created_at']

    def create_poam_item(
        self,
        weakness_id: str,
        title: str,
        description: str,
        system_group_id: uuid.UUID,
        risk_level: str = 'moderate',
        source_type: str = 'assessment',
        tags: Optional[List[str]] = None
    ):
        """Create a new POA&M item"""
        self.weakness_id = weakness_id
        self.title = title
        self.description = description
        self.system_group_id = system_group_id
        self.risk_level = risk_level
        self.source_type = source_type
        self.tags = tags if tags is not None else []
        self.status = 'draft'
        self.identified_date = timezone.now().date()

        from .domain_events import POAMItemCreated
        self._raise_event(POAMItemCreated(
            aggregate_id=self.id,
            weakness_id=weakness_id,
            title=title,
            system_group_id=str(system_group_id)
        ))

    def submit_for_approval(self):
        """Submit POA&M item for approval"""
        if self.status == 'draft':
            self.status = 'submitted'
            self.submitted_date = timezone.now().date()

            from .domain_events import POAMItemSubmitted
            self._raise_event(POAMItemSubmitted(
                aggregate_id=self.id,
                weakness_id=self.weakness_id
            ))

    def approve_poam(self):
        """Approve the POA&M item"""
        if self.status == 'submitted':
            self.status = 'approved'
            self.approved_date = timezone.now().date()

            from .domain_events import POAMItemApproved
            self._raise_event(POAMItemApproved(
                aggregate_id=self.id,
                weakness_id=self.weakness_id
            ))

    def reject_poam(self, reason: str):
        """Reject the POA&M item"""
        if self.status == 'submitted':
            self.status = 'rejected'
            self.comments = f"Rejected: {reason}\n\n{self.comments or ''}"

            from .domain_events import POAMItemRejected
            self._raise_event(POAMItemRejected(
                aggregate_id=self.id,
                weakness_id=self.weakness_id,
                reason=reason
            ))

    def start_remediation(self):
        """Mark remediation as started"""
        if self.status in ['approved', 'draft']:
            self.status = 'in_progress'

            from .domain_events import POAMRemediationStarted
            self._raise_event(POAMRemediationStarted(
                aggregate_id=self.id,
                weakness_id=self.weakness_id
            ))

    def complete_remediation(self, evidence: Optional[List[Dict[str, Any]]] = None):
        """Mark remediation as completed"""
        if self.status == 'in_progress':
            self.status = 'completed'
            self.actual_completion_date = timezone.now().date()

            if evidence:
                self.evidence_after = evidence

            from .domain_events import POAMRemediationCompleted
            self._raise_event(POAMRemediationCompleted(
                aggregate_id=self.id,
                weakness_id=self.weakness_id
            ))

    def add_milestone(self, description: str, target_date: timezone.date, status: str = 'pending'):
        """Add a remediation milestone"""
        milestone = {
            'id': str(uuid.uuid4()),
            'description': description,
            'target_date': target_date.isoformat(),
            'status': status,
            'created_at': timezone.now().isoformat()
        }

        if not self.milestones:
            self.milestones = []
        self.milestones.append(milestone)

        from .domain_events import POAMMilestoneAdded
        self._raise_event(POAMMilestoneAdded(
            aggregate_id=self.id,
            milestone_id=milestone['id'],
            description=description
        ))

    def update_milestone(self, milestone_id: str, status: str, actual_date: Optional[timezone.date] = None):
        """Update milestone status"""
        for milestone in self.milestones:
            if milestone['id'] == milestone_id:
                old_status = milestone['status']
                milestone['status'] = status
                milestone['updated_at'] = timezone.now().isoformat()

                if actual_date:
                    milestone['actual_date'] = actual_date.isoformat()

                from .domain_events import POAMMilestoneUpdated
                self._raise_event(POAMMilestoneUpdated(
                    aggregate_id=self.id,
                    milestone_id=milestone_id,
                    old_status=old_status,
                    new_status=status
                ))
                break

    def request_deviation(self, justification: str):
        """Request a deviation for this POA&M item"""
        self.has_deviation = True
        self.deviation_justification = justification

        from .domain_events import POAMDeviationRequested
        self._raise_event(POAMDeviationRequested(
            aggregate_id=self.id,
            weakness_id=self.weakness_id,
            justification=justification
        ))

    def approve_deviation(self):
        """Approve the deviation request"""
        if self.has_deviation and not self.deviation_approved:
            self.deviation_approved = True
            self.deviation_approval_date = timezone.now().date()

            from .domain_events import POAMDeviationApproved
            self._raise_event(POAMDeviationApproved(
                aggregate_id=self.id,
                weakness_id=self.weakness_id
            ))

    def add_evidence(self, evidence_type: str, evidence_data: Dict[str, Any]):
        """Add evidence to the POA&M item"""
        evidence_entry = {
            'id': str(uuid.uuid4()),
            'type': evidence_type,
            'data': evidence_data,
            'added_at': timezone.now().isoformat(),
            'added_by': str(getattr(self, 'updated_by', None))
        }

        if evidence_type == 'before_remediation':
            if not self.evidence_before:
                self.evidence_before = []
            self.evidence_before.append(evidence_entry)
        elif evidence_type == 'after_remediation':
            if not self.evidence_after:
                self.evidence_after = []
            self.evidence_after.append(evidence_entry)
        else:
            if not self.supporting_documents:
                self.supporting_documents = []
            self.supporting_documents.append(evidence_entry)

        from .domain_events import POAMEvidenceAdded
        self._raise_event(POAMEvidenceAdded(
            aggregate_id=self.id,
            evidence_type=evidence_type,
            evidence_id=evidence_entry['id']
        ))

    def schedule_review(self, review_date: timezone.date):
        """Schedule next review date"""
        self.next_review_date = review_date

        from .domain_events import POAMReviewScheduled
        self._raise_event(POAMReviewScheduled(
            aggregate_id=self.id,
            review_date=review_date.isoformat()
        ))

    def mark_reviewed(self):
        """Mark as reviewed"""
        self.last_reviewed_date = timezone.now().date()
        self.next_review_date = None  # Clear scheduled review

    @property
    def is_overdue(self) -> bool:
        """Check if the POA&M item is overdue"""
        if not self.estimated_completion_date:
            return False
        return timezone.now().date() > self.estimated_completion_date and self.status != 'completed'

    @property
    def days_overdue(self) -> int:
        """Get number of days overdue"""
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.estimated_completion_date).days

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on milestones"""
        if not self.milestones:
            return 0.0

        completed_milestones = sum(1 for m in self.milestones if m.get('status') == 'completed')
        return round((completed_milestones / len(self.milestones)) * 100, 2)

    @property
    def upcoming_milestones(self) -> List[Dict[str, Any]]:
        """Get upcoming milestones"""
        today = timezone.now().date()
        return [
            m for m in self.milestones
            if m.get('status') in ['pending', 'in_progress'] and
            m.get('target_date') and
            timezone.datetime.fromisoformat(m['target_date']).date() >= today
        ]

    @property
    def overdue_milestones(self) -> List[Dict[str, Any]]:
        """Get overdue milestones"""
        today = timezone.now().date()
        return [
            m for m in self.milestones
            if m.get('status') in ['pending', 'in_progress'] and
            m.get('target_date') and
            timezone.datetime.fromisoformat(m['target_date']).date() < today
        ]

    def __str__(self):
        return f"POAMItem({self.weakness_id}: {self.title})"
