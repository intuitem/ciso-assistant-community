"""
BCP Plan Aggregate

Aggregate for managing Business Continuity Plans including risk assessment,
recovery strategies, and plan testing.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class BCPPlan(AggregateRoot):
    """
    BCP Plan aggregate for comprehensive business continuity planning.

    Manages business continuity plans including risk assessments, recovery strategies,
    plan development, testing, and maintenance.
    """

    # Plan identification
    plan_name = models.CharField(
        max_length=255,
        help_text="Name of the BCP plan"
    )

    plan_description = models.TextField(
        help_text="Description of the BCP plan scope and objectives"
    )

    plan_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique plan identifier (e.g., BCP-2024-001)"
    )

    # Plan scope and coverage
    scope = models.CharField(
        max_length=100,
        help_text="Plan scope (e.g., 'Enterprise', 'Department', 'System')"
    )

    covered_processes = models.JSONField(
        default=list,
        blank=True,
        help_text="Business processes covered by this plan"
    )

    covered_assets = models.JSONField(
        default=list,
        blank=True,
        help_text="Critical assets covered by this plan"
    )

    geographical_scope = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Geographical areas covered by the plan"
    )

    # Plan status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('superseded', 'Superseded'),
        ('archived', 'Archived'),
    ]

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current plan status"
    )

    version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Plan version"
    )

    # Plan ownership and responsibility
    plan_owner_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of plan owner"
    )

    plan_owner_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of plan owner"
    )

    plan_coordinator_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of plan coordinator"
    )

    plan_coordinator_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of plan coordinator"
    )

    # Risk assessment
    risk_assessment = models.JSONField(
        default=dict,
        blank=True,
        help_text="Business impact analysis and risk assessment"
    )

    bia_completed = models.BooleanField(
        default=False,
        help_text="Whether Business Impact Analysis is completed"
    )

    bia_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date BIA was completed"
    )

    # Recovery strategies
    recovery_strategies = models.JSONField(
        default=list,
        blank=True,
        help_text="Recovery strategies for different scenarios"
    )

    # Recovery objectives
    rto_objectives = models.JSONField(
        default=dict,
        blank=True,
        help_text="Recovery Time Objectives by process/asset"
    )

    rpo_objectives = models.JSONField(
        default=dict,
        blank=True,
        help_text="Recovery Point Objectives by process/asset"
    )

    # Plan components
    emergency_contacts = models.JSONField(
        default=list,
        blank=True,
        help_text="Emergency contact information"
    )

    response_procedures = models.JSONField(
        default=list,
        blank=True,
        help_text="Incident response procedures"
    )

    recovery_procedures = models.JSONField(
        default=list,
        blank=True,
        help_text="Recovery procedures"
    )

    communication_plan = models.JSONField(
        default=dict,
        blank=True,
        help_text="Communication plan for stakeholders"
    )

    # Testing and maintenance
    test_schedule = models.JSONField(
        default=dict,
        blank=True,
        help_text="Testing schedule and procedures"
    )

    last_test_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last plan test"
    )

    next_test_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled test"
    )

    test_results = models.JSONField(
        default=list,
        blank=True,
        help_text="Results from plan tests"
    )

    # Plan approval and review
    approved_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User ID of approver"
    )

    approved_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of approver"
    )

    approval_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of plan approval"
    )

    review_schedule = models.CharField(
        max_length=20,
        choices=[
            ('annual', 'Annual'),
            ('biannual', 'Biannual'),
            ('quarterly', 'Quarterly'),
        ],
        default='annual',
        help_text="Plan review frequency"
    )

    last_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last plan review"
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled review"
    )

    # Effectiveness and metrics
    effectiveness_rating = models.CharField(
        max_length=10,
        choices=[
            ('poor', 'Poor'),
            ('fair', 'Fair'),
            ('good', 'Good'),
            ('excellent', 'Excellent'),
        ],
        blank=True,
        null=True,
        help_text="Overall plan effectiveness rating"
    )

    improvement_areas = models.JSONField(
        default=list,
        blank=True,
        help_text="Identified areas for improvement"
    )

    # Integration with other contexts
    related_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="Related risks from Risk Registers"
    )

    related_assets = models.JSONField(
        default=list,
        blank=True,
        help_text="Related assets from Asset context"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Plan tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    class Meta:
        db_table = "bcp_plans"
        indexes = [
            models.Index(fields=['status'], name='bcp_plan_status_idx'),
            models.Index(fields=['scope'], name='bcp_plan_scope_idx'),
            models.Index(fields=['plan_owner_user_id'], name='bcp_plan_owner_idx'),
            models.Index(fields=['next_test_date'], name='bcp_plan_test_idx'),
            models.Index(fields=['next_review_date'], name='bcp_plan_review_idx'),
            models.Index(fields=['created_at'], name='bcp_plan_created_idx'),
        ]
        ordering = ['-created_at']

    def create_plan(
        self,
        plan_id: str,
        plan_name: str,
        plan_description: str,
        scope: str,
        plan_owner_user_id: Optional[uuid.UUID] = None,
        plan_owner_username: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new BCP plan"""
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.plan_description = plan_description
        self.scope = scope
        self.plan_owner_user_id = plan_owner_user_id
        self.plan_owner_username = plan_owner_username
        self.tags = tags if tags is not None else []
        self.status = 'draft'

        from .domain_events import BCPPlanCreated
        self._raise_event(BCPPlanCreated(
            aggregate_id=self.id,
            plan_id=plan_id,
            plan_name=plan_name,
            scope=scope
        ))

    def perform_business_impact_analysis(self, bia_data: Dict[str, Any]):
        """Perform Business Impact Analysis"""
        self.risk_assessment = bia_data
        self.bia_completed = True
        self.bia_date = timezone.now().date()

        from .domain_events import BCPPlanBIACompleted
        self._raise_event(BCPPlanBIACompleted(
            aggregate_id=self.id,
            plan_id=self.plan_id,
            bia_date=str(self.bia_date)
        ))

    def define_recovery_objectives(self, rto_data: Dict[str, Any], rpo_data: Dict[str, Any]):
        """Define recovery objectives"""
        self.rto_objectives = rto_data
        self.rpo_objectives = rpo_data

        from .domain_events import BCPPlanRecoveryObjectivesDefined
        self._raise_event(BCPPlanRecoveryObjectivesDefined(
            aggregate_id=self.id,
            plan_id=self.plan_id
        ))

    def develop_recovery_strategies(self, strategies: List[Dict[str, Any]]):
        """Develop recovery strategies"""
        self.recovery_strategies = strategies

        from .domain_events import BCPPlanStrategiesDeveloped
        self._raise_event(BCPPlanStrategiesDeveloped(
            aggregate_id=self.id,
            plan_id=self.plan_id,
            strategy_count=len(strategies)
        ))

    def approve_plan(self, approver_user_id: uuid.UUID, approver_username: str):
        """Approve the BCP plan"""
        if self.status in ['draft', 'review']:
            self.status = 'approved'
            self.approved_by_user_id = approver_user_id
            self.approved_by_username = approver_username
            self.approval_date = timezone.now().date()

            from .domain_events import BCPPlanApproved
            self._raise_event(BCPPlanApproved(
                aggregate_id=self.id,
                plan_id=self.plan_id,
                approved_by_user_id=str(approver_user_id)
            ))

    def activate_plan(self):
        """Activate the BCP plan"""
        if self.status == 'approved':
            self.status = 'active'
            self._calculate_next_review_date()

            from .domain_events import BCPPlanActivated
            self._raise_event(BCPPlanActivated(
                aggregate_id=self.id,
                plan_id=self.plan_id
            ))

    def conduct_test(self, test_results: Dict[str, Any]):
        """Conduct plan testing"""
        self.last_test_date = timezone.now().date()
        self.test_results.append(test_results)
        self._calculate_next_test_date()

        # Update effectiveness based on test results
        if test_results.get('overall_rating'):
            self.effectiveness_rating = test_results['overall_rating']

        from .domain_events import BCPPlanTested
        self._raise_event(BCPPlanTested(
            aggregate_id=self.id,
            plan_id=self.plan_id,
            test_date=str(self.last_test_date),
            results=test_results
        ))

    def conduct_review(self, review_notes: Optional[str] = None):
        """Conduct plan review"""
        self.last_review_date = timezone.now().date()
        self._calculate_next_review_date()

        from .domain_events import BCPPlanReviewed
        self._raise_event(BCPPlanReviewed(
            aggregate_id=self.id,
            plan_id=self.plan_id,
            review_date=str(self.last_review_date)
        ))

    def _calculate_next_test_date(self):
        """Calculate next test date"""
        if not self.last_test_date:
            return

        # Default to annual testing, but could be based on test_schedule
        self.next_test_date = self.last_test_date + timezone.timedelta(days=365)

    def _calculate_next_review_date(self):
        """Calculate next review date"""
        base_date = self.last_review_date or self.approval_date or timezone.now().date()

        if self.review_schedule == 'annual':
            days = 365
        elif self.review_schedule == 'biannual':
            days = 182
        elif self.review_schedule == 'quarterly':
            days = 90
        else:
            days = 365

        self.next_review_date = base_date + timezone.timedelta(days=days)

    @property
    def is_active(self) -> bool:
        """Check if plan is active"""
        return self.status == 'active'

    @property
    def requires_testing(self) -> bool:
        """Check if plan requires testing"""
        if not self.next_test_date:
            return True
        return timezone.now().date() >= self.next_test_date

    @property
    def requires_review(self) -> bool:
        """Check if plan requires review"""
        if not self.next_review_date:
            return True
        return timezone.now().date() >= self.next_review_date

    @property
    def test_compliance_percentage(self) -> float:
        """Calculate testing compliance"""
        if not self.test_schedule or not self.last_test_date:
            return 0.0

        # Simplified calculation - could be enhanced
        days_since_last_test = (timezone.now().date() - self.last_test_date).days
        test_frequency_days = 365  # Default annual

        if days_since_last_test <= test_frequency_days:
            return 100.0
        elif days_since_last_test <= test_frequency_days * 1.2:  # 20% grace period
            return 80.0
        else:
            return 0.0

    def __str__(self):
        return f"BCPPlan({self.plan_id}: {self.plan_name} - {self.scope} - {self.status})"
