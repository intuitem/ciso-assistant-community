"""
Risk Register Aggregate

Aggregate for managing master risk registers that consolidate and
aggregate risks across all domains (asset, third party, business).
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class RiskRegister(AggregateRoot):
    """
    Risk Register aggregate for consolidated risk management.

    Serves as the master risk register that aggregates risks from all
    domains, provides consolidated reporting, and enables organization-wide
    risk management and oversight.
    """

    # Register identification
    name = models.CharField(
        max_length=255,
        help_text="Name of the risk register"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the risk register scope and purpose"
    )

    register_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique register identifier (e.g., RR-2024, RR-IT)"
    )

    # Register scope and ownership
    scope = models.CharField(
        max_length=100,
        help_text="Scope of the register (e.g., 'Enterprise', 'IT', 'Finance')"
    )

    owning_organization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Organization or department owning this register"
    )

    owner_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the register owner"
    )

    owner_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the register owner"
    )

    # Register status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('superseded', 'Superseded'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Status of the risk register"
    )

    # Risk aggregation (embedded ID arrays)
    asset_risk_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of asset risks included in this register"
    )

    third_party_risk_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of third party risks included in this register"
    )

    business_risk_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of business risks included in this register"
    )

    risk_scenario_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of risk scenarios included in this register"
    )

    # Consolidated statistics (computed fields)
    total_risks = models.IntegerField(
        default=0,
        help_text="Total number of risks in the register"
    )

    critical_risks = models.IntegerField(
        default=0,
        help_text="Number of critical risks"
    )

    high_risks = models.IntegerField(
        default=0,
        help_text="Number of high risks"
    )

    moderate_risks = models.IntegerField(
        default=0,
        help_text="Number of moderate risks"
    )

    low_risks = models.IntegerField(
        default=0,
        help_text="Number of low risks"
    )

    risks_requiring_treatment = models.IntegerField(
        default=0,
        help_text="Number of risks requiring treatment"
    )

    risks_under_treatment = models.IntegerField(
        default=0,
        help_text="Number of risks currently under treatment"
    )

    risks_effectively_treated = models.IntegerField(
        default=0,
        help_text="Number of risks with effective treatment"
    )

    # Risk appetite and thresholds
    risk_appetite_statement = models.TextField(
        blank=True,
        null=True,
        help_text="Organization's risk appetite statement"
    )

    risk_appetite_critical_threshold = models.IntegerField(
        default=20,
        help_text="Risk score threshold for critical risks"
    )

    risk_appetite_high_threshold = models.IntegerField(
        default=15,
        help_text="Risk score threshold for high risks"
    )

    risk_appetite_moderate_threshold = models.IntegerField(
        default=10,
        help_text="Risk score threshold for moderate risks"
    )

    # Reporting and review
    reporting_frequency = models.CharField(
        max_length=50,
        choices=[
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
        ],
        default='monthly',
        help_text="Frequency of risk register reporting"
    )

    last_report_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last risk report"
    )

    next_report_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled report"
    )

    last_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last register review"
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled review"
    )

    # Risk heat map data (computed)
    risk_heat_map = models.JSONField(
        default=dict,
        blank=True,
        help_text="Risk heat map data for visualization"
    )

    # Register configuration
    included_risk_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Risk categories included in this register"
    )

    excluded_risk_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Risk categories excluded from this register"
    )

    risk_scoring_methodology = models.CharField(
        max_length=100,
        default='Likelihood x Impact',
        help_text="Risk scoring methodology used"
    )

    # Audit and compliance
    regulatory_requirements = models.JSONField(
        default=list,
        blank=True,
        help_text="Regulatory requirements this register addresses"
    )

    compliance_frameworks = models.JSONField(
        default=list,
        blank=True,
        help_text="Compliance frameworks this register supports"
    )

    # Metadata and tags
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Register tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional register properties"
    )

    class Meta:
        db_table = "risk_registers"
        indexes = [
            models.Index(fields=['status'], name='risk_register_status_idx'),
            models.Index(fields=['scope'], name='risk_register_scope_idx'),
            models.Index(fields=['owner_user_id'], name='risk_register_owner_idx'),
            models.Index(fields=['next_report_date'], name='risk_register_report_idx'),
            models.Index(fields=['next_review_date'], name='risk_register_review_idx'),
            models.Index(fields=['total_risks'], name='risk_register_total_risks_idx'),
            models.Index(fields=['critical_risks'], name='risk_register_critical_idx'),
            models.Index(fields=['created_at'], name='risk_register_created_idx'),
        ]
        ordering = ['-created_at']

    def create_risk_register(
        self,
        register_id: str,
        name: str,
        scope: str,
        owner_user_id: Optional[uuid.UUID] = None,
        owner_username: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new risk register"""
        self.register_id = register_id
        self.name = name
        self.scope = scope
        self.owner_user_id = owner_user_id
        self.owner_username = owner_username
        self.description = description
        self.tags = tags if tags is not None else []
        self.status = 'draft'

        from .domain_events import RiskRegisterCreated
        self._raise_event(RiskRegisterCreated(
            aggregate_id=self.id,
            register_id=register_id,
            name=name,
            scope=scope
        ))

    def activate_register(self):
        """Activate the risk register"""
        if self.status == 'draft':
            self.status = 'active'

            from .domain_events import RiskRegisterUpdated
            self._raise_event(RiskRegisterUpdated(
                aggregate_id=self.id,
                register_id=self.register_id,
                status_change='draft → active'
            ))

    def add_asset_risk(self, asset_risk_id: str):
        """Add an asset risk to the register"""
        if asset_risk_id not in self.asset_risk_ids:
            self.asset_risk_ids.append(asset_risk_id)
            self._update_statistics()

            from .domain_events import RiskRegisterUpdated
            self._raise_event(RiskRegisterUpdated(
                aggregate_id=self.id,
                register_id=self.register_id,
                risk_added=f"asset_risk:{asset_risk_id}"
            ))

    def add_third_party_risk(self, third_party_risk_id: str):
        """Add a third party risk to the register"""
        if third_party_risk_id not in self.third_party_risk_ids:
            self.third_party_risk_ids.append(third_party_risk_id)
            self._update_statistics()

            from .domain_events import RiskRegisterUpdated
            self._raise_event(RiskRegisterUpdated(
                aggregate_id=self.id,
                register_id=self.register_id,
                risk_added=f"third_party_risk:{third_party_risk_id}"
            ))

    def add_business_risk(self, business_risk_id: str):
        """Add a business risk to the register"""
        if business_risk_id not in self.business_risk_ids:
            self.business_risk_ids.append(business_risk_id)
            self._update_statistics()

            from .domain_events import RiskRegisterUpdated
            self._raise_event(RiskRegisterUpdated(
                aggregate_id=self.id,
                register_id=self.register_id,
                risk_added=f"business_risk:{business_risk_id}"
            ))

    def add_risk_scenario(self, risk_scenario_id: str):
        """Add a risk scenario to the register"""
        if risk_scenario_id not in self.risk_scenario_ids:
            self.risk_scenario_ids.append(risk_scenario_id)
            self._update_statistics()

            from .domain_events import RiskRegisterUpdated
            self._raise_event(RiskRegisterUpdated(
                aggregate_id=self.id,
                register_id=self.register_id,
                risk_added=f"risk_scenario:{risk_scenario_id}"
            ))

    def remove_risk(self, risk_id: str, risk_type: str):
        """Remove a risk from the register"""
        if risk_type == 'asset_risk' and risk_id in self.asset_risk_ids:
            self.asset_risk_ids.remove(risk_id)
        elif risk_type == 'third_party_risk' and risk_id in self.third_party_risk_ids:
            self.third_party_risk_ids.remove(risk_id)
        elif risk_type == 'business_risk' and risk_id in self.business_risk_ids:
            self.business_risk_ids.remove(risk_id)
        elif risk_type == 'risk_scenario' and risk_id in self.risk_scenario_ids:
            self.risk_scenario_ids.remove(risk_id)

        self._update_statistics()

        from .domain_events import RiskRegisterUpdated
        self._raise_event(RiskRegisterUpdated(
            aggregate_id=self.id,
            register_id=self.register_id,
            risk_removed=f"{risk_type}:{risk_id}"
        ))

    def consolidate_statistics(self):
        """Manually trigger statistics consolidation"""
        self._update_statistics()
        self._generate_heat_map()

        from .domain_events import RiskRegisterConsolidated
        self._raise_event(RiskRegisterConsolidated(
            aggregate_id=self.id,
            register_id=self.register_id,
            total_risks=self.total_risks,
            critical_risks=self.critical_risks
        ))

    def generate_report(self, report_date: Optional[timezone.date] = None):
        """Generate a risk register report"""
        self.last_report_date = report_date or timezone.now().date()
        self._calculate_next_report_date()

        from .domain_events import RiskRegisterReported
        self._raise_event(RiskRegisterReported(
            aggregate_id=self.id,
            register_id=self.register_id,
            report_date=str(self.last_report_date)
        ))

    def conduct_review(self, review_date: Optional[timezone.date] = None, notes: Optional[str] = None):
        """Conduct a register review"""
        self.last_review_date = review_date or timezone.now().date()
        self._calculate_next_review_date()

        from .domain_events import RiskRegisterUpdated
        self._raise_event(RiskRegisterUpdated(
            aggregate_id=self.id,
            register_id=self.register_id,
            review_conducted=str(self.last_review_date)
        ))

    def update_risk_appetite(self, appetite_statement: str, critical_threshold: int, high_threshold: int, moderate_threshold: int):
        """Update risk appetite settings"""
        self.risk_appetite_statement = appetite_statement
        self.risk_appetite_critical_threshold = critical_threshold
        self.risk_appetite_high_threshold = high_threshold
        self.risk_appetite_moderate_threshold = moderate_threshold

        # Re-classify risks based on new appetite
        self._update_statistics()

        from .domain_events import RiskRegisterUpdated
        self._raise_event(RiskRegisterUpdated(
            aggregate_id=self.id,
            register_id=self.register_id,
            appetite_updated=True
        ))

    def archive_register(self, reason: str):
        """Archive the risk register"""
        if self.status == 'active':
            self.status = 'archived'

            from .domain_events import RiskRegisterUpdated
            self._raise_event(RiskRegisterUpdated(
                aggregate_id=self.id,
                register_id=self.register_id,
                status_change='active → archived',
                reason=reason
            ))

    def _update_statistics(self):
        """Update consolidated statistics from all risks"""
        # This would typically be done by querying the actual risk aggregates
        # For now, we'll use placeholder logic
        self.total_risks = (
            len(self.asset_risk_ids) +
            len(self.third_party_risk_ids) +
            len(self.business_risk_ids) +
            len(self.risk_scenario_ids)
        )

        # Placeholder risk level distribution (would be calculated from actual risks)
        self.critical_risks = int(self.total_risks * 0.1)  # 10% critical
        self.high_risks = int(self.total_risks * 0.2)      # 20% high
        self.moderate_risks = int(self.total_risks * 0.4)  # 40% moderate
        self.low_risks = self.total_risks - self.critical_risks - self.high_risks - self.moderate_risks

        # Treatment statistics (placeholders)
        self.risks_requiring_treatment = int(self.total_risks * 0.6)  # 60% need treatment
        self.risks_under_treatment = int(self.risks_requiring_treatment * 0.7)  # 70% under treatment
        self.risks_effectively_treated = int(self.risks_under_treatment * 0.8)  # 80% effective

    def _generate_heat_map(self):
        """Generate risk heat map data"""
        # This would create a 5x5 matrix of likelihood vs impact
        # with risk counts in each cell
        self.risk_heat_map = {
            'matrix': [
                [0, 0, 0, 0, 0],  # Very Low likelihood
                [0, 0, 0, 0, 0],  # Low likelihood
                [0, 0, 0, 0, 0],  # Moderate likelihood
                [0, 0, 0, 0, 0],  # High likelihood
                [0, 0, 0, 0, 0],  # Very High likelihood
            ],
            'labels': {
                'likelihood': ['Very Low', 'Low', 'Moderate', 'High', 'Very High'],
                'impact': ['Very Low', 'Low', 'Moderate', 'High', 'Very High']
            },
            'generated_at': str(timezone.now())
        }

    def _calculate_next_report_date(self):
        """Calculate next report date based on frequency"""
        if not self.last_report_date:
            return

        if self.reporting_frequency == 'weekly':
            days = 7
        elif self.reporting_frequency == 'monthly':
            days = 30
        elif self.reporting_frequency == 'quarterly':
            days = 90
        elif self.reporting_frequency == 'annually':
            days = 365
        else:
            days = 30  # default monthly

        from datetime import timedelta
        self.next_report_date = self.last_report_date + timedelta(days=days)

    def _calculate_next_review_date(self):
        """Calculate next review date (typically annual)"""
        if not self.last_review_date:
            return

        from datetime import timedelta
        self.next_review_date = self.last_review_date + timedelta(days=365)

    @property
    def risk_distribution(self) -> Dict[str, int]:
        """Get risk distribution summary"""
        return {
            'critical': self.critical_risks,
            'high': self.high_risks,
            'moderate': self.moderate_risks,
            'low': self.low_risks,
            'total': self.total_risks
        }

    @property
    def treatment_effectiveness(self) -> float:
        """Calculate treatment effectiveness percentage"""
        if self.risks_requiring_treatment == 0:
            return 100.0
        return round((self.risks_effectively_treated / self.risks_requiring_treatment) * 100, 2)

    @property
    def risks_within_appetite(self) -> int:
        """Count risks within organizational appetite"""
        return self.low_risks + self.moderate_risks

    @property
    def risks_exceeding_appetite(self) -> int:
        """Count risks exceeding organizational appetite"""
        return self.high_risks + self.critical_risks

    @property
    def is_overdue_for_report(self) -> bool:
        """Check if register is overdue for reporting"""
        if not self.next_report_date:
            return False
        return timezone.now().date() > self.next_report_date

    @property
    def is_overdue_for_review(self) -> bool:
        """Check if register is overdue for review"""
        if not self.next_review_date:
            return False
        return timezone.now().date() > self.next_review_date

    def get_top_risks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top risks by severity (placeholder - would query actual risks)"""
        # This would return the highest severity risks
        return [{
            'id': f'placeholder-{i}',
            'title': f'Top Risk {i}',
            'severity': 'high',
            'score': 20 - i
        } for i in range(min(limit, 10))]

    def __str__(self):
        return f"RiskRegister({self.register_id}: {self.name} - {self.total_risks} risks)"
