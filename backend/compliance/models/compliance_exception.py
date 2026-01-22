"""
Compliance Exception Aggregate

Aggregate for managing compliance exceptions, deviations, and waivers
from compliance requirements with approval workflows and expiration tracking.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class ComplianceException(AggregateRoot):
    """
    Compliance Exception aggregate for managing deviations from compliance requirements.

    Handles exception requests, approval workflows, expiration tracking,
    and risk acceptance for non-compliant situations.
    """

    # Relationship to compliance assessment
    compliance_assessment_id = models.UUIDField(
        db_index=True,
        help_text="ID of the compliance assessment this exception relates to"
    )

    # Exception identification
    exception_id = models.CharField(
        max_length=100,
        help_text="Unique exception identifier (e.g., 'EXC-2024-001')"
    )

    exception_title = models.CharField(
        max_length=500,
        help_text="Title/summary of the exception"
    )

    exception_description = models.TextField(
        help_text="Detailed description of the exception request"
    )

    # Exception classification
    EXCEPTION_TYPES = [
        ('temporary_waiver', 'Temporary Waiver'),
        ('permanent_exception', 'Permanent Exception'),
        ('compensating_control', 'Compensating Control'),
        ('risk_acceptance', 'Risk Acceptance'),
        ('alternative_implementation', 'Alternative Implementation'),
        ('delayed_compliance', 'Delayed Compliance'),
    ]

    exception_type = models.CharField(
        max_length=25,
        choices=EXCEPTION_TYPES,
        default='temporary_waiver',
        help_text="Type of compliance exception"
    )

    # Framework and requirement context
    framework = models.CharField(
        max_length=100,
        help_text="Compliance framework this exception relates to"
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

    # Exception status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
        ('superseded', 'Superseded'),
    ]

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current status of the exception"
    )

    # Business justification
    business_justification = models.TextField(
        help_text="Business justification for the exception"
    )

    risk_assessment = models.TextField(
        blank=True,
        null=True,
        help_text="Risk assessment supporting the exception"
    )

    impact_assessment = models.TextField(
        blank=True,
        null=True,
        help_text="Impact assessment of granting the exception"
    )

    # Compensating controls (if applicable)
    compensating_controls = models.JSONField(
        default=list,
        blank=True,
        help_text="Compensating controls implemented"
    )

    compensating_controls_effectiveness = models.CharField(
        max_length=20,
        choices=[
            ('not_assessed', 'Not Assessed'),
            ('inadequate', 'Inadequate'),
            ('adequate', 'Adequate'),
            ('strong', 'Strong'),
            ('exceeds', 'Exceeds Requirements'),
        ],
        default='not_assessed',
        help_text="Effectiveness of compensating controls"
    )

    # Exception duration and expiration
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when exception becomes effective"
    )

    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when exception expires"
    )

    auto_renewal = models.BooleanField(
        default=False,
        help_text="Whether exception auto-renews"
    )

    renewal_period_months = models.IntegerField(
        null=True,
        blank=True,
        help_text="Auto-renewal period in months"
    )

    max_renewals = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of renewals allowed"
    )

    renewal_count = models.IntegerField(
        default=0,
        help_text="Number of times exception has been renewed"
    )

    # Approval workflow
    approval_required = models.BooleanField(
        default=True,
        help_text="Whether formal approval is required"
    )

    approval_workflow = models.CharField(
        max_length=50,
        choices=[
            ('single_approver', 'Single Approver'),
            ('dual_approval', 'Dual Approval'),
            ('committee_review', 'Committee Review'),
            ('board_approval', 'Board Approval'),
        ],
        default='single_approver',
        help_text="Approval workflow required"
    )

    # Primary approval
    approved_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of primary approver"
    )

    approved_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of primary approver"
    )

    approval_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of primary approval"
    )

    approval_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from primary approval"
    )

    # Secondary approval (for dual approval workflows)
    secondary_approved_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of secondary approver"
    )

    secondary_approved_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of secondary approver"
    )

    secondary_approval_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of secondary approval"
    )

    secondary_approval_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from secondary approval"
    )

    # Rejection details
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejection"
    )

    rejected_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of person who rejected"
    )

    rejected_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of person who rejected"
    )

    rejection_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of rejection"
    )

    # Exception ownership and responsibility
    requested_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of person who requested the exception"
    )

    requested_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of person who requested the exception"
    )

    owned_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID responsible for exception management"
    )

    owned_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username responsible for exception management"
    )

    # Monitoring and review
    monitoring_required = models.BooleanField(
        default=True,
        help_text="Whether ongoing monitoring is required"
    )

    monitoring_frequency = models.CharField(
        max_length=20,
        choices=[
            ('continuous', 'Continuous'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
        ],
        default='quarterly',
        help_text="Frequency of exception monitoring"
    )

    last_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last exception review"
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled review"
    )

    review_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from exception reviews"
    )

    # Risk management
    associated_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of associated risks"
    )

    risk_acceptance_level = models.CharField(
        max_length=20,
        choices=[
            ('not_assessed', 'Not Assessed'),
            ('accepted', 'Accepted'),
            ('conditionally_accepted', 'Conditionally Accepted'),
            ('not_accepted', 'Not Accepted'),
        ],
        default='not_assessed',
        help_text="Level of risk acceptance"
    )

    risk_mitigation_plan = models.TextField(
        blank=True,
        null=True,
        help_text="Plan to mitigate accepted risks"
    )

    # Cost and resource impact
    implementation_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost of implementing exception/compensation"
    )

    ongoing_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Ongoing cost of maintaining exception"
    )

    resource_impact = models.TextField(
        blank=True,
        null=True,
        help_text="Impact on resources and operations"
    )

    # Supporting documentation
    supporting_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of supporting documents"
    )

    evidence_of_effectiveness = models.JSONField(
        default=list,
        blank=True,
        help_text="Evidence demonstrating exception effectiveness"
    )

    # Related entities
    related_finding_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related compliance findings"
    )

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

    # Exception conditions and constraints
    conditions = models.TextField(
        blank=True,
        null=True,
        help_text="Conditions that must be met for exception to remain valid"
    )

    constraints = models.TextField(
        blank=True,
        null=True,
        help_text="Constraints and limitations of the exception"
    )

    triggers_for_review = models.TextField(
        blank=True,
        null=True,
        help_text="Triggers that would require exception review"
    )

    # Audit and compliance tracking
    audit_trail = models.JSONField(
        default=list,
        blank=True,
        help_text="Audit trail of changes and decisions"
    )

    compliance_impact = models.TextField(
        blank=True,
        null=True,
        help_text="Overall impact on compliance posture"
    )

    # Metadata
    priority = models.CharField(
        max_length=10,
        choices=[
            ('critical', 'Critical'),
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        default='medium',
        help_text="Exception priority"
    )

    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Exception category for organization"
    )

    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Exception tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    class Meta:
        db_table = "compliance_exceptions"
        indexes = [
            models.Index(fields=['compliance_assessment_id'], name='exception_assessment_idx'),
            models.Index(fields=['status'], name='exception_status_idx'),
            models.Index(fields=['exception_type'], name='exception_type_idx'),
            models.Index(fields=['approved_by_user_id'], name='exception_approver_idx'),
            models.Index(fields=['end_date'], name='exception_expiry_idx'),
            models.Index(fields=['next_review_date'], name='exception_review_idx'),
            models.Index(fields=['created_at'], name='exception_created_idx'),
        ]
        ordering = ['-created_at']

    def create_exception(
        self,
        compliance_assessment_id: uuid.UUID,
        exception_id: str,
        exception_title: str,
        exception_description: str,
        exception_type: str,
        business_justification: str,
        framework: str,
        requested_by_user_id: Optional[uuid.UUID] = None,
        requested_by_username: Optional[str] = None,
        start_date: Optional[timezone.date] = None,
        end_date: Optional[timezone.date] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new compliance exception"""
        self.compliance_assessment_id = compliance_assessment_id
        self.exception_id = exception_id
        self.exception_title = exception_title
        self.exception_description = exception_description
        self.exception_type = exception_type
        self.business_justification = business_justification
        self.framework = framework
        self.requested_by_user_id = requested_by_user_id
        self.requested_by_username = requested_by_username
        self.start_date = start_date
        self.end_date = end_date
        self.tags = tags if tags is not None else []
        self.status = 'draft'

        from .domain_events import ComplianceExceptionCreated
        self._raise_event(ComplianceExceptionCreated(
            aggregate_id=self.id,
            compliance_assessment_id=str(compliance_assessment_id),
            exception_id=exception_id,
            exception_type=exception_type
        ))

    def submit_for_approval(self):
        """Submit exception for approval"""
        if self.status == 'draft':
            self.status = 'submitted'

            from .domain_events import ComplianceExceptionUpdated
            self._raise_event(ComplianceExceptionUpdated(
                aggregate_id=self.id,
                exception_id=self.exception_id,
                status_change='draft → submitted'
            ))

    def approve_exception(
        self,
        approved_by_user_id: uuid.UUID,
        approved_by_username: str,
        approval_notes: Optional[str] = None,
        secondary_approver_user_id: Optional[uuid.UUID] = None,
        secondary_approver_username: Optional[str] = None
    ):
        """Approve the compliance exception"""
        if self.status == 'submitted' or self.status == 'under_review':
            self.status = 'approved'
            self.approved_by_user_id = approved_by_user_id
            self.approved_by_username = approved_by_username
            self.approval_date = timezone.now().date()
            self.approval_notes = approval_notes

            if secondary_approver_user_id:
                self.secondary_approved_by_user_id = secondary_approver_user_id
                self.secondary_approved_by_username = secondary_approver_username
                self.secondary_approval_date = timezone.now().date()

            from .domain_events import ComplianceExceptionApproved
            self._raise_event(ComplianceExceptionApproved(
                aggregate_id=self.id,
                exception_id=self.exception_id,
                approved_by_user_id=str(approved_by_user_id),
                approval_date=str(self.approval_date)
            ))

    def reject_exception(
        self,
        rejected_by_user_id: uuid.UUID,
        rejected_by_username: str,
        rejection_reason: str
    ):
        """Reject the compliance exception"""
        if self.status in ['submitted', 'under_review']:
            self.status = 'rejected'
            self.rejected_by_user_id = rejected_by_user_id
            self.rejected_by_username = rejected_by_username
            self.rejection_date = timezone.now().date()
            self.rejection_reason = rejection_reason

            from .domain_events import ComplianceExceptionRejected
            self._raise_event(ComplianceExceptionRejected(
                aggregate_id=self.id,
                exception_id=self.exception_id,
                rejected_by_user_id=str(rejected_by_user_id),
                rejection_reason=rejection_reason
            ))

    def extend_exception(
        self,
        new_end_date: timezone.date,
        extension_reason: str,
        approved_by_user_id: uuid.UUID,
        approved_by_username: str
    ):
        """Extend the exception duration"""
        old_end_date = self.end_date
        self.end_date = new_end_date
        self.renewal_count += 1

        # Add to audit trail
        audit_entry = {
            'action': 'extended',
            'old_end_date': str(old_end_date),
            'new_end_date': str(new_end_date),
            'reason': extension_reason,
            'approved_by': str(approved_by_user_id),
            'approved_at': str(timezone.now())
        }

        if not self.audit_trail:
            self.audit_trail = []
        self.audit_trail.append(audit_entry)

        from .domain_events import ComplianceExceptionExtended
        self._raise_event(ComplianceExceptionExtended(
            aggregate_id=self.id,
            exception_id=self.exception_id,
            new_end_date=str(new_end_date),
            approved_by_user_id=str(approved_by_user_id)
        ))

    def conduct_review(self, review_notes: Optional[str] = None, next_review_date: Optional[timezone.date] = None):
        """Conduct an exception review"""
        self.last_review_date = timezone.now().date()
        self.next_review_date = next_review_date or self._calculate_next_review_date()

        if review_notes:
            existing_notes = self.review_notes or ""
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            self.review_notes = f"{existing_notes}\n\n[{timestamp}] {review_notes}".strip()

        from .domain_events import ComplianceExceptionUpdated
        self._raise_event(ComplianceExceptionUpdated(
            aggregate_id=self.id,
            exception_id=self.exception_id,
            review_conducted=str(self.last_review_date)
        ))

    def revoke_exception(self, revocation_reason: str, revoked_by_user_id: uuid.UUID, revoked_by_username: str):
        """Revoke the exception"""
        if self.status == 'approved':
            self.status = 'revoked'

            # Add to audit trail
            audit_entry = {
                'action': 'revoked',
                'reason': revocation_reason,
                'revoked_by': str(revoked_by_user_id),
                'revoked_at': str(timezone.now())
            }

            if not self.audit_trail:
                self.audit_trail = []
            self.audit_trail.append(audit_entry)

            from .domain_events import ComplianceExceptionUpdated
            self._raise_event(ComplianceExceptionUpdated(
                aggregate_id=self.id,
                exception_id=self.exception_id,
                status_change='approved → revoked',
                reason=revocation_reason
            ))

    def check_expiration(self):
        """Check if exception has expired"""
        if self.end_date and self.status == 'approved':
            if timezone.now().date() > self.end_date:
                self.status = 'expired'

                from .domain_events import ComplianceExceptionExpired
                self._raise_event(ComplianceExceptionExpired(
                    aggregate_id=self.id,
                    exception_id=self.exception_id,
                    expiry_date=str(self.end_date)
                ))

    def auto_renew(self):
        """Auto-renew exception if enabled and within limits"""
        if (self.auto_renewal and
            self.status == 'approved' and
            self.end_date and
            self.renewal_period_months and
            (self.max_renewals is None or self.renewal_count < self.max_renewals)):

            from datetime import timedelta
            new_end_date = self.end_date + timedelta(days=self.renewal_period_months * 30)

            self.extend_exception(
                new_end_date=new_end_date,
                extension_reason="Auto-renewal",
                approved_by_user_id=self.approved_by_user_id,
                approved_by_username=self.approved_by_username
            )

    def _calculate_next_review_date(self) -> timezone.date:
        """Calculate next review date based on monitoring frequency"""
        base_date = self.last_review_date or self.approval_date or timezone.now().date()

        if self.monitoring_frequency == 'continuous':
            return base_date + timezone.timedelta(days=90)  # Quarterly for practical purposes
        elif self.monitoring_frequency == 'monthly':
            return base_date + timezone.timedelta(days=30)
        elif self.monitoring_frequency == 'quarterly':
            return base_date + timezone.timedelta(days=90)
        elif self.monitoring_frequency == 'annually':
            return base_date + timezone.timedelta(days=365)
        else:
            return base_date + timezone.timedelta(days=90)  # Default quarterly

    @property
    def is_expired(self) -> bool:
        """Check if exception has expired"""
        if not self.end_date:
            return False
        return timezone.now().date() > self.end_date

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until expiry"""
        if not self.end_date:
            return None
        return (self.end_date - timezone.now().date()).days

    @property
    def is_due_for_review(self) -> bool:
        """Check if exception is due for review"""
        if not self.next_review_date:
            return False
        return timezone.now().date() >= self.next_review_date

    @property
    def requires_immediate_attention(self) -> bool:
        """Check if exception requires immediate attention"""
        return (
            self.status in ['submitted', 'under_review'] or
            (self.is_expired and self.status == 'approved') or
            self.is_due_for_review
        )

    @property
    def duration_days(self) -> Optional[int]:
        """Calculate exception duration"""
        if not self.start_date or not self.end_date:
            return None
        return (self.end_date - self.start_date).days

    @property
    def days_active(self) -> Optional[int]:
        """Calculate days exception has been active"""
        if not self.start_date or self.status != 'approved':
            return None

        end_date = self.end_date if self.end_date else timezone.now().date()
        return (end_date - self.start_date).days

    def __str__(self):
        return f"ComplianceException({self.exception_id}: {self.exception_title} - {self.exception_type} - {self.status})"
