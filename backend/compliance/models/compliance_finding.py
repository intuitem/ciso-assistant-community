"""
Compliance Finding Aggregate

Aggregate for managing compliance findings, observations, and issues
identified during compliance assessments with remediation tracking.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class ComplianceFinding(AggregateRoot):
    """
    Compliance Finding aggregate for managing assessment findings.

    Tracks compliance issues, observations, and non-conformities identified
    during assessments, including remediation planning and tracking.
    """

    # Relationship to compliance assessment
    compliance_assessment_id = models.UUIDField(
        db_index=True,
        help_text="ID of the compliance assessment this finding belongs to"
    )

    # Finding identification
    finding_id = models.CharField(
        max_length=100,
        help_text="Unique finding identifier (e.g., 'FIND-2024-001')"
    )

    finding_title = models.CharField(
        max_length=500,
        help_text="Title/summary of the finding"
    )

    finding_description = models.TextField(
        help_text="Detailed description of the finding"
    )

    # Finding classification
    FINDING_TYPES = [
        ('non_conformity', 'Non-Conformity'),
        ('observation', 'Observation'),
        ('opportunity_for_improvement', 'Opportunity for Improvement'),
        ('positive_finding', 'Positive Finding'),
        ('minor_deficiency', 'Minor Deficiency'),
        ('major_deficiency', 'Major Deficiency'),
    ]

    finding_type = models.CharField(
        max_length=30,
        choices=FINDING_TYPES,
        default='non_conformity',
        help_text="Type of finding"
    )

    # Severity and impact
    SEVERITY_LEVELS = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('informational', 'Informational'),
    ]

    severity = models.CharField(
        max_length=15,
        choices=SEVERITY_LEVELS,
        default='medium',
        help_text="Severity level of the finding"
    )

    impact_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the impact of this finding"
    )

    # Framework and requirement context
    framework = models.CharField(
        max_length=100,
        help_text="Compliance framework this finding relates to"
    )

    requirement_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Specific requirement identifier (e.g., 'AC-1')"
    )

    requirement_title = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Title of the related requirement"
    )

    # Finding status
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('remediated', 'Remediated'),
        ('closed', 'Closed'),
        ('dismissed', 'Dismissed'),
        ('escalated', 'Escalated'),
    ]

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='open',
        help_text="Current status of the finding"
    )

    # Finding details
    root_cause = models.TextField(
        blank=True,
        null=True,
        help_text="Root cause analysis of the finding"
    )

    immediate_cause = models.TextField(
        blank=True,
        null=True,
        help_text="Immediate cause of the finding"
    )

    evidence = models.TextField(
        blank=True,
        null=True,
        help_text="Evidence supporting the finding"
    )

    supporting_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of supporting documents"
    )

    # Remediation planning
    remediation_required = models.BooleanField(
        default=True,
        help_text="Whether remediation is required"
    )

    remediation_plan = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed remediation plan"
    )

    remediation_steps = models.JSONField(
        default=list,
        blank=True,
        help_text="Step-by-step remediation actions"
    )

    # Remediation ownership
    remediation_owner_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID responsible for remediation"
    )

    remediation_owner_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of remediation owner"
    )

    remediation_team = models.JSONField(
        default=list,
        blank=True,
        help_text="Team members involved in remediation"
    )

    # Remediation timeline
    remediation_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline for remediation completion"
    )

    remediation_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date remediation was started"
    )

    remediation_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date remediation was completed"
    )

    # Remediation status and progress
    remediation_status = models.CharField(
        max_length=20,
        choices=[
            ('not_started', 'Not Started'),
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('deferred', 'Deferred'),
        ],
        default='not_started',
        help_text="Status of remediation efforts"
    )

    remediation_progress_percentage = models.IntegerField(
        default=0,
        help_text="Progress percentage (0-100)"
    )

    # Risk assessment
    associated_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of associated risks from Risk Registers"
    )

    risk_score = models.FloatField(
        default=0.0,
        help_text="Risk score associated with this finding (0.0-100.0)"
    )

    # Cost and resource estimates
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated cost of remediation"
    )

    estimated_effort_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated effort in person-days"
    )

    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual cost incurred"
    )

    actual_effort_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Actual effort in person-days"
    )

    # Verification and validation
    verification_required = models.BooleanField(
        default=True,
        help_text="Whether verification of remediation is required"
    )

    verification_method = models.TextField(
        blank=True,
        null=True,
        help_text="Method used to verify remediation"
    )

    verification_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of remediation verification"
    )

    verification_result = models.CharField(
        max_length=20,
        choices=[
            ('not_verified', 'Not Verified'),
            ('verified_effective', 'Verified Effective'),
            ('verified_partially', 'Verified Partially'),
            ('not_effective', 'Not Effective'),
            ('cannot_verify', 'Cannot Verify'),
        ],
        default='not_verified',
        help_text="Result of remediation verification"
    )

    # Approval and sign-off
    approval_required = models.BooleanField(
        default=False,
        help_text="Whether formal approval is required"
    )

    approved_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of the approver"
    )

    approved_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the approver"
    )

    approval_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of approval"
    )

    # Follow-up and monitoring
    follow_up_required = models.BooleanField(
        default=False,
        help_text="Whether follow-up monitoring is required"
    )

    follow_up_frequency = models.CharField(
        max_length=20,
        choices=[
            ('none', 'None'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
        ],
        default='none',
        help_text="Frequency of follow-up monitoring"
    )

    next_follow_up_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next follow-up"
    )

    follow_up_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from follow-up activities"
    )

    # Finding ownership and responsibility
    identified_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of person who identified the finding"
    )

    identified_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of person who identified the finding"
    )

    assigned_to_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID assigned to address the finding"
    )

    assigned_to_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username assigned to address the finding"
    )

    # Review and audit
    review_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from reviews"
    )

    audit_trail = models.JSONField(
        default=list,
        blank=True,
        help_text="Audit trail of changes and actions"
    )

    # Related entities
    related_requirement_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related requirement assessments"
    )

    related_control_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related controls"
    )

    related_asset_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related assets"
    )

    # Categorization and metadata
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Finding category for organization"
    )

    subcategory = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Finding subcategory"
    )

    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Finding tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    # Priority calculation
    priority_score = models.IntegerField(
        default=0,
        help_text="Calculated priority score (auto-updated)"
    )

    class Meta:
        db_table = "compliance_findings"
        indexes = [
            models.Index(fields=['compliance_assessment_id'], name='finding_assessment_idx'),
            models.Index(fields=['status'], name='finding_status_idx'),
            models.Index(fields=['severity'], name='finding_severity_idx'),
            models.Index(fields=['finding_type'], name='finding_type_idx'),
            models.Index(fields=['remediation_owner_user_id'], name='finding_owner_idx'),
            models.Index(fields=['remediation_deadline'], name='finding_deadline_idx'),
            models.Index(fields=['verification_result'], name='finding_verification_idx'),
            models.Index(fields=['priority_score'], name='finding_priority_idx'),
            models.Index(fields=['created_at'], name='finding_created_idx'),
        ]
        ordering = ['-priority_score', '-created_at']

    def create_finding(
        self,
        compliance_assessment_id: uuid.UUID,
        finding_id: str,
        finding_title: str,
        finding_description: str,
        finding_type: str,
        severity: str,
        framework: str,
        identified_by_user_id: Optional[uuid.UUID] = None,
        identified_by_username: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new compliance finding"""
        self.compliance_assessment_id = compliance_assessment_id
        self.finding_id = finding_id
        self.finding_title = finding_title
        self.finding_description = finding_description
        self.finding_type = finding_type
        self.severity = severity
        self.framework = framework
        self.identified_by_user_id = identified_by_user_id
        self.identified_by_username = identified_by_username
        self.tags = tags if tags is not None else []
        self.status = 'open'

        # Calculate initial priority
        self._calculate_priority_score()

        from .domain_events import ComplianceFindingCreated
        self._raise_event(ComplianceFindingCreated(
            aggregate_id=self.id,
            compliance_assessment_id=str(compliance_assessment_id),
            finding_id=finding_id,
            severity=severity,
            finding_type=finding_type
        ))

    def update_finding_details(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        root_cause: Optional[str] = None,
        impact_description: Optional[str] = None,
        evidence: Optional[str] = None
    ):
        """Update finding details"""
        if title:
            self.finding_title = title
        if description:
            self.finding_description = description
        if root_cause:
            self.root_cause = root_cause
        if impact_description:
            self.impact_description = impact_description
        if evidence:
            self.evidence = evidence

        from .domain_events import ComplianceFindingUpdated
        self._raise_event(ComplianceFindingUpdated(
            aggregate_id=self.id,
            finding_id=self.finding_id,
            updated_fields=['title', 'description', 'root_cause', 'impact', 'evidence']
        ))

    def assign_owner(
        self,
        assigned_to_user_id: uuid.UUID,
        assigned_to_username: str,
        remediation_owner_user_id: Optional[uuid.UUID] = None,
        remediation_owner_username: Optional[str] = None
    ):
        """Assign ownership for finding remediation"""
        self.assigned_to_user_id = assigned_to_user_id
        self.assigned_to_username = assigned_to_username

        if remediation_owner_user_id:
            self.remediation_owner_user_id = remediation_owner_user_id
            self.remediation_owner_username = remediation_owner_username

    def plan_remediation(
        self,
        remediation_plan: str,
        remediation_steps: List[Dict[str, Any]],
        deadline: Optional[timezone.date] = None,
        estimated_cost: Optional[float] = None,
        estimated_effort_days: Optional[int] = None
    ):
        """Plan remediation for the finding"""
        self.remediation_plan = remediation_plan
        self.remediation_steps = remediation_steps
        self.remediation_deadline = deadline
        self.remediation_status = 'planned'

        if estimated_cost is not None:
            self.estimated_cost = estimated_cost
        if estimated_effort_days is not None:
            self.estimated_effort_days = estimated_effort_days

        from .domain_events import ComplianceFindingUpdated
        self._raise_event(ComplianceFindingUpdated(
            aggregate_id=self.id,
            finding_id=self.finding_id,
            updated_fields=['remediation_plan']
        ))

    def start_remediation(self, start_date: Optional[timezone.date] = None):
        """Start remediation efforts"""
        if self.remediation_status == 'planned':
            self.remediation_status = 'in_progress'
            self.remediation_start_date = start_date or timezone.now().date()

            from .domain_events import ComplianceFindingStatusChanged
            self._raise_event(ComplianceFindingStatusChanged(
                aggregate_id=self.id,
                finding_id=self.finding_id,
                old_status='open',
                new_status='in_progress'
            ))

    def update_remediation_progress(self, progress_percentage: int, notes: Optional[str] = None):
        """Update remediation progress"""
        old_progress = self.remediation_progress_percentage
        self.remediation_progress_percentage = progress_percentage

        if notes:
            existing_notes = self.follow_up_notes or ""
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            self.follow_up_notes = f"{existing_notes}\n\n[{timestamp}] Progress: {progress_percentage}%\n{notes}".strip()

        # Auto-update status based on progress
        if progress_percentage >= 100:
            self.complete_remediation()
        elif progress_percentage > 0 and self.remediation_status == 'not_started':
            self.start_remediation()

    def complete_remediation(self, completion_date: Optional[timezone.date] = None, actual_cost: Optional[float] = None, actual_effort: Optional[int] = None):
        """Mark remediation as completed"""
        self.remediation_status = 'completed'
        self.remediation_completion_date = completion_date or timezone.now().date()
        self.remediation_progress_percentage = 100

        if actual_cost is not None:
            self.actual_cost = actual_cost
        if actual_effort is not None:
            self.actual_effort_days = actual_effort

        from .domain_events import ComplianceFindingRemediated
        self._raise_event(ComplianceFindingRemediated(
            aggregate_id=self.id,
            finding_id=self.finding_id,
            completion_date=str(self.remediation_completion_date)
        ))

    def verify_remediation(
        self,
        verification_method: str,
        verification_result: str,
        verification_date: Optional[timezone.date] = None
    ):
        """Verify remediation effectiveness"""
        self.verification_method = verification_method
        self.verification_result = verification_result
        self.verification_date = verification_date or timezone.now().date()

        # Update finding status based on verification
        if verification_result == 'verified_effective':
            self.close_finding('remediated')
        elif verification_result == 'not_effective':
            self.status = 'open'  # Re-open for further remediation

        from .domain_events import ComplianceFindingUpdated
        self._raise_event(ComplianceFindingUpdated(
            aggregate_id=self.id,
            finding_id=self.finding_id,
            updated_fields=['verification']
        ))

    def close_finding(self, closure_reason: str):
        """Close the finding"""
        if self.status in ['open', 'in_progress', 'remediated']:
            old_status = self.status
            self.status = 'closed'

            from .domain_events import ComplianceFindingClosed
            self._raise_event(ComplianceFindingClosed(
                aggregate_id=self.id,
                finding_id=self.finding_id,
                old_status=old_status,
                closure_reason=closure_reason
            ))

    def escalate_finding(self, escalation_reason: str):
        """Escalate the finding"""
        if self.status != 'escalated':
            old_status = self.status
            self.status = 'escalated'

            from .domain_events import ComplianceFindingStatusChanged
            self._raise_event(ComplianceFindingStatusChanged(
                aggregate_id=self.id,
                finding_id=self.finding_id,
                old_status=old_status,
                new_status='escalated',
                reason=escalation_reason
            ))

    def add_follow_up(self, follow_up_notes: str, next_follow_up_date: Optional[timezone.date] = None):
        """Add follow-up monitoring"""
        self.follow_up_required = True
        self.follow_up_frequency = 'quarterly'  # Default
        self.next_follow_up_date = next_follow_up_date

        existing_notes = self.follow_up_notes or ""
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
        self.follow_up_notes = f"{existing_notes}\n\n[{timestamp}] {follow_up_notes}".strip()

    def _calculate_priority_score(self):
        """Calculate priority score based on severity, type, and other factors"""
        # Base score from severity
        severity_scores = {
            'critical': 100,
            'high': 75,
            'medium': 50,
            'low': 25,
            'informational': 10
        }

        base_score = severity_scores.get(self.severity, 50)

        # Adjust for finding type
        type_multipliers = {
            'major_deficiency': 1.5,
            'non_conformity': 1.3,
            'minor_deficiency': 1.1,
            'observation': 1.0,
            'opportunity_for_improvement': 0.9,
            'positive_finding': 0.5
        }

        type_multiplier = type_multipliers.get(self.finding_type, 1.0)

        # Adjust for remediation status
        status_multipliers = {
            'open': 1.2,
            'in_progress': 1.0,
            'remediated': 0.8,
            'closed': 0.5,
            'dismissed': 0.3
        }

        status_multiplier = status_multipliers.get(self.status, 1.0)

        # Calculate final score
        self.priority_score = int(base_score * type_multiplier * status_multiplier)

    @property
    def is_overdue(self) -> bool:
        """Check if finding remediation is overdue"""
        if not self.remediation_deadline or self.remediation_status == 'completed':
            return False
        return timezone.now().date() > self.remediation_deadline

    @property
    def days_overdue(self) -> int:
        """Calculate days overdue"""
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.remediation_deadline).days

    @property
    def requires_immediate_attention(self) -> bool:
        """Check if finding requires immediate attention"""
        return (
            self.severity in ['critical', 'high'] and
            self.status in ['open', 'in_progress'] and
            (self.is_overdue or not self.remediation_owner_user_id)
        )

    @property
    def remediation_duration_days(self) -> Optional[int]:
        """Calculate remediation duration"""
        if not self.remediation_start_date or not self.remediation_completion_date:
            return None
        return (self.remediation_completion_date - self.remediation_start_date).days

    @property
    def cost_variance(self) -> Optional[float]:
        """Calculate cost variance"""
        if not self.estimated_cost or not self.actual_cost:
            return None
        return float(self.actual_cost - self.estimated_cost)

    @property
    def effort_variance(self) -> Optional[int]:
        """Calculate effort variance"""
        if not self.estimated_effort_days or not self.actual_effort_days:
            return None
        return self.actual_effort_days - self.estimated_effort_days

    def __str__(self):
        return f"ComplianceFinding({self.finding_id}: {self.finding_title} - {self.severity} - {self.status})"
