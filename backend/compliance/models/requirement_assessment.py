"""
Requirement Assessment Aggregate

Aggregate for managing individual requirement assessments within
compliance assessments, including evidence collection and validation.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class RequirementAssessment(AggregateRoot):
    """
    Requirement Assessment aggregate for evaluating individual compliance requirements.

    Manages the assessment of specific framework requirements, evidence collection,
    validation, and determination of compliance status for each requirement.
    """

    # Relationship to compliance assessment
    compliance_assessment_id = models.UUIDField(
        db_index=True,
        help_text="ID of the parent compliance assessment"
    )

    # Requirement identification
    requirement_id = models.CharField(
        max_length=100,
        help_text="Unique requirement identifier (e.g., 'AC-1', 'SI-3')"
    )

    requirement_title = models.CharField(
        max_length=500,
        help_text="Title/name of the requirement"
    )

    requirement_description = models.TextField(
        help_text="Full description of the requirement"
    )

    # Framework context
    framework = models.CharField(
        max_length=100,
        help_text="Compliance framework (e.g., 'NIST SP 800-53', 'ISO 27001')"
    )

    framework_section = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Framework section or category"
    )

    framework_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Framework version"
    )

    # Assessment status
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('evidence_collected', 'Evidence Collected'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('not_applicable', 'Not Applicable'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started',
        help_text="Current assessment status"
    )

    # Assessment results
    ASSESSMENT_RESULTS = [
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('compensating_control', 'Compensating Control'),
        ('not_applicable', 'Not Applicable'),
        ('insufficient_evidence', 'Insufficient Evidence'),
    ]

    assessment_result = models.CharField(
        max_length=25,
        choices=ASSESSMENT_RESULTS,
        blank=True,
        null=True,
        help_text="Result of the requirement assessment"
    )

    compliance_score = models.FloatField(
        default=0.0,
        help_text="Compliance score for this requirement (0.0-100.0)"
    )

    # Assessment details
    assessment_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed assessment notes and rationale"
    )

    assessment_methodology = models.TextField(
        blank=True,
        null=True,
        help_text="Methodology used for assessment"
    )

    # Evidence management
    evidence_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of evidence items supporting this assessment"
    )

    required_evidence_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Types of evidence required for compliance"
    )

    evidence_sufficiency = models.CharField(
        max_length=20,
        choices=[
            ('insufficient', 'Insufficient'),
            ('adequate', 'Adequate'),
            ('comprehensive', 'Comprehensive'),
        ],
        default='insufficient',
        help_text="Assessment of evidence sufficiency"
    )

    # Control implementation
    implemented_controls = models.JSONField(
        default=list,
        blank=True,
        help_text="Controls implemented to meet this requirement"
    )

    compensating_controls = models.JSONField(
        default=list,
        blank=True,
        help_text="Compensating controls used"
    )

    control_effectiveness = models.CharField(
        max_length=20,
        choices=[
            ('not_implemented', 'Not Implemented'),
            ('partially_implemented', 'Partially Implemented'),
            ('fully_implemented', 'Fully Implemented'),
            ('exceeds_requirements', 'Exceeds Requirements'),
        ],
        default='not_implemented',
        help_text="Effectiveness of implemented controls"
    )

    # Risk considerations
    associated_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="Risks associated with non-compliance"
    )

    risk_mitigation_effectiveness = models.CharField(
        max_length=20,
        choices=[
            ('inadequate', 'Inadequate'),
            ('adequate', 'Adequate'),
            ('strong', 'Strong'),
        ],
        default='adequate',
        help_text="Effectiveness of risk mitigation"
    )

    # Assessment ownership
    assessor_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the assessor"
    )

    assessor_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the assessor"
    )

    reviewer_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the reviewer"
    )

    reviewer_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the reviewer"
    )

    # Assessment dates
    assessment_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date assessment was started"
    )

    assessment_completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date assessment was completed"
    )

    review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of formal review"
    )

    approval_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of approval"
    )

    # Review and approval
    review_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from the review process"
    )

    approval_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from the approval process"
    )

    # Remediation planning
    remediation_required = models.BooleanField(
        default=False,
        help_text="Whether remediation is required"
    )

    remediation_plan = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed remediation plan"
    )

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

    remediation_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline for remediation completion"
    )

    remediation_status = models.CharField(
        max_length=20,
        choices=[
            ('not_started', 'Not Started'),
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='not_started',
        help_text="Status of remediation efforts"
    )

    # Related findings and exceptions
    related_finding_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related compliance findings"
    )

    exception_granted = models.BooleanField(
        default=False,
        help_text="Whether an exception has been granted"
    )

    exception_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of granted exception"
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
        help_text="Assessment priority"
    )

    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Assessment tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    # Integration fields
    mapped_control_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of mapped controls from Control Library"
    )

    mapped_risk_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of mapped risks from Risk Registers"
    )

    class Meta:
        db_table = "requirement_assessments"
        indexes = [
            models.Index(fields=['compliance_assessment_id'], name='req_assessment_parent_idx'),
            models.Index(fields=['status'], name='req_assessment_status_idx'),
            models.Index(fields=['assessment_result'], name='req_assessment_result_idx'),
            models.Index(fields=['framework'], name='req_assessment_framework_idx'),
            models.Index(fields=['assessor_user_id'], name='req_assessment_assessor_idx'),
            models.Index(fields=['remediation_deadline'], name='req_assessment_deadline_idx'),
            models.Index(fields=['compliance_score'], name='req_assessment_score_idx'),
            models.Index(fields=['created_at'], name='req_assessment_created_idx'),
        ]
        ordering = ['framework', 'requirement_id']
        unique_together = ['compliance_assessment_id', 'requirement_id']

    def create_requirement_assessment(
        self,
        compliance_assessment_id: uuid.UUID,
        requirement_id: str,
        requirement_title: str,
        requirement_description: str,
        framework: str,
        assessor_user_id: Optional[uuid.UUID] = None,
        assessor_username: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new requirement assessment"""
        self.compliance_assessment_id = compliance_assessment_id
        self.requirement_id = requirement_id
        self.requirement_title = requirement_title
        self.requirement_description = requirement_description
        self.framework = framework
        self.assessor_user_id = assessor_user_id
        self.assessor_username = assessor_username
        self.tags = tags if tags is not None else []
        self.status = 'not_started'

        from .domain_events import RequirementAssessmentCreated
        self._raise_event(RequirementAssessmentCreated(
            aggregate_id=self.id,
            compliance_assessment_id=str(compliance_assessment_id),
            requirement_id=requirement_id,
            framework=framework
        ))

    def start_assessment(self, start_date: Optional[timezone.date] = None):
        """Start the requirement assessment"""
        if self.status == 'not_started':
            self.status = 'in_progress'
            self.assessment_start_date = start_date or timezone.now().date()

            from .domain_events import RequirementAssessmentStatusChanged
            self._raise_event(RequirementAssessmentStatusChanged(
                aggregate_id=self.id,
                requirement_id=self.requirement_id,
                old_status='not_started',
                new_status='in_progress'
            ))

    def update_assessment_result(
        self,
        assessment_result: str,
        compliance_score: float,
        assessment_notes: Optional[str] = None,
        assessment_methodology: Optional[str] = None
    ):
        """Update the assessment result"""
        old_result = self.assessment_result
        old_score = self.compliance_score

        self.assessment_result = assessment_result
        self.compliance_score = compliance_score
        if assessment_notes:
            self.assessment_notes = assessment_notes
        if assessment_methodology:
            self.assessment_methodology = assessment_methodology

        # Update status and determine remediation needs
        if assessment_result == 'compliant':
            self.status = 'approved'
            self.remediation_required = False
        elif assessment_result == 'non_compliant':
            self.status = 'under_review'
            self.remediation_required = True
        elif assessment_result == 'compensating_control':
            self.status = 'under_review'
            self.remediation_required = False
        elif assessment_result == 'not_applicable':
            self.status = 'approved'
            self.remediation_required = False

        from .domain_events import RequirementAssessmentUpdated
        self._raise_event(RequirementAssessmentUpdated(
            aggregate_id=self.id,
            requirement_id=self.requirement_id,
            old_result=old_result,
            new_result=assessment_result,
            old_score=old_score,
            new_score=compliance_score
        ))

    def add_evidence(self, evidence_id: str, evidence_type: str):
        """Add evidence to the assessment"""
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)

            # Update evidence sufficiency based on types
            self._update_evidence_sufficiency()

            from .domain_events import RequirementAssessmentEvidenceAdded
            self._raise_event(RequirementAssessmentEvidenceAdded(
                aggregate_id=self.id,
                requirement_id=self.requirement_id,
                evidence_id=evidence_id,
                evidence_type=evidence_type
            ))

    def add_implemented_control(self, control_id: str, effectiveness: str = 'fully_implemented'):
        """Add an implemented control"""
        control_entry = {
            'control_id': control_id,
            'effectiveness': effectiveness,
            'added_at': str(timezone.now())
        }

        if not self.implemented_controls:
            self.implemented_controls = []
        self.implemented_controls.append(control_entry)

        # Update overall control effectiveness
        self._update_control_effectiveness()

    def add_compensating_control(self, control_id: str, justification: str):
        """Add a compensating control"""
        control_entry = {
            'control_id': control_id,
            'justification': justification,
            'approved': False,
            'added_at': str(timezone.now())
        }

        if not self.compensating_controls:
            self.compensating_controls = []
        self.compensating_controls.append(control_entry)

    def approve_assessment(
        self,
        reviewer_user_id: uuid.UUID,
        reviewer_username: str,
        approval_notes: Optional[str] = None
    ):
        """Approve the requirement assessment"""
        if self.status == 'under_review':
            self.status = 'approved'
            self.reviewer_user_id = reviewer_user_id
            self.reviewer_username = reviewer_username
            self.approval_date = timezone.now().date()
            self.approval_notes = approval_notes

            from .domain_events import RequirementAssessmentApproved
            self._raise_event(RequirementAssessmentApproved(
                aggregate_id=self.id,
                requirement_id=self.requirement_id,
                approved_by_user_id=str(reviewer_user_id),
                approval_date=str(self.approval_date)
            ))

    def submit_for_review(self):
        """Submit assessment for review"""
        if self.status in ['in_progress', 'evidence_collected']:
            self.status = 'under_review'
            self.review_date = timezone.now().date()

            from .domain_events import RequirementAssessmentStatusChanged
            self._raise_event(RequirementAssessmentStatusChanged(
                aggregate_id=self.id,
                requirement_id=self.requirement_id,
                old_status=self.status,
                new_status='under_review'
            ))

    def complete_assessment(self, completion_date: Optional[timezone.date] = None):
        """Mark assessment as completed"""
        self.assessment_completion_date = completion_date or timezone.now().date()

        # If approved, status remains approved
        # If not approved, status indicates completion but needs review

        from .domain_events import RequirementAssessmentStatusChanged
        self._raise_event(RequirementAssessmentStatusChanged(
            aggregate_id=self.id,
            requirement_id=self.requirement_id,
            old_status=self.status,
            new_status=f"{self.status}_completed"
        ))

    def plan_remediation(
        self,
        remediation_plan: str,
        remediation_owner_user_id: uuid.UUID,
        remediation_owner_username: str,
        deadline: Optional[timezone.date] = None
    ):
        """Plan remediation for non-compliant requirement"""
        self.remediation_required = True
        self.remediation_plan = remediation_plan
        self.remediation_owner_user_id = remediation_owner_user_id
        self.remediation_owner_username = remediation_owner_username
        self.remediation_deadline = deadline
        self.remediation_status = 'planned'

    def update_remediation_status(self, new_status: str):
        """Update remediation status"""
        old_status = self.remediation_status
        self.remediation_status = new_status

        if new_status == 'completed':
            # Check if remediation resolved the compliance issue
            self._evaluate_post_remediation_compliance()

    def grant_exception(self, exception_id: uuid.UUID):
        """Grant an exception for this requirement"""
        self.exception_granted = True
        self.exception_id = exception_id
        self.assessment_result = 'compensating_control'  # Exception treated as compensating control

    def _update_evidence_sufficiency(self):
        """Update evidence sufficiency based on collected evidence"""
        evidence_count = len(self.evidence_ids)
        required_types = len(self.required_evidence_types)

        if evidence_count == 0:
            self.evidence_sufficiency = 'insufficient'
        elif evidence_count >= required_types:
            self.evidence_sufficiency = 'comprehensive'
        else:
            self.evidence_sufficiency = 'adequate'

    def _update_control_effectiveness(self):
        """Update overall control effectiveness"""
        if not self.implemented_controls:
            self.control_effectiveness = 'not_implemented'
            return

        # Determine overall effectiveness
        effectiveness_levels = {
            'not_implemented': 0,
            'partially_implemented': 1,
            'fully_implemented': 2,
            'exceeds_requirements': 3
        }

        max_effectiveness = max(
            effectiveness_levels.get(ctrl.get('effectiveness', 'not_implemented'), 0)
            for ctrl in self.implemented_controls
        )

        reverse_map = {v: k for k, v in effectiveness_levels.items()}
        self.control_effectiveness = reverse_map.get(max_effectiveness, 'not_implemented')

    def _evaluate_post_remediation_compliance(self):
        """Evaluate compliance after remediation completion"""
        # This would typically trigger a re-assessment
        # For now, we'll assume remediation improves compliance
        if self.assessment_result == 'non_compliant':
            self.assessment_result = 'compliant'
            self.compliance_score = 100.0
            self.status = 'approved'

    @property
    def is_compliant(self) -> bool:
        """Check if requirement is compliant"""
        return self.assessment_result in ['compliant', 'compensating_control', 'not_applicable']

    @property
    def requires_immediate_attention(self) -> bool:
        """Check if requirement requires immediate attention"""
        return (
            self.assessment_result == 'non_compliant' and
            self.remediation_required and
            self.remediation_status in ['not_started', 'cancelled']
        )

    @property
    def is_overdue(self) -> bool:
        """Check if assessment is overdue"""
        if not self.remediation_deadline or self.remediation_status == 'completed':
            return False
        return timezone.now().date() > self.remediation_deadline

    @property
    def days_until_deadline(self) -> Optional[int]:
        """Calculate days until remediation deadline"""
        if not self.remediation_deadline:
            return None
        return (self.remediation_deadline - timezone.now().date()).days

    @property
    def assessment_duration_days(self) -> Optional[int]:
        """Calculate assessment duration"""
        if not self.assessment_start_date or not self.assessment_completion_date:
            return None
        return (self.assessment_completion_date - self.assessment_start_date).days

    def __str__(self):
        return f"RequirementAssessment({self.requirement_id}: {self.requirement_title} - {self.assessment_result})"
