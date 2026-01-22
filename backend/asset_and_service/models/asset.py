"""
Asset Aggregate

Aggregate for managing organizational assets including hardware, software,
data, and other resources with comprehensive lifecycle management.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class Asset(AggregateRoot):
    """
    Asset aggregate for comprehensive asset management.

    Manages hardware, software, data assets, and other organizational
    resources with lifecycle tracking, classification, and relationships.
    """

    # Basic identification
    name = models.CharField(
        max_length=255,
        help_text="Asset name or identifier"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the asset"
    )

    asset_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique asset identifier (e.g., AST-001, HW-001)"
    )

    # Asset type and classification
    ASSET_TYPES = [
        ('hardware', 'Hardware'),
        ('software', 'Software'),
        ('data', 'Data'),
        ('network', 'Network Infrastructure'),
        ('cloud_service', 'Cloud Service'),
        ('physical', 'Physical Asset'),
        ('intangible', 'Intangible Asset'),
        ('service', 'Service'),
        ('other', 'Other'),
    ]

    asset_type = models.CharField(
        max_length=20,
        choices=ASSET_TYPES,
        default='hardware',
        help_text="Type of asset"
    )

    # Detailed categorization
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Asset category (e.g., 'Server', 'Database', 'Network Device')"
    )

    subcategory = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Asset subcategory for further classification"
    )

    # Asset classification and sensitivity
    SENSITIVITY_LEVELS = [
        ('public', 'Public'),
        ('internal', 'Internal'),
        ('confidential', 'Confidential'),
        ('restricted', 'Restricted'),
        ('highly_sensitive', 'Highly Sensitive'),
    ]

    sensitivity_level = models.CharField(
        max_length=20,
        choices=SENSITIVITY_LEVELS,
        default='internal',
        help_text="Data sensitivity or classification level"
    )

    # Criticality and business impact
    CRITICALITY_LEVELS = [
        ('very_low', 'Very Low'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('very_high', 'Very High'),
        ('critical', 'Critical'),
    ]

    criticality_level = models.CharField(
        max_length=20,
        choices=CRITICALITY_LEVELS,
        default='moderate',
        help_text="Business criticality of the asset"
    )

    # Financial information
    acquisition_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Original acquisition cost"
    )

    current_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current assessed value"
    )

    depreciation_method = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Depreciation method used"
    )

    useful_life_years = models.IntegerField(
        null=True,
        blank=True,
        help_text="Expected useful life in years"
    )

    # Location and physical attributes
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Physical or logical location"
    )

    room = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Room or specific location identifier"
    )

    rack_position = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Rack position for data center assets"
    )

    # Technical specifications
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Asset manufacturer or vendor"
    )

    model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Asset model or version"
    )

    serial_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Serial number or unique identifier"
    )

    firmware_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Firmware or software version"
    )

    # Status and lifecycle
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('procured', 'Procured'),
        ('deployed', 'Deployed'),
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('decommissioned', 'Decommissioned'),
        ('disposed', 'Disposed'),
        ('lost_stolen', 'Lost/Stolen'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned',
        help_text="Current lifecycle status"
    )

    # Dates
    acquisition_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date asset was acquired"
    )

    deployment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date asset was deployed"
    )

    last_maintenance_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last maintenance"
    )

    next_maintenance_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled maintenance"
    )

    warranty_expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Warranty expiry date"
    )

    end_of_life_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected end of life date"
    )

    disposal_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date asset was disposed"
    )

    # Ownership and responsibility
    owner_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the asset owner"
    )

    owner_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the asset owner"
    )

    custodian_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the asset custodian"
    )

    custodian_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the asset custodian"
    )

    owning_organization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Organization or department owning the asset"
    )

    # Relationships (embedded ID arrays for DDD pattern)
    parent_asset_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of parent assets (what this asset belongs to)"
    )

    child_asset_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of child assets (what belongs to this asset)"
    )

    related_asset_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related assets"
    )

    supporting_service_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of services that support this asset"
    )

    dependent_service_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of services that depend on this asset"
    )

    # Risk and compliance
    risk_score = models.IntegerField(
        default=0,
        help_text="Calculated risk score (0-100)"
    )

    compliance_status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Compliance status (compliant, non-compliant, etc.)"
    )

    last_assessment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last risk/compliance assessment"
    )

    # Configuration and change management
    configuration_baseline = models.TextField(
        blank=True,
        null=True,
        help_text="Baseline configuration"
    )

    last_configuration_change = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last configuration change timestamp"
    )

    change_history = models.JSONField(
        default=list,
        blank=True,
        help_text="History of configuration changes"
    )

    # Monitoring and alerts
    monitoring_enabled = models.BooleanField(
        default=False,
        help_text="Whether asset is monitored"
    )

    monitoring_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Monitoring configuration and thresholds"
    )

    alert_rules = models.JSONField(
        default=list,
        blank=True,
        help_text="Alert rules for this asset"
    )

    # Metadata and tags
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Asset tags for organization and filtering"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional asset properties"
    )

    # Usage analytics
    usage_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Usage statistics and metrics"
    )

    access_logs = models.JSONField(
        default=list,
        blank=True,
        help_text="Recent access and usage logs"
    )

    class Meta:
        db_table = "assets"
        indexes = [
            models.Index(fields=['asset_type', 'status'], name='asset_type_status_idx'),
            models.Index(fields=['category', 'subcategory'], name='asset_category_idx'),
            models.Index(fields=['owner_user_id'], name='asset_owner_idx'),
            models.Index(fields=['criticality_level'], name='asset_criticality_idx'),
            models.Index(fields=['sensitivity_level'], name='asset_sensitivity_idx'),
            models.Index(fields=['status'], name='asset_status_idx'),
            models.Index(fields=['location'], name='asset_location_idx'),
            models.Index(fields=['next_maintenance_date'], name='asset_maintenance_idx'),
            models.Index(fields=['end_of_life_date'], name='asset_eol_idx'),
            models.Index(fields=['created_at'], name='asset_created_idx'),
        ]
        ordering = ['-created_at']

    def create_asset(
        self,
        asset_id: str,
        name: str,
        asset_type: str,
        owner_user_id: Optional[uuid.UUID] = None,
        owner_username: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new asset"""
        self.asset_id = asset_id
        self.name = name
        self.asset_type = asset_type
        self.owner_user_id = owner_user_id
        self.owner_username = owner_username
        self.description = description
        self.category = category
        self.tags = tags if tags is not None else []
        self.status = 'planned'

        from .domain_events import AssetCreated
        self._raise_event(AssetCreated(
            aggregate_id=self.id,
            asset_id=asset_id,
            asset_type=asset_type,
            owner_user_id=str(owner_user_id) if owner_user_id else None
        ))

    def deploy_asset(self, location: Optional[str] = None, deployment_date: Optional[timezone.date] = None):
        """Deploy the asset"""
        if self.status in ['planned', 'procured']:
            old_status = self.status
            self.status = 'deployed'
            self.location = location or self.location
            self.deployment_date = deployment_date or timezone.now().date()

            from .domain_events import AssetDeployed
            self._raise_event(AssetDeployed(
                aggregate_id=self.id,
                asset_id=self.asset_id,
                old_status=old_status,
                new_status=self.status,
                location=self.location
            ))

    def activate_asset(self):
        """Activate the asset for production use"""
        if self.status == 'deployed':
            self.status = 'active'

            from .domain_events import AssetActivated
            self._raise_event(AssetActivated(
                aggregate_id=self.id,
                asset_id=self.asset_id
            ))

    def decommission_asset(self, reason: str):
        """Decommission the asset"""
        if self.status == 'active':
            self.status = 'decommissioned'

            from .domain_events import AssetDecommissioned
            self._raise_event(AssetDecommissioned(
                aggregate_id=self.id,
                asset_id=self.asset_id,
                reason=reason
            ))

    def dispose_asset(self, disposal_date: Optional[timezone.date] = None):
        """Dispose of the asset"""
        if self.status == 'decommissioned':
            self.status = 'disposed'
            self.disposal_date = disposal_date or timezone.now().date()

            from .domain_events import AssetDisposed
            self._raise_event(AssetDisposed(
                aggregate_id=self.id,
                asset_id=self.asset_id,
                disposal_date=str(self.disposal_date)
            ))

    def update_criticality(self, criticality_level: str, justification: str):
        """Update asset criticality level"""
        old_criticality = self.criticality_level
        self.criticality_level = criticality_level

        from .domain_events import AssetCriticalityUpdated
        self._raise_event(AssetCriticalityUpdated(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            old_criticality=old_criticality,
            new_criticality=criticality_level,
            justification=justification
        ))

    def add_relationship(self, related_asset_id: str, relationship_type: str):
        """Add a relationship to another asset"""
        if relationship_type == 'parent':
            if related_asset_id not in self.parent_asset_ids:
                self.parent_asset_ids.append(related_asset_id)
        elif relationship_type == 'child':
            if related_asset_id not in self.child_asset_ids:
                self.child_asset_ids.append(related_asset_id)
        elif relationship_type == 'related':
            if related_asset_id not in self.related_asset_ids:
                self.related_asset_ids.append(related_asset_id)

        from .domain_events import AssetRelationshipAdded
        self._raise_event(AssetRelationshipAdded(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            related_asset_id=related_asset_id,
            relationship_type=relationship_type
        ))

    def remove_relationship(self, related_asset_id: str, relationship_type: str):
        """Remove a relationship to another asset"""
        if relationship_type == 'parent':
            if related_asset_id in self.parent_asset_ids:
                self.parent_asset_ids.remove(related_asset_id)
        elif relationship_type == 'child':
            if related_asset_id in self.child_asset_ids:
                self.child_asset_ids.remove(related_asset_id)
        elif relationship_type == 'related':
            if related_asset_id in self.related_asset_ids:
                self.related_asset_ids.remove(related_asset_id)

        from .domain_events import AssetRelationshipRemoved
        self._raise_event(AssetRelationshipRemoved(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            related_asset_id=related_asset_id,
            relationship_type=relationship_type
        ))

    def schedule_maintenance(self, maintenance_date: timezone.date, description: str):
        """Schedule maintenance for the asset"""
        self.next_maintenance_date = maintenance_date

        from .domain_events import AssetMaintenanceScheduled
        self._raise_event(AssetMaintenanceScheduled(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            maintenance_date=str(maintenance_date),
            description=description
        ))

    def record_maintenance(self, maintenance_date: Optional[timezone.date] = None, notes: Optional[str] = None):
        """Record completed maintenance"""
        self.last_maintenance_date = maintenance_date or timezone.now().date()

        maintenance_record = {
            'date': str(self.last_maintenance_date),
            'notes': notes or '',
            'recorded_at': str(timezone.now())
        }

        if not self.change_history:
            self.change_history = []
        self.change_history.append(maintenance_record)

        from .domain_events import AssetMaintenanceCompleted
        self._raise_event(AssetMaintenanceCompleted(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            maintenance_date=str(self.last_maintenance_date)
        ))

    def update_risk_score(self, risk_score: int, assessment_date: Optional[timezone.date] = None):
        """Update the asset's risk score"""
        old_score = self.risk_score
        self.risk_score = risk_score
        self.last_assessment_date = assessment_date or timezone.now().date()

        from .domain_events import AssetRiskUpdated
        self._raise_event(AssetRiskUpdated(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            old_score=old_score,
            new_score=risk_score
        ))

    def transfer_ownership(self, new_owner_user_id: uuid.UUID, new_owner_username: str):
        """Transfer asset ownership"""
        old_owner_id = self.owner_user_id
        old_owner_username = self.owner_username

        self.owner_user_id = new_owner_user_id
        self.owner_username = new_owner_username

        from .domain_events import AssetOwnershipTransferred
        self._raise_event(AssetOwnershipTransferred(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            old_owner_id=str(old_owner_id) if old_owner_id else None,
            new_owner_id=str(new_owner_user_id),
            old_owner_username=old_owner_username,
            new_owner_username=new_owner_username
        ))

    def add_service_dependency(self, service_id: str, dependency_type: str):
        """Add a service dependency"""
        if dependency_type == 'supports':
            if service_id not in self.supporting_service_ids:
                self.supporting_service_ids.append(service_id)
        elif dependency_type == 'depends_on':
            if service_id not in self.dependent_service_ids:
                self.dependent_service_ids.append(service_id)

        from .domain_events import AssetServiceDependencyAdded
        self._raise_event(AssetServiceDependencyAdded(
            aggregate_id=self.id,
            asset_id=self.asset_id,
            service_id=service_id,
            dependency_type=dependency_type
        ))

    def log_access(self, user_id: str, action: str, details: Optional[Dict[str, Any]] = None):
        """Log access to the asset"""
        access_record = {
            'timestamp': str(timezone.now()),
            'user_id': user_id,
            'action': action,
            'details': details or {}
        }

        if not self.access_logs:
            self.access_logs = []
        self.access_logs.append(access_record)

        # Keep only last 100 access records
        if len(self.access_logs) > 100:
            self.access_logs = self.access_logs[-100:]

    @property
    def is_active(self) -> bool:
        """Check if asset is in active status"""
        return self.status == 'active'

    @property
    def is_critical(self) -> bool:
        """Check if asset is critical"""
        return self.criticality_level in ['high', 'very_high', 'critical']

    @property
    def is_overdue_for_maintenance(self) -> bool:
        """Check if asset is overdue for maintenance"""
        if not self.next_maintenance_date:
            return False
        return timezone.now().date() > self.next_maintenance_date

    @property
    def is_end_of_life(self) -> bool:
        """Check if asset is at end of life"""
        if not self.end_of_life_date:
            return False
        return timezone.now().date() > self.end_of_life_date

    @property
    def total_relationships(self) -> int:
        """Get total number of asset relationships"""
        return len(self.parent_asset_ids) + len(self.child_asset_ids) + len(self.related_asset_ids)

    @property
    def total_service_dependencies(self) -> int:
        """Get total number of service dependencies"""
        return len(self.supporting_service_ids) + len(self.dependent_service_ids)

    @property
    def age_days(self) -> Optional[int]:
        """Get asset age in days"""
        if not self.acquisition_date:
            return None
        return (timezone.now().date() - self.acquisition_date).days

    def __str__(self):
        return f"Asset({self.asset_id}: {self.name} - {self.asset_type})"
