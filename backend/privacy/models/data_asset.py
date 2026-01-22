"""
Data Asset Aggregate

Aggregate for managing privacy data assets, including classification,
processing purposes, data subject rights, and privacy impact assessments.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class DataAsset(AggregateRoot):
    """
    Data Asset aggregate for comprehensive privacy data asset management.

    Manages data assets subject to privacy regulations, including classification,
    processing purposes, data subject rights, retention schedules, and privacy
    impact assessments.
    """

    # Asset identification
    asset_name = models.CharField(
        max_length=255,
        help_text="Name/identifier of the data asset"
    )

    asset_description = models.TextField(
        help_text="Description of the data asset and its contents"
    )

    asset_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique asset identifier (e.g., DATA-PII-001)"
    )

    # Data classification
    DATA_CATEGORIES = [
        ('personal_data', 'Personal Data'),
        ('sensitive_personal_data', 'Sensitive Personal Data'),
        ('special_category_data', 'Special Category Data'),
        ('criminal_conviction_data', 'Criminal Conviction Data'),
        ('genetic_data', 'Genetic Data'),
        ('biometric_data', 'Biometric Data'),
        ('health_data', 'Health Data'),
        ('financial_data', 'Financial Data'),
        ('communication_data', 'Communication Data'),
        ('location_data', 'Location Data'),
        ('online_identifier_data', 'Online Identifier Data'),
        ('racial_ethnic_data', 'Racial/Ethnic Origin Data'),
        ('political_opinion_data', 'Political Opinion Data'),
        ('religious_belief_data', 'Religious Belief Data'),
        ('trade_union_data', 'Trade Union Membership Data'),
        ('sexual_orientation_data', 'Sexual Orientation Data'),
    ]

    primary_data_category = models.CharField(
        max_length=30,
        choices=DATA_CATEGORIES,
        default='personal_data',
        help_text="Primary category of personal data"
    )

    data_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="All applicable data categories for this asset"
    )

    # Privacy classification
    SENSITIVITY_LEVELS = [
        ('public', 'Public'),
        ('internal', 'Internal'),
        ('confidential', 'Confidential'),
        ('restricted', 'Restricted'),
        ('highly_restricted', 'Highly Restricted'),
    ]

    sensitivity_level = models.CharField(
        max_length=20,
        choices=SENSITIVITY_LEVELS,
        default='confidential',
        help_text="Privacy sensitivity level"
    )

    # Data subject information
    data_subject_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Types of data subjects (e.g., customers, employees, website visitors)"
    )

    estimated_data_subjects = models.IntegerField(
        null=True,
        blank=True,
        help_text="Estimated number of data subjects"
    )

    # Processing information
    processing_purposes = models.JSONField(
        default=list,
        blank=True,
        help_text="Purposes for which the data is processed"
    )

    legal_bases = models.JSONField(
        default=list,
        blank=True,
        help_text="Legal bases for processing (GDPR Article 6/9)"
    )

    legitimate_interests = models.TextField(
        blank=True,
        null=True,
        help_text="Description of legitimate interests for processing"
    )

    # Data sources and collection
    data_sources = models.JSONField(
        default=list,
        blank=True,
        help_text="Sources from which data is collected"
    )

    collection_methods = models.JSONField(
        default=list,
        blank=True,
        help_text="Methods used to collect the data"
    )

    consent_required = models.BooleanField(
        default=False,
        help_text="Whether consent is required for collection"
    )

    consent_mechanisms = models.JSONField(
        default=list,
        blank=True,
        help_text="Mechanisms used to obtain consent"
    )

    # Data storage and retention
    storage_locations = models.JSONField(
        default=list,
        blank=True,
        help_text="Locations where data is stored"
    )

    retention_schedule = models.TextField(
        blank=True,
        null=True,
        help_text="Data retention schedule and justification"
    )

    retention_period_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Retention period in days"
    )

    disposal_methods = models.JSONField(
        default=list,
        blank=True,
        help_text="Methods for data disposal"
    )

    # Data sharing and transfers
    recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="Recipients or categories of recipients"
    )

    third_party_processors = models.JSONField(
        default=list,
        blank=True,
        help_text="Third party processors involved"
    )

    international_transfers = models.JSONField(
        default=list,
        blank=True,
        help_text="International data transfers and safeguards"
    )

    # Security measures
    security_measures = models.JSONField(
        default=list,
        blank=True,
        help_text="Security measures applied to protect the data"
    )

    encryption_methods = models.JSONField(
        default=list,
        blank=True,
        help_text="Encryption methods used"
    )

    access_controls = models.JSONField(
        default=list,
        blank=True,
        help_text="Access control measures"
    )

    # Privacy impact assessment
    pia_required = models.BooleanField(
        default=False,
        help_text="Whether Privacy Impact Assessment is required"
    )

    pia_completed = models.BooleanField(
        default=False,
        help_text="Whether PIA has been completed"
    )

    pia_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date PIA was completed"
    )

    pia_findings = models.TextField(
        blank=True,
        null=True,
        help_text="Key findings from Privacy Impact Assessment"
    )

    # Data Protection Officer
    dpo_review_required = models.BooleanField(
        default=False,
        help_text="Whether DPO review is required"
    )

    dpo_reviewed = models.BooleanField(
        default=False,
        help_text="Whether DPO has reviewed"
    )

    dpo_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of DPO review"
    )

    dpo_comments = models.TextField(
        blank=True,
        null=True,
        help_text="Comments from Data Protection Officer"
    )

    # Data subject rights
    subject_rights_supported = models.JSONField(
        default=list,
        blank=True,
        help_text="Data subject rights supported for this asset"
    )

    right_of_access_mechanism = models.TextField(
        blank=True,
        null=True,
        help_text="Mechanism for handling right of access requests"
    )

    right_of_rectification_mechanism = models.TextField(
        blank=True,
        null=True,
        help_text="Mechanism for handling right of rectification requests"
    )

    right_of_erasure_mechanism = models.TextField(
        blank=True,
        null=True,
        help_text="Mechanism for handling right of erasure requests"
    )

    # Risk assessment
    privacy_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="Privacy risks associated with this data asset"
    )

    risk_mitigation_measures = models.JSONField(
        default=list,
        blank=True,
        help_text="Risk mitigation measures implemented"
    )

    residual_privacy_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="Residual privacy risks after mitigation"
    )

    # Compliance status
    COMPLIANCE_STATUSES = [
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('under_review', 'Under Review'),
        ('remediation_required', 'Remediation Required'),
        ('exempt', 'Exempt'),
    ]

    compliance_status = models.CharField(
        max_length=20,
        choices=COMPLIANCE_STATUSES,
        default='under_review',
        help_text="Current compliance status"
    )

    compliance_issues = models.JSONField(
        default=list,
        blank=True,
        help_text="Outstanding compliance issues"
    )

    # Audit and review
    last_audit_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last privacy audit"
    )

    next_audit_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled audit"
    )

    audit_findings = models.TextField(
        blank=True,
        null=True,
        help_text="Findings from privacy audits"
    )

    # Ownership and responsibility
    data_owner_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the data owner"
    )

    data_owner_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the data owner"
    )

    data_steward_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the data steward"
    )

    data_steward_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the data steward"
    )

    dpo_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the Data Protection Officer"
    )

    dpo_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the Data Protection Officer"
    )

    # System integration
    system_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name of the system where data resides"
    )

    database_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Database where data is stored"
    )

    table_names = models.JSONField(
        default=list,
        blank=True,
        help_text="Database table names containing this data"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Asset tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    # Integration fields
    related_asset_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Related asset IDs from Asset context"
    )

    related_control_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Related control IDs from Control Library"
    )

    related_risk_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Related risk IDs from Risk Registers"
    )

    class Meta:
        db_table = "privacy_data_assets"
        indexes = [
            models.Index(fields=['primary_data_category'], name='data_asset_category_idx'),
            models.Index(fields=['sensitivity_level'], name='data_asset_sensitivity_idx'),
            models.Index(fields=['compliance_status'], name='data_asset_compliance_idx'),
            models.Index(fields=['pia_required'], name='data_asset_pia_idx'),
            models.Index(fields=['data_owner_user_id'], name='data_asset_owner_idx'),
            models.Index(fields=['next_audit_date'], name='data_asset_audit_idx'),
            models.Index(fields=['created_at'], name='data_asset_created_idx'),
        ]
        ordering = ['-created_at']

    def create_data_asset(
        self,
        asset_id: str,
        asset_name: str,
        asset_description: str,
        primary_data_category: str,
        data_subject_types: List[str],
        processing_purposes: List[str],
        data_owner_user_id: Optional[uuid.UUID] = None,
        data_owner_username: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new privacy data asset"""
        self.asset_id = asset_id
        self.asset_name = asset_name
        self.asset_description = asset_description
        self.primary_data_category = primary_data_category
        self.data_subject_types = data_subject_types
        self.processing_purposes = processing_purposes
        self.data_owner_user_id = data_owner_user_id
        self.data_owner_username = data_owner_username
        self.tags = tags if tags is not None else []

        # Set default sensitivity level based on data category
        self._set_default_sensitivity_level()

        # Determine if PIA is required
        self.pia_required = self._assess_pia_requirement()

        # Determine if DPO review is required
        self.dpo_review_required = self._assess_dpo_review_requirement()

        # Set default compliance status
        self.compliance_status = 'under_review'

        from .domain_events import DataAssetCreated
        self._raise_event(DataAssetCreated(
            aggregate_id=self.id,
            asset_id=asset_id,
            asset_name=asset_name,
            primary_data_category=primary_data_category,
            sensitivity_level=self.sensitivity_level
        ))

    def update_data_classification(
        self,
        data_categories: List[str],
        sensitivity_level: Optional[str] = None
    ):
        """Update data classification and sensitivity"""
        old_category = self.primary_data_category
        old_sensitivity = self.sensitivity_level

        self.data_categories = data_categories
        if sensitivity_level:
            self.sensitivity_level = sensitivity_level
        else:
            self._set_default_sensitivity_level()

        # Re-assess PIA and DPO requirements
        self.pia_required = self._assess_pia_requirement()
        self.dpo_review_required = self._assess_dpo_review_requirement()

        from .domain_events import DataAssetClassificationUpdated
        self._raise_event(DataAssetClassificationUpdated(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            old_category=old_category,
            new_category=self.primary_data_category,
            old_sensitivity=old_sensitivity,
            new_sensitivity=self.sensitivity_level
        ))

    def update_processing_information(
        self,
        legal_bases: List[str],
        legitimate_interests: Optional[str] = None,
        processing_purposes: Optional[List[str]] = None
    ):
        """Update processing information"""
        self.legal_bases = legal_bases
        if legitimate_interests:
            self.legitimate_interests = legitimate_interests
        if processing_purposes:
            self.processing_purposes = processing_purposes

        from .domain_events import DataAssetProcessingUpdated
        self._raise_event(DataAssetProcessingUpdated(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            legal_bases=legal_bases,
            processing_purposes=self.processing_purposes
        ))

    def update_retention_schedule(
        self,
        retention_schedule: str,
        retention_period_days: Optional[int] = None,
        disposal_methods: Optional[List[str]] = None
    ):
        """Update data retention and disposal information"""
        self.retention_schedule = retention_schedule
        if retention_period_days:
            self.retention_period_days = retention_period_days
        if disposal_methods:
            self.disposal_methods = disposal_methods

        from .domain_events import DataAssetRetentionUpdated
        self._raise_event(DataAssetRetentionUpdated(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            retention_period_days=self.retention_period_days
        ))

    def update_security_measures(
        self,
        security_measures: List[str],
        encryption_methods: Optional[List[str]] = None,
        access_controls: Optional[List[str]] = None
    ):
        """Update security measures"""
        self.security_measures = security_measures
        if encryption_methods:
            self.encryption_methods = encryption_methods
        if access_controls:
            self.access_controls = access_controls

        from .domain_events import DataAssetSecurityUpdated
        self._raise_event(DataAssetSecurityUpdated(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            security_measures=security_measures
        ))

    def conduct_privacy_impact_assessment(
        self,
        findings: str,
        assessor_user_id: uuid.UUID,
        assessor_username: str
    ):
        """Conduct Privacy Impact Assessment"""
        self.pia_completed = True
        self.pia_date = timezone.now().date()
        self.pia_findings = findings

        # Update compliance status based on findings
        if 'high risk' in findings.lower() or 'significant impact' in findings.lower():
            self.compliance_status = 'remediation_required'
        else:
            self.compliance_status = 'compliant'

        from .domain_events import DataAssetPIACompleted
        self._raise_event(DataAssetPIACompleted(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            pia_date=str(self.pia_date),
            findings=findings
        ))

    def conduct_dpo_review(
        self,
        comments: str,
        dpo_user_id: uuid.UUID,
        dpo_username: str
    ):
        """Conduct Data Protection Officer review"""
        self.dpo_reviewed = True
        self.dpo_review_date = timezone.now().date()
        self.dpo_comments = comments
        self.dpo_user_id = dpo_user_id
        self.dpo_username = dpo_username

        from .domain_events import DataAssetDPOReviewed
        self._raise_event(DataAssetDPOReviewed(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            dpo_user_id=str(dpo_user_id),
            review_date=str(self.dpo_review_date)
        ))

    def conduct_privacy_audit(
        self,
        findings: str,
        next_audit_date: Optional[timezone.date] = None
    ):
        """Conduct privacy audit"""
        self.last_audit_date = timezone.now().date()
        self.audit_findings = findings
        self.next_audit_date = next_audit_date

        # Update compliance status based on audit findings
        if 'non-compliant' in findings.lower() or 'violation' in findings.lower():
            self.compliance_status = 'non_compliant'
            self.compliance_issues = self._extract_compliance_issues(findings)
        else:
            self.compliance_status = 'compliant'

        from .domain_events import DataAssetAudited
        self._raise_event(DataAssetAudited(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            audit_date=str(self.last_audit_date),
            findings=findings
        ))

    def update_compliance_status(
        self,
        status: str,
        issues: Optional[List[str]] = None
    ):
        """Update compliance status"""
        old_status = self.compliance_status
        self.compliance_status = status
        if issues:
            self.compliance_issues = issues

        from .domain_events import DataAssetComplianceUpdated
        self._raise_event(DataAssetComplianceUpdated(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            old_status=old_status,
            new_status=status,
            issues=self.compliance_issues
        ))

    def assign_ownership(
        self,
        data_owner_user_id: Optional[uuid.UUID] = None,
        data_owner_username: Optional[str] = None,
        data_steward_user_id: Optional[uuid.UUID] = None,
        data_steward_username: Optional[str] = None
    ):
        """Assign data ownership and stewardship"""
        if data_owner_user_id:
            self.data_owner_user_id = data_owner_user_id
            self.data_owner_username = data_owner_username
        if data_steward_user_id:
            self.data_steward_user_id = data_steward_user_id
            self.data_steward_username = data_steward_username

        from .domain_events import DataAssetOwnershipAssigned
        self._raise_event(DataAssetOwnershipAssigned(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            data_owner_user_id=str(data_owner_user_id) if data_owner_user_id else None,
            data_steward_user_id=str(data_steward_user_id) if data_steward_user_id else None
        ))

    def _set_default_sensitivity_level(self):
        """Set default sensitivity level based on data category"""
        high_sensitivity_categories = [
            'special_category_data', 'genetic_data', 'biometric_data',
            'health_data', 'criminal_conviction_data'
        ]

        if self.primary_data_category in high_sensitivity_categories:
            self.sensitivity_level = 'highly_restricted'
        elif self.primary_data_category in ['sensitive_personal_data', 'financial_data']:
            self.sensitivity_level = 'restricted'
        else:
            self.sensitivity_level = 'confidential'

    def _assess_pia_requirement(self) -> bool:
        """Assess whether Privacy Impact Assessment is required"""
        # PIA required for high-risk processing
        high_risk_indicators = [
            self.sensitivity_level in ['restricted', 'highly_restricted'],
            'special_category_data' in self.data_categories,
            len(self.international_transfers) > 0,
            self.primary_data_category in ['genetic_data', 'biometric_data', 'health_data'],
            len(self.data_subject_types) > 10000  # Large scale processing
        ]

        return any(high_risk_indicators)

    def _assess_dpo_review_requirement(self) -> bool:
        """Assess whether DPO review is required"""
        # DPO review required for sensitive data or high-risk processing
        return (
            self.sensitivity_level in ['restricted', 'highly_restricted'] or
            self.pia_required or
            'special_category_data' in self.data_categories
        )

    def _extract_compliance_issues(self, audit_findings: str) -> List[str]:
        """Extract compliance issues from audit findings"""
        # Simple extraction - could be enhanced with NLP
        issues = []
        findings_lower = audit_findings.lower()

        if 'consent' in findings_lower and 'missing' in findings_lower:
            issues.append("Consent mechanism missing or inadequate")
        if 'retention' in findings_lower and ('excessive' in findings_lower or 'violation' in findings_lower):
            issues.append("Data retention policy violation")
        if 'security' in findings_lower and ('breach' in findings_lower or 'inadequate' in findings_lower):
            issues.append("Inadequate security measures")
        if 'transfer' in findings_lower and ('unauthorized' in findings_lower or 'violation' in findings_lower):
            issues.append("International transfer compliance issue")

        return issues

    @property
    def is_high_risk(self) -> bool:
        """Check if this data asset is considered high risk"""
        return (
            self.sensitivity_level == 'highly_restricted' or
            self.pia_required or
            self.primary_data_category in ['special_category_data', 'genetic_data', 'biometric_data', 'health_data']
        )

    @property
    def requires_audit_attention(self) -> bool:
        """Check if asset requires audit attention"""
        return (
            self.compliance_status in ['non_compliant', 'remediation_required'] or
            self.is_overdue_for_audit or
            self.pia_required and not self.pia_completed
        )

    @property
    def is_overdue_for_audit(self) -> bool:
        """Check if asset is overdue for audit"""
        if not self.next_audit_date:
            return False
        return timezone.now().date() > self.next_audit_date

    @property
    def data_subject_rights_compliance_score(self) -> float:
        """Calculate compliance score for data subject rights"""
        rights_supported = len(self.subject_rights_supported)
        total_rights = 8  # GDPR has 8 data subject rights

        if total_rights == 0:
            return 0.0

        return round((rights_supported / total_rights) * 100, 2)

    @property
    def retention_compliance_status(self) -> str:
        """Check retention compliance status"""
        if not self.retention_period_days:
            return "not_defined"

        # Simplified check - could be enhanced with actual data analysis
        if self.retention_period_days > 2555:  # 7 years
            return "potentially_excessive"
        elif self.retention_period_days < 30:
            return "potentially_insufficient"
        else:
            return "compliant"

    def __str__(self):
        return f"DataAsset({self.asset_id}: {self.asset_name} - {self.primary_data_category} - {self.sensitivity_level})"
