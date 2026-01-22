"""
Asset Risk Aggregate

Aggregate for managing risks associated with specific assets,
including threat assessments, vulnerability analysis, and risk scoring.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class AssetRisk(AggregateRoot):
    """
    Asset Risk aggregate for comprehensive asset risk management.

    Tracks risks specific to assets including threats, vulnerabilities,
    impact assessments, and risk treatment plans.
    """

    # Relationships
    asset_id = models.UUIDField(
        db_index=True,
        help_text="ID of the asset this risk assessment applies to"
    )

    asset_name = models.CharField(
        max_length=255,
        help_text="Cached name of the asset for performance"
    )

    # Risk identification
    risk_title = models.CharField(
        max_length=500,
        help_text="Title/description of the risk"
    )

    risk_description = models.TextField(
        help_text="Detailed description of the risk scenario"
    )

    risk_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique risk identifier (e.g., RISK-AST-001)"
    )

    # Risk categorization
    RISK_CATEGORIES = [
        ('confidentiality', 'Confidentiality'),
        ('integrity', 'Integrity'),
        ('availability', 'Availability'),
        ('financial', 'Financial'),
        ('reputational', 'Reputational'),
        ('operational', 'Operational'),
        ('compliance', 'Compliance'),
        ('strategic', 'Strategic'),
    ]

    risk_category = models.CharField(
        max_length=20,
        choices=RISK_CATEGORIES,
        default='operational',
        help_text="Primary category of the risk"
    )

    risk_subcategory = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="More specific risk subcategory"
    )

    # Threat and vulnerability details
    threat_source = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Source of the threat (e.g., hacker, natural disaster, insider)"
    )

    threat_vector = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="How the threat is executed (e.g., phishing, physical access, SQL injection)"
    )

    vulnerability_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the vulnerability being exploited"
    )

    cve_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Associated CVE identifiers"
    )

    cwe_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Associated CWE identifiers"
    )

    # Risk assessment scores (CVSS-based)
    cvss_base_score = models.FloatField(
        default=0.0,
        help_text="CVSS base score (0.0-10.0)"
    )

    cvss_temporal_score = models.FloatField(
        default=0.0,
        help_text="CVSS temporal score"
    )

    cvss_environmental_score = models.FloatField(
        default=0.0,
        help_text="CVSS environmental score"
    )

    # Custom risk scoring
    inherent_likelihood = models.IntegerField(
        default=1,
        help_text="Inherent likelihood score (1-5)"
    )

    inherent_impact = models.IntegerField(
        default=1,
        help_text="Inherent impact score (1-5)"
    )

    inherent_risk_score = models.IntegerField(
        default=1,
        help_text="Inherent risk score (calculated)"
    )

    residual_likelihood = models.IntegerField(
        default=1,
        help_text="Residual likelihood after controls"
    )

    residual_impact = models.IntegerField(
        default=1,
        help_text="Residual impact after controls"
    )

    residual_risk_score = models.IntegerField(
        default=1,
        help_text="Residual risk score (calculated)"
    )

    # Risk levels
    RISK_LEVELS = [
        ('very_low', 'Very Low'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('very_high', 'Very High'),
        ('critical', 'Critical'),
    ]

    inherent_risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVELS,
        default='moderate',
        help_text="Inherent risk level"
    )

    residual_risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVELS,
        default='moderate',
        help_text="Residual risk level after controls"
    )

    # Risk appetite and thresholds
    risk_appetite = models.CharField(
        max_length=20,
        choices=RISK_LEVELS,
        default='moderate',
        help_text="Organization's risk appetite for this risk"
    )

    risk_threshold = models.IntegerField(
        default=3,
        help_text="Risk score threshold for treatment (1-5)"
    )

    requires_treatment = models.BooleanField(
        default=False,
        help_text="Whether this risk requires treatment"
    )

    # Risk treatment plan
    treatment_strategy = models.CharField(
        max_length=50,
        choices=[
            ('accept', 'Accept'),
            ('avoid', 'Avoid'),
            ('mitigate', 'Mitigate'),
            ('transfer', 'Transfer'),
            ('monitor', 'Monitor Only'),
        ],
        blank=True,
        null=True,
        help_text="Risk treatment strategy"
    )

    treatment_plan = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed treatment plan"
    )

    treatment_owner_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID responsible for treatment implementation"
    )

    treatment_owner_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of treatment owner"
    )

    # Treatment implementation
    treatment_status = models.CharField(
        max_length=20,
        choices=[
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('implemented', 'Implemented'),
            ('effective', 'Effective'),
            ('ineffective', 'Ineffective'),
        ],
        default='planned',
        help_text="Status of treatment implementation"
    )

    treatment_implemented_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date treatment was implemented"
    )

    treatment_effective_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date treatment became effective"
    )

    # Treatment milestones
    treatment_milestones = models.JSONField(
        default=list,
        blank=True,
        help_text="Treatment implementation milestones"
    )

    # Risk monitoring and review
    monitoring_frequency = models.CharField(
        max_length=50,
        choices=[
            ('continuous', 'Continuous'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
        ],
        default='monthly',
        help_text="How often this risk should be monitored"
    )

    last_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last risk review"
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled review"
    )

    review_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from risk reviews"
    )

    # Risk ownership and responsibility
    risk_owner_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the risk owner"
    )

    risk_owner_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the risk owner"
    )

    risk_manager_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the risk manager"
    )

    risk_manager_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the risk manager"
    )

    # Supporting information
    supporting_evidence = models.JSONField(
        default=list,
        blank=True,
        help_text="Evidence supporting the risk assessment"
    )

    related_findings = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related findings or vulnerabilities"
    )

    related_controls = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related controls that address this risk"
    )

    # Risk tags and metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Risk tags for organization and filtering"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional risk properties"
    )

    # Assessment metadata
    assessed_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of person who performed assessment"
    )

    assessed_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of assessor"
    )

    assessment_methodology = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Risk assessment methodology used"
    )

    confidence_level = models.CharField(
        max_length=20,
        choices=[
            ('very_low', 'Very Low'),
            ('low', 'Low'),
            ('moderate', 'Moderate'),
            ('high', 'High'),
            ('very_high', 'Very High'),
        ],
        default='moderate',
        help_text="Confidence level in the assessment"
    )

    class Meta:
        db_table = "asset_risks"
        indexes = [
            models.Index(fields=['asset_id', 'residual_risk_level'], name='asset_risk_level_idx'),
            models.Index(fields=['risk_category'], name='asset_risk_category_idx'),
            models.Index(fields=['treatment_status'], name='asset_risk_treatment_idx'),
            models.Index(fields=['next_review_date'], name='asset_risk_review_idx'),
            models.Index(fields=['requires_treatment'], name='asset_risk_treatment_needed_idx'),
            models.Index(fields=['residual_risk_score'], name='asset_risk_score_idx'),
            models.Index(fields=['created_at'], name='asset_risk_created_idx'),
        ]
        ordering = ['-residual_risk_score', '-created_at']

    def create_asset_risk(
        self,
        asset_id: uuid.UUID,
        asset_name: str,
        risk_id: str,
        risk_title: str,
        risk_description: str,
        risk_category: str = 'operational',
        inherent_likelihood: int = 3,
        inherent_impact: int = 3,
        assessed_by_user_id: Optional[uuid.UUID] = None,
        assessed_by_username: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new asset risk assessment"""
        self.asset_id = asset_id
        self.asset_name = asset_name
        self.risk_id = risk_id
        self.risk_title = risk_title
        self.risk_description = risk_description
        self.risk_category = risk_category
        self.inherent_likelihood = inherent_likelihood
        self.inherent_impact = inherent_impact
        self.assessed_by_user_id = assessed_by_user_id
        self.assessed_by_username = assessed_by_username
        self.tags = tags if tags is not None else []

        # Calculate inherent risk score
        self.inherent_risk_score = self._calculate_risk_score(inherent_likelihood, inherent_impact)
        self.inherent_risk_level = self._get_risk_level(self.inherent_risk_score)

        # Initially, residual = inherent
        self.residual_likelihood = inherent_likelihood
        self.residual_impact = inherent_impact
        self.residual_risk_score = self.inherent_risk_score
        self.residual_risk_level = self.inherent_risk_level

        # Determine if treatment is required
        self.requires_treatment = self.residual_risk_score >= self.risk_threshold

        from .domain_events import AssetRiskCreated
        self._raise_event(AssetRiskCreated(
            aggregate_id=self.id,
            asset_id=str(asset_id),
            risk_id=risk_id,
            risk_title=risk_title,
            inherent_risk_score=self.inherent_risk_score
        ))

    def update_risk_assessment(
        self,
        likelihood: Optional[int] = None,
        impact: Optional[int] = None,
        cvss_base_score: Optional[float] = None,
        risk_category: Optional[str] = None,
        threat_source: Optional[str] = None,
        threat_vector: Optional[str] = None
    ):
        """Update the risk assessment details"""
        old_score = self.inherent_risk_score

        if likelihood is not None:
            self.inherent_likelihood = likelihood
        if impact is not None:
            self.inherent_impact = impact
        if cvss_base_score is not None:
            self.cvss_base_score = cvss_base_score
        if risk_category is not None:
            self.risk_category = risk_category
        if threat_source is not None:
            self.threat_source = threat_source
        if threat_vector is not None:
            self.threat_vector = threat_vector

        # Recalculate risk scores
        self.inherent_risk_score = self._calculate_risk_score(self.inherent_likelihood, self.inherent_impact)
        self.inherent_risk_level = self._get_risk_level(self.inherent_risk_score)

        # Update residual if no treatments applied yet
        if self.treatment_status == 'planned':
            self.residual_likelihood = self.inherent_likelihood
            self.residual_impact = self.inherent_impact
            self.residual_risk_score = self.inherent_risk_score
            self.residual_risk_level = self.inherent_risk_level
            self.requires_treatment = self.residual_risk_score >= self.risk_threshold

        from .domain_events import AssetRiskAssessmentUpdated
        self._raise_event(AssetRiskAssessmentUpdated(
            aggregate_id=self.id,
            risk_id=self.risk_id,
            old_score=old_score,
            new_score=self.inherent_risk_score
        ))

    def define_treatment_plan(
        self,
        treatment_strategy: str,
        treatment_plan: str,
        treatment_owner_user_id: Optional[uuid.UUID] = None,
        treatment_owner_username: Optional[str] = None
    ):
        """Define a risk treatment plan"""
        self.treatment_strategy = treatment_strategy
        self.treatment_plan = treatment_plan
        self.treatment_owner_user_id = treatment_owner_user_id
        self.treatment_owner_username = treatment_owner_username
        self.treatment_status = 'planned'

        from .domain_events import AssetRiskTreatmentPlanDefined
        self._raise_event(AssetRiskTreatmentPlanDefined(
            aggregate_id=self.id,
            risk_id=self.risk_id,
            treatment_strategy=treatment_strategy
        ))

    def implement_treatment(self, implementation_date: Optional[timezone.date] = None):
        """Mark treatment as implemented"""
        if self.treatment_status == 'planned' or self.treatment_status == 'in_progress':
            self.treatment_status = 'implemented'
            self.treatment_implemented_date = implementation_date or timezone.now().date()

            from .domain_events import AssetRiskTreatmentImplemented
            self._raise_event(AssetRiskTreatmentImplemented(
                aggregate_id=self.id,
                risk_id=self.risk_id,
                implementation_date=str(self.treatment_implemented_date)
            ))

    def update_residual_risk(
        self,
        residual_likelihood: int,
        residual_impact: int,
        effective_date: Optional[timezone.date] = None
    ):
        """Update residual risk after treatment implementation"""
        old_score = self.residual_risk_score

        self.residual_likelihood = residual_likelihood
        self.residual_impact = residual_impact
        self.residual_risk_score = self._calculate_risk_score(residual_likelihood, residual_impact)
        self.residual_risk_level = self._get_risk_level(self.residual_risk_score)
        self.treatment_effective_date = effective_date or timezone.now().date()
        self.treatment_status = 'effective'
        self.requires_treatment = self.residual_risk_score >= self.risk_threshold

        from .domain_events import AssetRiskResidualUpdated
        self._raise_event(AssetRiskResidualUpdated(
            aggregate_id=self.id,
            risk_id=self.risk_id,
            old_residual_score=old_score,
            new_residual_score=self.residual_risk_score
        ))

    def add_milestone(self, milestone_description: str, target_date: timezone.date, status: str = 'pending'):
        """Add a treatment milestone"""
        milestone = {
            'id': str(uuid.uuid4()),
            'description': milestone_description,
            'target_date': str(target_date),
            'status': status,
            'created_at': str(timezone.now())
        }

        if not self.treatment_milestones:
            self.treatment_milestones = []
        self.treatment_milestones.append(milestone)

        from .domain_events import AssetRiskMilestoneAdded
        self._raise_event(AssetRiskMilestoneAdded(
            aggregate_id=self.id,
            risk_id=self.risk_id,
            milestone_id=milestone['id'],
            description=milestone_description
        ))

    def update_milestone_status(self, milestone_id: str, status: str, actual_date: Optional[timezone.date] = None):
        """Update milestone status"""
        for milestone in self.treatment_milestones:
            if milestone['id'] == milestone_id:
                old_status = milestone['status']
                milestone['status'] = status
                milestone['updated_at'] = str(timezone.now())

                if actual_date and status == 'completed':
                    milestone['actual_date'] = str(actual_date)

                from .domain_events import AssetRiskMilestoneUpdated
                self._raise_event(AssetRiskMilestoneUpdated(
                    aggregate_id=self.id,
                    risk_id=self.risk_id,
                    milestone_id=milestone_id,
                    old_status=old_status,
                    new_status=status
                ))
                break

    def conduct_review(self, review_notes: Optional[str] = None, next_review_date: Optional[timezone.date] = None):
        """Conduct a risk review"""
        self.last_review_date = timezone.now().date()
        self.next_review_date = next_review_date
        if review_notes:
            existing_notes = self.review_notes or ""
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            self.review_notes = f"{existing_notes}\n\n[{timestamp}] {review_notes}".strip()

        from .domain_events import AssetRiskReviewed
        self._raise_event(AssetRiskReviewed(
            aggregate_id=self.id,
            risk_id=self.risk_id,
            review_date=str(self.last_review_date)
        ))

    def add_evidence(self, evidence_type: str, evidence_data: Dict[str, Any]):
        """Add supporting evidence"""
        evidence_entry = {
            'id': str(uuid.uuid4()),
            'type': evidence_type,
            'data': evidence_data,
            'added_at': str(timezone.now()),
            'added_by': str(getattr(self, 'updated_by', None))
        }

        if not self.supporting_evidence:
            self.supporting_evidence = []
        self.supporting_evidence.append(evidence_entry)

    def assign_owner(self, owner_user_id: uuid.UUID, owner_username: str, manager_user_id: Optional[uuid.UUID] = None, manager_username: Optional[str] = None):
        """Assign risk ownership"""
        self.risk_owner_user_id = owner_user_id
        self.risk_owner_username = owner_username
        if manager_user_id:
            self.risk_manager_user_id = manager_user_id
            self.risk_manager_username = manager_username

        from .domain_events import AssetRiskOwnerAssigned
        self._raise_event(AssetRiskOwnerAssigned(
            aggregate_id=self.id,
            risk_id=self.risk_id,
            owner_user_id=str(owner_user_id),
            owner_username=owner_username
        ))

    def _calculate_risk_score(self, likelihood: int, impact: int) -> int:
        """Calculate risk score from likelihood and impact"""
        return likelihood * impact

    def _get_risk_level(self, score: int) -> str:
        """Determine risk level from score"""
        if score <= 2:
            return 'very_low'
        elif score <= 6:
            return 'low'
        elif score <= 12:
            return 'moderate'
        elif score <= 20:
            return 'high'
        else:
            return 'critical'

    @property
    def is_treated(self) -> bool:
        """Check if risk has effective treatment"""
        return self.treatment_status in ['effective']

    @property
    def risk_reduction_achieved(self) -> float:
        """Calculate percentage of risk reduction achieved"""
        if self.inherent_risk_score == 0:
            return 0.0
        reduction = self.inherent_risk_score - self.residual_risk_score
        return round((reduction / self.inherent_risk_score) * 100, 2)

    @property
    def requires_attention(self) -> bool:
        """Check if risk requires immediate attention"""
        return (self.residual_risk_level in ['high', 'critical'] and
                not self.is_treated and
                self.requires_treatment)

    @property
    def is_overdue_for_review(self) -> bool:
        """Check if risk is overdue for review"""
        if not self.next_review_date:
            return False
        return timezone.now().date() > self.next_review_date

    @property
    def treatment_completion_percentage(self) -> float:
        """Calculate treatment completion percentage"""
        if not self.treatment_milestones:
            return 0.0

        completed = sum(1 for m in self.treatment_milestones if m.get('status') == 'completed')
        return round((completed / len(self.treatment_milestones)) * 100, 2)

    def __str__(self):
        return f"AssetRisk({self.risk_id}: {self.risk_title} - {self.residual_risk_level})"
