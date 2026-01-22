"""
Third Party Entity Aggregate

Aggregate for managing third party vendors, suppliers, and partners
including risk assessments, contracts, and compliance monitoring.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class ThirdPartyEntity(AggregateRoot):
    """
    Third Party Entity aggregate for comprehensive vendor and supplier management.

    Manages third party relationships including vendor assessments, contract management,
    risk monitoring, compliance tracking, and performance evaluation.
    """

    # Entity identification
    entity_name = models.CharField(
        max_length=255,
        help_text="Name of the third party entity"
    )

    entity_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the third party entity"
    )

    entity_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique entity identifier (e.g., TP-2024-001)"
    )

    # Entity classification
    ENTITY_TYPES = [
        ('vendor', 'Vendor'),
        ('supplier', 'Supplier'),
        ('partner', 'Partner'),
        ('contractor', 'Contractor'),
        ('consultant', 'Consultant'),
        ('cloud_provider', 'Cloud Provider'),
        ('other', 'Other'),
    ]

    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPES,
        default='vendor',
        help_text="Type of third party entity"
    )

    # Entity details
    industry = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Industry sector"
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Country of operation"
    )

    headquarters_location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Headquarters location"
    )

    website = models.URLField(
        blank=True,
        null=True,
        help_text="Entity website"
    )

    contact_information = models.JSONField(
        default=dict,
        blank=True,
        help_text="Primary contact information"
    )

    # Entity status
    STATUS_CHOICES = [
        ('prospective', 'Prospective'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('blacklisted', 'Blacklisted'),
    ]

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='prospective',
        help_text="Current relationship status"
    )

    # Risk assessment
    inherent_risk_level = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium',
        help_text="Inherent risk level"
    )

    residual_risk_level = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium',
        help_text="Residual risk level after controls"
    )

    risk_assessment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last risk assessment"
    )

    risk_score = models.FloatField(
        default=0.0,
        help_text="Quantitative risk score (0.0-100.0)"
    )

    # Contract management
    contracts = models.JSONField(
        default=list,
        blank=True,
        help_text="Associated contracts"
    )

    active_contracts_count = models.IntegerField(
        default=0,
        help_text="Number of active contracts"
    )

    # Assessment and compliance
    assessments = models.JSONField(
        default=list,
        blank=True,
        help_text="Completed assessments"
    )

    compliance_status = models.CharField(
        max_length=20,
        choices=[
            ('compliant', 'Compliant'),
            ('non_compliant', 'Non-Compliant'),
            ('under_review', 'Under Review'),
            ('not_assessed', 'Not Assessed'),
        ],
        default='not_assessed',
        help_text="Overall compliance status"
    )

    last_assessment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last compliance assessment"
    )

    next_assessment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled assessment"
    )

    # Criticality and business impact
    criticality_level = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium',
        help_text="Business criticality level"
    )

    business_impact = models.TextField(
        blank=True,
        null=True,
        help_text="Description of business impact if disrupted"
    )

    # Performance and quality metrics
    performance_rating = models.CharField(
        max_length=10,
        choices=[
            ('poor', 'Poor'),
            ('fair', 'Fair'),
            ('good', 'Good'),
            ('excellent', 'Excellent'),
        ],
        blank=True,
        null=True,
        help_text="Overall performance rating"
    )

    quality_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Quality and performance metrics"
    )

    # Security and privacy
    security_rating = models.CharField(
        max_length=10,
        choices=[
            ('poor', 'Poor'),
            ('fair', 'Fair'),
            ('good', 'Good'),
            ('excellent', 'Excellent'),
        ],
        blank=True,
        null=True,
        help_text="Security posture rating"
    )

    data_processing = models.JSONField(
        default=dict,
        blank=True,
        help_text="Data processing activities and safeguards"
    )

    # Financial information
    annual_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual revenue (if public)"
    )

    employee_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of employees"
    )

    # Relationship management
    relationship_owner_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of relationship owner"
    )

    relationship_owner_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of relationship owner"
    )

    relationship_manager_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of relationship manager"
    )

    relationship_manager_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of relationship manager"
    )

    # Audit and review
    last_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last relationship review"
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled review"
    )

    review_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes from relationship reviews"
    )

    # Integration fields
    related_assets = models.JSONField(
        default=list,
        blank=True,
        help_text="Related assets from Asset context"
    )

    related_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="Related risks from Risk Registers"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Entity tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    class Meta:
        db_table = "third_party_entities"
        indexes = [
            models.Index(fields=['entity_type'], name='tp_entity_type_idx'),
            models.Index(fields=['status'], name='tp_entity_status_idx'),
            models.Index(fields=['inherent_risk_level'], name='tp_entity_risk_idx'),
            models.Index(fields=['compliance_status'], name='tp_entity_compliance_idx'),
            models.Index(fields=['criticality_level'], name='tp_entity_criticality_idx'),
            models.Index(fields=['relationship_owner_user_id'], name='tp_entity_owner_idx'),
            models.Index(fields=['next_assessment_date'], name='tp_entity_assessment_idx'),
            models.Index(fields=['created_at'], name='tp_entity_created_idx'),
        ]
        ordering = ['-created_at']

    def create_entity(
        self,
        entity_id: str,
        entity_name: str,
        entity_type: str,
        entity_description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new third party entity"""
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.entity_type = entity_type
        self.entity_description = entity_description
        self.tags = tags if tags is not None else []
        self.status = 'prospective'

        from .domain_events import ThirdPartyEntityCreated
        self._raise_event(ThirdPartyEntityCreated(
            aggregate_id=self.id,
            entity_id=entity_id,
            entity_name=entity_name,
            entity_type=entity_type
        ))

    def activate_entity(self):
        """Activate the third party entity"""
        if self.status == 'prospective':
            self.status = 'active'

            from .domain_events import ThirdPartyEntityActivated
            self._raise_event(ThirdPartyEntityActivated(
                aggregate_id=self.id,
                entity_id=self.entity_id
            ))

    def perform_risk_assessment(self, risk_level: str, risk_score: float):
        """Perform risk assessment"""
        self.inherent_risk_level = risk_level
        self.risk_score = risk_score
        self.risk_assessment_date = timezone.now().date()

        # Initially, residual = inherent
        self.residual_risk_level = risk_level

        from .domain_events import ThirdPartyEntityRiskAssessed
        self._raise_event(ThirdPartyEntityRiskAssessed(
            aggregate_id=self.id,
            entity_id=self.entity_id,
            risk_level=risk_level,
            risk_score=risk_score
        ))

    def update_compliance_status(self, status: str, assessment_date: Optional[timezone.date] = None):
        """Update compliance status"""
        old_status = self.compliance_status
        self.compliance_status = status
        self.last_assessment_date = assessment_date or timezone.now().date()

        from .domain_events import ThirdPartyEntityComplianceUpdated
        self._raise_event(ThirdPartyEntityComplianceUpdated(
            aggregate_id=self.id,
            entity_id=self.entity_id,
            old_status=old_status,
            new_status=status
        ))

    def assign_relationship_owner(self, owner_user_id: uuid.UUID, owner_username: str):
        """Assign relationship owner"""
        self.relationship_owner_user_id = owner_user_id
        self.relationship_owner_username = owner_username

        from .domain_events import ThirdPartyEntityOwnerAssigned
        self._raise_event(ThirdPartyEntityOwnerAssigned(
            aggregate_id=self.id,
            entity_id=self.entity_id,
            owner_user_id=str(owner_user_id)
        ))

    def conduct_review(self, review_notes: Optional[str] = None):
        """Conduct relationship review"""
        self.last_review_date = timezone.now().date()
        if review_notes:
            existing_notes = self.review_notes or ""
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            self.review_notes = f"{existing_notes}\n\n[{timestamp}] {review_notes}".strip()

        from .domain_events import ThirdPartyEntityReviewed
        self._raise_event(ThirdPartyEntityReviewed(
            aggregate_id=self.id,
            entity_id=self.entity_id,
            review_date=str(self.last_review_date)
        ))

    def terminate_relationship(self, reason: str):
        """Terminate relationship with entity"""
        if self.status == 'active':
            self.status = 'terminated'

            from .domain_events import ThirdPartyEntityTerminated
            self._raise_event(ThirdPartyEntityTerminated(
                aggregate_id=self.id,
                entity_id=self.entity_id,
                reason=reason
            ))

    @property
    def is_active(self) -> bool:
        """Check if entity relationship is active"""
        return self.status == 'active'

    @property
    def requires_attention(self) -> bool:
        """Check if entity requires attention"""
        return (
            self.status == 'active' and (
                self.residual_risk_level in ['high', 'critical'] or
                self.compliance_status == 'non_compliant' or
                self.is_overdue_for_assessment or
                self.is_overdue_for_review
            )
        )

    @property
    def is_overdue_for_assessment(self) -> bool:
        """Check if assessment is overdue"""
        if not self.next_assessment_date:
            return False
        return timezone.now().date() > self.next_assessment_date

    @property
    def is_overdue_for_review(self) -> bool:
        """Check if review is overdue"""
        if not self.next_review_date:
            return False
        return timezone.now().date() > self.next_review_date

    @property
    def risk_reduction_achieved(self) -> bool:
        """Check if risk reduction has been achieved"""
        risk_levels = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        inherent = risk_levels.get(self.inherent_risk_level, 2)
        residual = risk_levels.get(self.residual_risk_level, 2)
        return residual < inherent

    def __str__(self):
        return f"ThirdPartyEntity({self.entity_id}: {self.entity_name} - {self.entity_type} - {self.status})"
