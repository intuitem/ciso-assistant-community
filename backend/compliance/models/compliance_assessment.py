"""
Compliance Assessment Aggregate

Aggregate for orchestrating comprehensive compliance assessments across
multiple frameworks, managing assessment lifecycle, and coordinating
evidence collection and validation.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class ComplianceAssessment(AggregateRoot):
    """
    Compliance Assessment aggregate for comprehensive framework assessments.

    Orchestrates multi-framework compliance assessments, coordinates evidence
    collection, manages assessment lifecycle, and provides consolidated
    compliance reporting across all applicable frameworks.
    """

    # Assessment identification
    name = models.CharField(
        max_length=255,
        help_text="Name of the compliance assessment"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the assessment scope and objectives"
    )

    assessment_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique assessment identifier (e.g., CMP-2024-001)"
    )

    # Assessment scope and ownership
    scope = models.CharField(
        max_length=100,
        help_text="Assessment scope (e.g., 'Enterprise', 'System', 'Department')"
    )

    assessment_type = models.CharField(
        max_length=50,
        choices=[
            ('gap_analysis', 'Gap Analysis'),
            ('full_assessment', 'Full Assessment'),
            ('targeted_review', 'Targeted Review'),
            ('continuous_monitoring', 'Continuous Monitoring'),
            ('certification_prep', 'Certification Preparation'),
        ],
        default='full_assessment',
        help_text="Type of compliance assessment"
    )

    # Framework and standard information
    primary_framework = models.CharField(
        max_length=100,
        help_text="Primary compliance framework (e.g., 'NIST SP 800-53', 'ISO 27001')"
    )

    framework_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Framework version or revision"
    )

    additional_frameworks = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional frameworks included in this assessment"
    )

    # Assessment lifecycle
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('evidence_collection', 'Evidence Collection'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('superseded', 'Superseded'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned',
        help_text="Current status of the assessment"
    )

    priority = models.CharField(
        max_length=10,
        choices=[
            ('critical', 'Critical'),
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        default='medium',
        help_text="Assessment priority"
    )

    # Assessment dates
    planned_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned assessment start date"
    )

    actual_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual assessment start date"
    )

    planned_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned assessment completion date"
    )

    actual_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual assessment completion date"
    )

    # Assessment ownership and responsibility
    assessment_lead_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the assessment lead"
    )

    assessment_lead_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the assessment lead"
    )

    assessment_team = models.JSONField(
        default=list,
        blank=True,
        help_text="Assessment team members and their roles"
    )

    # Target information (what's being assessed)
    target_type = models.CharField(
        max_length=50,
        choices=[
            ('organization', 'Organization'),
            ('system', 'System'),
            ('asset', 'Asset'),
            ('process', 'Process'),
            ('department', 'Department'),
            ('project', 'Project'),
        ],
        help_text="Type of target being assessed"
    )

    target_id = models.UUIDField(
        db_index=True,
        help_text="ID of the target being assessed"
    )

    target_name = models.CharField(
        max_length=255,
        help_text="Cached name of the assessment target"
    )

    # Assessment scope boundaries
    included_scopes = models.JSONField(
        default=list,
        blank=True,
        help_text="Specific scopes included in the assessment"
    )

    excluded_scopes = models.JSONField(
        default=list,
        blank=True,
        help_text="Scopes explicitly excluded from assessment"
    )

    assessment_boundaries = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of assessment boundaries"
    )

    # Framework requirements and controls
    requirement_assessment_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of requirement assessments in this compliance assessment"
    )

    control_assessment_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of control assessments in this compliance assessment"
    )

    # Evidence management
    evidence_collection_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of evidence collections for this assessment"
    )

    required_evidence_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Types of evidence required for this assessment"
    )

    # Assessment results and findings
    compliance_finding_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of findings from this assessment"
    )

    compliance_exception_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of exceptions granted for this assessment"
    )

    # Assessment scoring and metrics
    overall_compliance_score = models.FloatField(
        default=0.0,
        help_text="Overall compliance score (0.0-100.0)"
    )

    compliance_level = models.CharField(
        max_length=20,
        choices=[
            ('non_compliant', 'Non-Compliant'),
            ('limited', 'Limited'),
            ('moderate', 'Moderate'),
            ('substantial', 'Substantial'),
            ('full', 'Full'),
        ],
        default='limited',
        help_text="Overall compliance level"
    )

    # Requirement coverage statistics
    total_requirements = models.IntegerField(
        default=0,
        help_text="Total number of requirements in scope"
    )

    assessed_requirements = models.IntegerField(
        default=0,
        help_text="Number of requirements assessed"
    )

    compliant_requirements = models.IntegerField(
        default=0,
        help_text="Number of requirements found compliant"
    )

    non_compliant_requirements = models.IntegerField(
        default=0,
        help_text="Number of requirements found non-compliant"
    )

    not_applicable_requirements = models.IntegerField(
        default=0,
        help_text="Number of requirements deemed not applicable"
    )

    compensating_controls_count = models.IntegerField(
        default=0,
        help_text="Number of compensating controls identified"
    )

    # Risk and impact analysis
    risk_assessment_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of risk assessments related to this compliance assessment"
    )

    residual_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="Residual risks identified during assessment"
    )

    # Approval and sign-off
    approval_required = models.BooleanField(
        default=True,
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
        help_text="Date of formal approval"
    )

    approval_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from the approval process"
    )

    # Review and audit
    review_frequency = models.CharField(
        max_length=50,
        choices=[
            ('continuous', 'Continuous'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
            ('biennial', 'Biennial'),
        ],
        default='annually',
        help_text="Frequency of assessment reviews"
    )

    last_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last assessment review"
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled review"
    )

    review_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from assessment reviews"
    )

    # Certification and accreditation
    certification_body = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Certification body or auditor"
    )

    certification_standard = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Specific certification standard"
    )

    certification_status = models.CharField(
        max_length=50,
        choices=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('submitted', 'Submitted'),
            ('under_review', 'Under Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
        ],
        default='not_started',
        help_text="Certification status"
    )

    certification_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of certification achievement"
    )

    certification_expiry = models.DateField(
        null=True,
        blank=True,
        help_text="Date of certification expiry"
    )

    # Integration with other contexts
    related_asset_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Related asset IDs from Asset context"
    )

    related_control_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Related control IDs from Control Library context"
    )

    related_risk_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Related risk IDs from Risk Registers context"
    )

    # Metadata and customization
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Assessment tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional assessment properties"
    )

    assessment_methodology = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed assessment methodology used"
    )

    tools_used = models.JSONField(
        default=list,
        blank=True,
        help_text="Tools and systems used in the assessment"
    )

    # Audit and compliance tracking
    regulatory_requirements = models.JSONField(
        default=list,
        blank=True,
        help_text="Regulatory requirements this assessment addresses"
    )

    compliance_deadlines = models.JSONField(
        default=list,
        blank=True,
        help_text="Important compliance deadlines"
    )

    class Meta:
        db_table = "compliance_assessments"
        indexes = [
            models.Index(fields=['status'], name='compliance_assessment_status_idx'),
            models.Index(fields=['target_type', 'target_id'], name='compliance_assessment_target_idx'),
            models.Index(fields=['primary_framework'], name='compliance_assessment_framework_idx'),
            models.Index(fields=['assessment_lead_user_id'], name='compliance_assessment_lead_idx'),
            models.Index(fields=['planned_completion_date'], name='compliance_assessment_due_idx'),
            models.Index(fields=['overall_compliance_score'], name='compliance_assessment_score_idx'),
            models.Index(fields=['certification_status'], name='compliance_assessment_cert_idx'),
            models.Index(fields=['next_review_date'], name='compliance_assessment_review_idx'),
            models.Index(fields=['created_at'], name='compliance_assessment_created_idx'),
        ]
        ordering = ['-created_at']

    def create_assessment(
        self,
        assessment_id: str,
        name: str,
        target_type: str,
        target_id: uuid.UUID,
        target_name: str,
        primary_framework: str,
        scope: str = 'System',
        assessment_lead_user_id: Optional[uuid.UUID] = None,
        assessment_lead_username: Optional[str] = None,
        planned_start_date: Optional[timezone.date] = None,
        planned_completion_date: Optional[timezone.date] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new compliance assessment"""
        self.assessment_id = assessment_id
        self.name = name
        self.target_type = target_type
        self.target_id = target_id
        self.target_name = target_name
        self.primary_framework = primary_framework
        self.scope = scope
        self.assessment_lead_user_id = assessment_lead_user_id
        self.assessment_lead_username = assessment_lead_username
        self.planned_start_date = planned_start_date
        self.planned_completion_date = planned_completion_date
        self.description = description
        self.tags = tags if tags is not None else []
        self.status = 'planned'

        # Set default review schedule
        if planned_completion_date:
            self._calculate_next_review_date()

        from .domain_events import ComplianceAssessmentCreated
        self._raise_event(ComplianceAssessmentCreated(
            aggregate_id=self.id,
            assessment_id=assessment_id,
            name=name,
            primary_framework=primary_framework,
            target_type=target_type
        ))

    def start_assessment(self, start_date: Optional[timezone.date] = None):
        """Start the compliance assessment"""
        if self.status == 'planned':
            self.status = 'in_progress'
            self.actual_start_date = start_date or timezone.now().date()

            from .domain_events import ComplianceAssessmentStarted
            self._raise_event(ComplianceAssessmentStarted(
                aggregate_id=self.id,
                assessment_id=self.assessment_id,
                start_date=str(self.actual_start_date)
            ))

    def update_progress(
        self,
        new_status: Optional[str] = None,
        assessed_requirements: Optional[int] = None,
        compliant_requirements: Optional[int] = None,
        non_compliant_requirements: Optional[int] = None,
        not_applicable_requirements: Optional[int] = None,
        overall_score: Optional[float] = None
    ):
        """Update assessment progress"""
        old_status = self.status
        old_score = self.overall_compliance_score

        if new_status:
            self.status = new_status
        if assessed_requirements is not None:
            self.assessed_requirements = assessed_requirements
        if compliant_requirements is not None:
            self.compliant_requirements = compliant_requirements
        if non_compliant_requirements is not None:
            self.non_compliant_requirements = non_compliant_requirements
        if not_applicable_requirements is not None:
            self.not_applicable_requirements = not_applicable_requirements
        if overall_score is not None:
            self.overall_compliance_score = overall_score
            self.compliance_level = self._calculate_compliance_level(overall_score)

        # Recalculate total requirements
        self.total_requirements = (
            self.compliant_requirements +
            self.non_compliant_requirements +
            self.not_applicable_requirements
        )

        from .domain_events import ComplianceAssessmentProgressUpdated
        self._raise_event(ComplianceAssessmentProgressUpdated(
            aggregate_id=self.id,
            assessment_id=self.assessment_id,
            old_status=old_status,
            new_status=self.status,
            old_score=old_score,
            new_score=self.overall_compliance_score,
            progress_percentage=self.progress_percentage
        ))

    def add_requirement_assessment(self, requirement_assessment_id: str):
        """Add a requirement assessment to this compliance assessment"""
        if requirement_assessment_id not in self.requirement_assessment_ids:
            self.requirement_assessment_ids.append(requirement_assessment_id)

            from .domain_events import ComplianceAssessmentRequirementAdded
            self._raise_event(ComplianceAssessmentRequirementAdded(
                aggregate_id=self.id,
                assessment_id=self.assessment_id,
                requirement_assessment_id=requirement_assessment_id
            ))

    def add_control_assessment(self, control_assessment_id: str):
        """Add a control assessment to this compliance assessment"""
        if control_assessment_id not in self.control_assessment_ids:
            self.control_assessment_ids.append(control_assessment_id)

            from .domain_events import ComplianceAssessmentControlAdded
            self._raise_event(ComplianceAssessmentControlAdded(
                aggregate_id=self.id,
                assessment_id=self.assessment_id,
                control_assessment_id=control_assessment_id
            ))

    def add_finding(self, finding_id: str):
        """Add a compliance finding to this assessment"""
        if finding_id not in self.compliance_finding_ids:
            self.compliance_finding_ids.append(finding_id)

            from .domain_events import ComplianceAssessmentFindingAdded
            self._raise_event(ComplianceAssessmentFindingAdded(
                aggregate_id=self.id,
                assessment_id=self.assessment_id,
                finding_id=finding_id
            ))

    def add_exception(self, exception_id: str):
        """Add a compliance exception to this assessment"""
        if exception_id not in self.compliance_exception_ids:
            self.compliance_exception_ids.append(exception_id)

            from .domain_events import ComplianceAssessmentExceptionAdded
            self._raise_event(ComplianceAssessmentExceptionAdded(
                aggregate_id=self.id,
                assessment_id=self.assessment_id,
                exception_id=exception_id
            ))

    def submit_for_approval(self):
        """Submit assessment for formal approval"""
        if self.status in ['in_progress', 'evidence_collection', 'review']:
            self.status = 'review'

            from .domain_events import ComplianceAssessmentSubmittedForApproval
            self._raise_event(ComplianceAssessmentSubmittedForApproval(
                aggregate_id=self.id,
                assessment_id=self.assessment_id,
                compliance_score=self.overall_compliance_score
            ))

    def approve_assessment(
        self,
        approved_by_user_id: uuid.UUID,
        approved_by_username: str,
        approval_notes: Optional[str] = None
    ):
        """Approve the compliance assessment"""
        if self.status == 'review':
            self.status = 'approved'
            self.approved_by_user_id = approved_by_user_id
            self.approved_by_username = approved_by_username
            self.approval_date = timezone.now().date()
            self.approval_notes = approval_notes

            from .domain_events import ComplianceAssessmentApproved
            self._raise_event(ComplianceAssessmentApproved(
                aggregate_id=self.id,
                assessment_id=self.assessment_id,
                approved_by_user_id=str(approved_by_user_id),
                approval_date=str(self.approval_date)
            ))

    def complete_assessment(self, completion_date: Optional[timezone.date] = None):
        """Mark assessment as completed"""
        if self.status in ['approved', 'in_progress']:
            self.status = 'completed'
            self.actual_completion_date = completion_date or timezone.now().date()

            from .domain_events import ComplianceAssessmentCompleted
            self._raise_event(ComplianceAssessmentCompleted(
                aggregate_id=self.id,
                assessment_id=self.assessment_id,
                completion_date=str(self.actual_completion_date),
                final_score=self.overall_compliance_score
            ))

    def conduct_review(self, review_notes: Optional[str] = None, next_review_date: Optional[timezone.date] = None):
        """Conduct an assessment review"""
        self.last_review_date = timezone.now().date()
        self.next_review_date = next_review_date or self._calculate_next_review_date()

        if review_notes:
            existing_notes = self.review_notes or ""
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            self.review_notes = f"{existing_notes}\n\n[{timestamp}] {review_notes}".strip()

        from .domain_events import ComplianceAssessmentReviewed
        self._raise_event(ComplianceAssessmentReviewed(
            aggregate_id=self.id,
            assessment_id=self.assessment_id,
            review_date=str(self.last_review_date)
        ))

    def update_certification_status(self, new_status: str, certification_date: Optional[timezone.date] = None,
                                  expiry_date: Optional[timezone.date] = None):
        """Update certification status"""
        old_status = self.certification_status
        self.certification_status = new_status

        if certification_date:
            self.certification_date = certification_date
        if expiry_date:
            self.certification_expiry = expiry_date

        from .domain_events import ComplianceAssessmentCertificationUpdated
        self._raise_event(ComplianceAssessmentCertificationUpdated(
            aggregate_id=self.id,
            assessment_id=self.assessment_id,
            old_status=old_status,
            new_status=new_status,
            certification_date=str(certification_date) if certification_date else None
        ))

    def _calculate_compliance_level(self, score: float) -> str:
        """Calculate compliance level from score"""
        if score >= 90:
            return 'full'
        elif score >= 75:
            return 'substantial'
        elif score >= 50:
            return 'moderate'
        elif score >= 25:
            return 'limited'
        else:
            return 'non_compliant'

    def _calculate_next_review_date(self) -> timezone.date:
        """Calculate next review date based on frequency"""
        base_date = self.planned_completion_date or self.actual_completion_date or timezone.now().date()

        if self.review_frequency == 'continuous':
            return base_date + timezone.timedelta(days=90)  # Quarterly for practical purposes
        elif self.review_frequency == 'monthly':
            return base_date + timezone.timedelta(days=30)
        elif self.review_frequency == 'quarterly':
            return base_date + timezone.timedelta(days=90)
        elif self.review_frequency == 'annually':
            return base_date + timezone.timedelta(days=365)
        elif self.review_frequency == 'biennial':
            return base_date + timezone.timedelta(days=730)
        else:
            return base_date + timezone.timedelta(days=365)  # Default annual

    @property
    def progress_percentage(self) -> float:
        """Calculate assessment progress percentage"""
        if self.total_requirements == 0:
            return 0.0
        return round((self.assessed_requirements / self.total_requirements) * 100, 2)

    @property
    def compliance_percentage(self) -> float:
        """Calculate compliance percentage"""
        if self.assessed_requirements == 0:
            return 0.0
        return round((self.compliant_requirements / self.assessed_requirements) * 100, 2)

    @property
    def is_overdue(self) -> bool:
        """Check if assessment is overdue"""
        if not self.planned_completion_date:
            return False
        return timezone.now().date() > self.planned_completion_date and self.status != 'completed'

    @property
    def days_overdue(self) -> int:
        """Calculate days overdue"""
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.planned_completion_date).days

    @property
    def is_due_soon(self) -> bool:
        """Check if assessment is due within 30 days"""
        if not self.planned_completion_date or self.status == 'completed':
            return False
        days_until_due = (self.planned_completion_date - timezone.now().date()).days
        return 0 <= days_until_due <= 30

    @property
    def requires_attention(self) -> bool:
        """Check if assessment requires immediate attention"""
        return (
            self.is_overdue or
            self.status == 'rejected' or
            (self.compliance_level in ['non_compliant', 'limited'] and self.status == 'completed')
        )

    @property
    def assessment_duration_days(self) -> Optional[int]:
        """Calculate assessment duration in days"""
        if not self.actual_start_date or not self.actual_completion_date:
            return None
        return (self.actual_completion_date - self.actual_start_date).days

    def __str__(self):
        return f"ComplianceAssessment({self.assessment_id}: {self.name} - {self.overall_compliance_score}%)"
