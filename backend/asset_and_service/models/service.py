"""
Service Aggregate

Aggregate for managing business and technical services including
service catalog, dependencies, SLAs, and lifecycle management.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class Service(AggregateRoot):
    """
    Service aggregate for comprehensive service management.

    Manages business services, technical services, service catalog,
    dependencies, SLAs, and service lifecycle.
    """

    # Basic identification
    name = models.CharField(
        max_length=255,
        help_text="Service name"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the service"
    )

    service_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique service identifier (e.g., SVC-001, APP-001)"
    )

    # Service classification
    SERVICE_TYPES = [
        ('business', 'Business Service'),
        ('technical', 'Technical Service'),
        ('application', 'Application Service'),
        ('infrastructure', 'Infrastructure Service'),
        ('network', 'Network Service'),
        ('security', 'Security Service'),
        ('cloud', 'Cloud Service'),
        ('other', 'Other'),
    ]

    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPES,
        default='technical',
        help_text="Type of service"
    )

    # Service category and classification
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Service category (e.g., 'Authentication', 'Database', 'Web Service')"
    )

    criticality_level = models.CharField(
        max_length=20,
        choices=[
            ('very_low', 'Very Low'),
            ('low', 'Low'),
            ('moderate', 'Moderate'),
            ('high', 'High'),
            ('very_high', 'Very High'),
            ('critical', 'Critical'),
        ],
        default='moderate',
        help_text="Business criticality of the service"
    )

    # Service lifecycle status
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('design', 'Design'),
        ('development', 'Development'),
        ('testing', 'Testing'),
        ('deployment', 'Deployment'),
        ('active', 'Active'),
        ('maintenance', 'Maintenance'),
        ('deprecated', 'Deprecated'),
        ('retired', 'Retired'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned',
        help_text="Current lifecycle status"
    )

    # Service owner and responsibility
    owner_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the service owner"
    )

    owner_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the service owner"
    )

    manager_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of the service manager"
    )

    manager_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of the service manager"
    )

    owning_organization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Organization or department owning the service"
    )

    # Service portfolio information
    portfolio = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Service portfolio (e.g., 'Core', 'Support', 'Development')"
    )

    version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Service version"
    )

    # Service Level Agreements (SLAs)
    sla_availability_target = models.FloatField(
        null=True,
        blank=True,
        help_text="SLA availability target as percentage (e.g., 99.9)"
    )

    sla_response_time_target = models.IntegerField(
        null=True,
        blank=True,
        help_text="SLA response time target in seconds"
    )

    sla_resolution_time_target = models.IntegerField(
        null=True,
        blank=True,
        help_text="SLA resolution time target in seconds"
    )

    # Service dependencies (embedded ID arrays)
    dependent_service_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of services this service depends on"
    )

    supporting_service_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of services that support this service"
    )

    dependent_asset_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of assets this service depends on"
    )

    supporting_asset_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of assets that support this service"
    )

    # Service consumers and stakeholders
    consumer_groups = models.JSONField(
        default=list,
        blank=True,
        help_text="Groups or roles that consume this service"
    )

    stakeholder_contacts = models.JSONField(
        default=list,
        blank=True,
        help_text="Key stakeholders and their contact information"
    )

    # Service documentation
    documentation_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to service documentation"
    )

    api_documentation_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to API documentation"
    )

    runbook_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL to operational runbook"
    )

    # Service monitoring and metrics
    monitoring_enabled = models.BooleanField(
        default=False,
        help_text="Whether service is monitored"
    )

    monitoring_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Monitoring configuration and endpoints"
    )

    health_check_url = models.URLField(
        blank=True,
        null=True,
        help_text="Health check endpoint URL"
    )

    # Service metrics and KPIs
    availability_percentage = models.FloatField(
        default=0.0,
        help_text="Current availability percentage"
    )

    average_response_time = models.IntegerField(
        default=0,
        help_text="Average response time in milliseconds"
    )

    error_rate_percentage = models.FloatField(
        default=0.0,
        help_text="Error rate percentage"
    )

    throughput_requests_per_minute = models.IntegerField(
        default=0,
        help_text="Throughput in requests per minute"
    )

    # Incident and problem management
    incident_count = models.IntegerField(
        default=0,
        help_text="Number of incidents in the last 30 days"
    )

    open_incident_count = models.IntegerField(
        default=0,
        help_text="Number of currently open incidents"
    )

    problem_count = models.IntegerField(
        default=0,
        help_text="Number of known problems"
    )

    # Change management
    planned_changes = models.JSONField(
        default=list,
        blank=True,
        help_text="Upcoming planned changes"
    )

    emergency_changes = models.IntegerField(
        default=0,
        help_text="Number of emergency changes in last 30 days"
    )

    # Cost and budgeting
    annual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual cost of the service"
    )

    cost_center = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Cost center code"
    )

    budget_category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Budget category"
    )

    # Service continuity and disaster recovery
    recovery_time_objective = models.IntegerField(
        null=True,
        blank=True,
        help_text="Recovery Time Objective in minutes"
    )

    recovery_point_objective = models.IntegerField(
        null=True,
        blank=True,
        help_text="Recovery Point Objective in minutes"
    )

    backup_frequency = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Backup frequency (e.g., 'daily', 'hourly')"
    )

    # Dates and milestones
    planned_go_live_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned go-live date"
    )

    actual_go_live_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual go-live date"
    )

    last_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of last service review"
    )

    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of next scheduled review"
    )

    end_of_life_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned end of life date"
    )

    # Service level and quality metrics
    customer_satisfaction_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Customer satisfaction score (1-5)"
    )

    service_quality_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Overall service quality score (1-5)"
    )

    # Configuration and technical details
    configuration_items = models.JSONField(
        default=list,
        blank=True,
        help_text="Configuration items related to this service"
    )

    technical_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Technical specifications and details"
    )

    # Metadata and tags
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Service tags for organization and filtering"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional service properties"
    )

    class Meta:
        db_table = "services"
        indexes = [
            models.Index(fields=['service_type', 'status'], name='service_type_status_idx'),
            models.Index(fields=['category'], name='service_category_idx'),
            models.Index(fields=['owner_user_id'], name='service_owner_idx'),
            models.Index(fields=['criticality_level'], name='service_criticality_idx'),
            models.Index(fields=['status'], name='service_status_idx'),
            models.Index(fields=['portfolio'], name='service_portfolio_idx'),
            models.Index(fields=['next_review_date'], name='service_review_idx'),
            models.Index(fields=['end_of_life_date'], name='service_eol_idx'),
            models.Index(fields=['created_at'], name='service_created_idx'),
        ]
        ordering = ['-created_at']

    def create_service(
        self,
        service_id: str,
        name: str,
        service_type: str,
        owner_user_id: Optional[uuid.UUID] = None,
        owner_username: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new service"""
        self.service_id = service_id
        self.name = name
        self.service_type = service_type
        self.owner_user_id = owner_user_id
        self.owner_username = owner_username
        self.description = description
        self.category = category
        self.tags = tags if tags is not None else []
        self.status = 'planned'

        from .domain_events import ServiceCreated
        self._raise_event(ServiceCreated(
            aggregate_id=self.id,
            service_id=service_id,
            service_type=service_type,
            owner_user_id=str(owner_user_id) if owner_user_id else None
        ))

    def activate_service(self, go_live_date: Optional[timezone.date] = None):
        """Activate the service"""
        if self.status in ['planned', 'design', 'development', 'testing', 'deployment']:
            self.status = 'active'
            self.actual_go_live_date = go_live_date or timezone.now().date()

            from .domain_events import ServiceActivated
            self._raise_event(ServiceActivated(
                aggregate_id=self.id,
                service_id=self.service_id,
                go_live_date=str(self.actual_go_live_date)
            ))

    def update_status(self, new_status: str, reason: str):
        """Update service status"""
        old_status = self.status
        self.status = new_status

        from .domain_events import ServiceStatusUpdated
        self._raise_event(ServiceStatusUpdated(
            aggregate_id=self.id,
            service_id=self.service_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason
        ))

    def add_dependency(self, dependency_id: str, dependency_type: str):
        """Add a service or asset dependency"""
        if dependency_type == 'service':
            if dependency_id not in self.dependent_service_ids:
                self.dependent_service_ids.append(dependency_id)
        elif dependency_type == 'asset':
            if dependency_id not in self.dependent_asset_ids:
                self.dependent_asset_ids.append(dependency_id)
        elif dependency_type == 'supporting_service':
            if dependency_id not in self.supporting_service_ids:
                self.supporting_service_ids.append(dependency_id)
        elif dependency_type == 'supporting_asset':
            if dependency_id not in self.supporting_asset_ids:
                self.supporting_asset_ids.append(dependency_id)

        from .domain_events import ServiceDependencyAdded
        self._raise_event(ServiceDependencyAdded(
            aggregate_id=self.id,
            service_id=self.service_id,
            dependency_id=dependency_id,
            dependency_type=dependency_type
        ))

    def remove_dependency(self, dependency_id: str, dependency_type: str):
        """Remove a service or asset dependency"""
        if dependency_type == 'service':
            if dependency_id in self.dependent_service_ids:
                self.dependent_service_ids.remove(dependency_id)
        elif dependency_type == 'asset':
            if dependency_id in self.dependent_asset_ids:
                self.dependent_asset_ids.remove(dependency_id)
        elif dependency_type == 'supporting_service':
            if dependency_id in self.supporting_service_ids:
                self.supporting_service_ids.remove(dependency_id)
        elif dependency_type == 'supporting_asset':
            if dependency_id in self.supporting_asset_ids:
                self.supporting_asset_ids.remove(dependency_id)

        from .domain_events import ServiceDependencyRemoved
        self._raise_event(ServiceDependencyRemoved(
            aggregate_id=self.id,
            service_id=self.service_id,
            dependency_id=dependency_id,
            dependency_type=dependency_type
        ))

    def update_metrics(self, metrics: Dict[str, Any]):
        """Update service performance metrics"""
        old_metrics = {
            'availability_percentage': self.availability_percentage,
            'average_response_time': self.average_response_time,
            'error_rate_percentage': self.error_rate_percentage,
            'throughput_requests_per_minute': self.throughput_requests_per_minute
        }

        self.availability_percentage = metrics.get('availability_percentage', self.availability_percentage)
        self.average_response_time = metrics.get('average_response_time', self.average_response_time)
        self.error_rate_percentage = metrics.get('error_rate_percentage', self.error_rate_percentage)
        self.throughput_requests_per_minute = metrics.get('throughput_requests_per_minute', self.throughput_requests_per_minute)

        from .domain_events import ServiceMetricsUpdated
        self._raise_event(ServiceMetricsUpdated(
            aggregate_id=self.id,
            service_id=self.service_id,
            old_metrics=old_metrics,
            new_metrics=metrics
        ))

    def record_incident(self, incident_id: str, severity: str, description: str):
        """Record a service incident"""
        self.incident_count += 1
        self.open_incident_count += 1

        from .domain_events import ServiceIncidentRecorded
        self._raise_event(ServiceIncidentRecorded(
            aggregate_id=self.id,
            service_id=self.service_id,
            incident_id=incident_id,
            severity=severity,
            description=description
        ))

    def resolve_incident(self, incident_id: str):
        """Resolve a service incident"""
        if self.open_incident_count > 0:
            self.open_incident_count -= 1

        from .domain_events import ServiceIncidentResolved
        self._raise_event(ServiceIncidentResolved(
            aggregate_id=self.id,
            service_id=self.service_id,
            incident_id=incident_id
        ))

    def schedule_change(self, change_id: str, change_type: str, scheduled_date: timezone.date, description: str):
        """Schedule a change for this service"""
        change_record = {
            'id': change_id,
            'type': change_type,
            'scheduled_date': str(scheduled_date),
            'description': description,
            'status': 'planned'
        }

        if not self.planned_changes:
            self.planned_changes = []
        self.planned_changes.append(change_record)

        from .domain_events import ServiceChangeScheduled
        self._raise_event(ServiceChangeScheduled(
            aggregate_id=self.id,
            service_id=self.service_id,
            change_id=change_id,
            change_type=change_type,
            scheduled_date=str(scheduled_date)
        ))

    def update_change_status(self, change_id: str, status: str):
        """Update the status of a scheduled change"""
        for change in self.planned_changes:
            if change['id'] == change_id:
                old_status = change['status']
                change['status'] = status
                change['updated_at'] = str(timezone.now())

                from .domain_events import ServiceChangeStatusUpdated
                self._raise_event(ServiceChangeStatusUpdated(
                    aggregate_id=self.id,
                    service_id=self.service_id,
                    change_id=change_id,
                    old_status=old_status,
                    new_status=status
                ))
                break

    def update_sla_metrics(self, sla_data: Dict[str, Any]):
        """Update SLA metrics"""
        old_sla = {
            'availability_target': self.sla_availability_target,
            'response_time_target': self.sla_response_time_target,
            'resolution_time_target': self.sla_resolution_time_target
        }

        self.sla_availability_target = sla_data.get('availability_target', self.sla_availability_target)
        self.sla_response_time_target = sla_data.get('response_time_target', self.sla_response_time_target)
        self.sla_resolution_time_target = sla_data.get('resolution_time_target', self.sla_resolution_time_target)

        from .domain_events import ServiceSLAUpdated
        self._raise_event(ServiceSLAUpdated(
            aggregate_id=self.id,
            service_id=self.service_id,
            old_sla=old_sla,
            new_sla=sla_data
        ))

    def transfer_ownership(self, new_owner_user_id: uuid.UUID, new_owner_username: str):
        """Transfer service ownership"""
        old_owner_id = self.owner_user_id
        old_owner_username = self.owner_username

        self.owner_user_id = new_owner_user_id
        self.owner_username = new_owner_username

        from .domain_events import ServiceOwnershipTransferred
        self._raise_event(ServiceOwnershipTransferred(
            aggregate_id=self.id,
            service_id=self.service_id,
            old_owner_id=str(old_owner_id) if old_owner_id else None,
            new_owner_id=str(new_owner_user_id),
            old_owner_username=old_owner_username,
            new_owner_username=new_owner_username
        ))

    def schedule_review(self, review_date: timezone.date):
        """Schedule next service review"""
        self.next_review_date = review_date

        from .domain_events import ServiceReviewScheduled
        self._raise_event(ServiceReviewScheduled(
            aggregate_id=self.id,
            service_id=self.service_id,
            review_date=str(review_date)
        ))

    def conduct_review(self, review_date: Optional[timezone.date] = None, notes: Optional[str] = None):
        """Conduct service review"""
        self.last_review_date = review_date or timezone.now().date()

        from .domain_events import ServiceReviewed
        self._raise_event(ServiceReviewed(
            aggregate_id=self.id,
            service_id=self.service_id,
            review_date=str(self.last_review_date),
            notes=notes
        ))

    @property
    def is_active(self) -> bool:
        """Check if service is active"""
        return self.status == 'active'

    @property
    def is_critical(self) -> bool:
        """Check if service is critical"""
        return self.criticality_level in ['high', 'very_high', 'critical']

    @property
    def total_dependencies(self) -> int:
        """Get total number of dependencies"""
        return len(self.dependent_service_ids) + len(self.dependent_asset_ids)

    @property
    def total_supporting_elements(self) -> int:
        """Get total number of supporting elements"""
        return len(self.supporting_service_ids) + len(self.supporting_asset_ids)

    @property
    def sla_compliance_percentage(self) -> float:
        """Calculate SLA compliance percentage"""
        if not self.sla_availability_target:
            return 0.0
        return min(100.0, (self.availability_percentage / self.sla_availability_target) * 100)

    @property
    def has_open_incidents(self) -> bool:
        """Check if service has open incidents"""
        return self.open_incident_count > 0

    @property
    def is_overdue_for_review(self) -> bool:
        """Check if service is overdue for review"""
        if not self.next_review_date:
            return False
        return timezone.now().date() > self.next_review_date

    def __str__(self):
        return f"Service({self.service_id}: {self.name} - {self.service_type})"
