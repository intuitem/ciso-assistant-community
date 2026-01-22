"""
Framework Aggregate

Aggregate for managing control frameworks like NIST SP 800-53, ISO 27001,
COBIT, and other compliance frameworks with their control structures.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class Framework(AggregateRoot):
    """
    Framework aggregate for comprehensive framework management.

    Manages control frameworks, their versions, and hierarchical
    control structures with mapping capabilities.
    """

    # Basic identification
    name = models.CharField(
        max_length=255,
        help_text="Framework name (e.g., 'NIST SP 800-53', 'ISO 27001')"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the framework"
    )

    framework_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique framework identifier (e.g., 'NIST-800-53', 'ISO-27001')"
    )

    # Framework classification
    FRAMEWORK_TYPES = [
        ('security', 'Security Control Framework'),
        ('privacy', 'Privacy Framework'),
        ('risk', 'Risk Management Framework'),
        ('compliance', 'Compliance Framework'),
        ('governance', 'Governance Framework'),
        ('audit', 'Audit Framework'),
        ('industry', 'Industry-Specific Framework'),
        ('custom', 'Custom Framework'),
    ]

    framework_type = models.CharField(
        max_length=20,
        choices=FRAMEWORK_TYPES,
        default='security',
        help_text="Type of framework"
    )

    # Framework metadata
    provider = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Framework provider/organization (e.g., 'NIST', 'ISO', 'PCI')"
    )

    version = models.CharField(
        max_length=50,
        help_text="Framework version (e.g., 'Rev. 5', '2022')"
    )

    publication_date = models.DateField(
        null=True,
        blank=True,
        help_text="Framework publication date"
    )

    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date framework becomes effective"
    )

    review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled review date"
    )

    # Framework status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('deprecated', 'Deprecated'),
        ('superseded', 'Superseded'),
        ('withdrawn', 'Withdrawn'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Framework status"
    )

    # Framework scope and applicability
    scope = models.TextField(
        blank=True,
        null=True,
        help_text="Framework scope and applicability"
    )

    industry_sectors = models.JSONField(
        default=list,
        blank=True,
        help_text="Applicable industry sectors"
    )

    organization_sizes = models.JSONField(
        default=list,
        blank=True,
        help_text="Applicable organization sizes"
    )

    geographic_regions = models.JSONField(
        default=list,
        blank=True,
        help_text="Applicable geographic regions"
    )

    # Framework structure
    control_count = models.IntegerField(
        default=0,
        help_text="Total number of controls in the framework"
    )

    category_count = models.IntegerField(
        default=0,
        help_text="Number of control categories/families"
    )

    hierarchical_structure = models.JSONField(
        default=dict,
        blank=True,
        help_text="Hierarchical structure of controls and categories"
    )

    control_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mappings to other frameworks"
    )

    # Documentation and resources
    documentation_url = models.URLField(
        blank=True,
        null=True,
        help_text="Official framework documentation URL"
    )

    reference_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="Reference documents and resources"
    )

    # Implementation guidance
    implementation_guidance = models.TextField(
        blank=True,
        null=True,
        help_text="General implementation guidance"
    )

    assessment_methodology = models.TextField(
        blank=True,
        null=True,
        help_text="Framework assessment methodology"
    )

    # Compliance and certification
    certification_body = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Certifying body or authority"
    )

    certification_requirements = models.TextField(
        blank=True,
        null=True,
        help_text="Certification requirements and process"
    )

    # Framework adoption and usage
    adoption_level = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Framework adoption level (e.g., 'Mandatory', 'Recommended')"
    )

    mandatory_for = models.JSONField(
        default=list,
        blank=True,
        help_text="Organizations/industries where framework is mandatory"
    )

    # Relationships (embedded ID arrays)
    related_framework_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related frameworks"
    )

    superseding_framework_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of frameworks that supersede this one"
    )

    superseded_by_framework_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of frameworks that this one supersedes"
    )

    # Usage tracking
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times framework has been used"
    )

    active_assessments = models.IntegerField(
        default=0,
        help_text="Number of active assessments using this framework"
    )

    # Metadata and tags
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Framework tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional framework properties"
    )

    # Framework maturity and updates
    maturity_level = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Framework maturity level"
    )

    last_updated = models.DateField(
        null=True,
        blank=True,
        help_text="Last framework update date"
    )

    update_frequency = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Expected update frequency (e.g., 'Annual', 'Biennial')"
    )

    class Meta:
        db_table = "frameworks"
        indexes = [
            models.Index(fields=['framework_type', 'status'], name='framework_type_status_idx'),
            models.Index(fields=['provider'], name='framework_provider_idx'),
            models.Index(fields=['status'], name='framework_status_idx'),
            models.Index(fields=['publication_date'], name='framework_publication_idx'),
            models.Index(fields=['effective_date'], name='framework_effective_idx'),
            models.Index(fields=['usage_count'], name='framework_usage_idx'),
            models.Index(fields=['created_at'], name='framework_created_idx'),
        ]
        ordering = ['-created_at']

    def create_framework(
        self,
        framework_id: str,
        name: str,
        framework_type: str,
        version: str,
        provider: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new framework"""
        self.framework_id = framework_id
        self.name = name
        self.framework_type = framework_type
        self.version = version
        self.provider = provider
        self.description = description
        self.tags = tags if tags is not None else []
        self.status = 'draft'

        from .domain_events import FrameworkCreated
        self._raise_event(FrameworkCreated(
            aggregate_id=self.id,
            framework_id=framework_id,
            name=name,
            framework_type=framework_type
        ))

    def publish_framework(self):
        """Publish the framework"""
        if self.status == 'draft':
            self.status = 'published'
            self.effective_date = timezone.now().date()

            from .domain_events import FrameworkPublished
            self._raise_event(FrameworkPublished(
                aggregate_id=self.id,
                framework_id=self.framework_id,
                effective_date=str(self.effective_date)
            ))

    def deprecate_framework(self, reason: str, superseding_framework_id: Optional[str] = None):
        """Deprecate the framework"""
        if self.status == 'published':
            self.status = 'deprecated'

            if superseding_framework_id:
                if not self.superseded_by_framework_ids:
                    self.superseded_by_framework_ids = []
                if superseding_framework_id not in self.superseded_by_framework_ids:
                    self.superseded_by_framework_ids.append(superseding_framework_id)

            from .domain_events import FrameworkDeprecated
            self._raise_event(FrameworkDeprecated(
                aggregate_id=self.id,
                framework_id=self.framework_id,
                reason=reason,
                superseding_framework_id=superseding_framework_id
            ))

    def update_structure(self, control_count: int, category_count: int, hierarchical_structure: Dict[str, Any]):
        """Update framework structure information"""
        old_control_count = self.control_count
        old_category_count = self.category_count

        self.control_count = control_count
        self.category_count = category_count
        self.hierarchical_structure = hierarchical_structure
        self.last_updated = timezone.now().date()

        from .domain_events import FrameworkStructureUpdated
        self._raise_event(FrameworkStructureUpdated(
            aggregate_id=self.id,
            framework_id=self.framework_id,
            old_control_count=old_control_count,
            new_control_count=control_count,
            old_category_count=old_category_count,
            new_category_count=category_count
        ))

    def add_mapping(self, target_framework_id: str, mapping_type: str, mapping_data: Dict[str, Any]):
        """Add mapping to another framework"""
        if not self.control_mappings:
            self.control_mappings = {}

        if target_framework_id not in self.control_mappings:
            self.control_mappings[target_framework_id] = {}

        self.control_mappings[target_framework_id][mapping_type] = mapping_data

        from .domain_events import FrameworkMappingAdded
        self._raise_event(FrameworkMappingAdded(
            aggregate_id=self.id,
            framework_id=self.framework_id,
            target_framework_id=target_framework_id,
            mapping_type=mapping_type
        ))

    def add_related_framework(self, related_framework_id: str, relationship_type: str):
        """Add relationship to another framework"""
        if relationship_type == 'related':
            if related_framework_id not in self.related_framework_ids:
                self.related_framework_ids.append(related_framework_id)
        elif relationship_type == 'supersedes':
            if related_framework_id not in self.superseding_framework_ids:
                self.superseding_framework_ids.append(related_framework_id)
        elif relationship_type == 'superseded_by':
            if related_framework_id not in self.superseded_by_framework_ids:
                self.superseded_by_framework_ids.append(related_framework_id)

        from .domain_events import FrameworkRelationshipAdded
        self._raise_event(FrameworkRelationshipAdded(
            aggregate_id=self.id,
            framework_id=self.framework_id,
            related_framework_id=related_framework_id,
            relationship_type=relationship_type
        ))

    def record_usage(self):
        """Record framework usage"""
        self.usage_count += 1

    def update_adoption_statistics(self, active_assessments: int):
        """Update adoption statistics"""
        self.active_assessments = active_assessments

    def schedule_review(self, review_date: timezone.date):
        """Schedule framework review"""
        self.review_date = review_date

        from .domain_events import FrameworkReviewScheduled
        self._raise_event(FrameworkReviewScheduled(
            aggregate_id=self.id,
            framework_id=self.framework_id,
            review_date=str(review_date)
        ))

    def conduct_review(self, review_date: Optional[timezone.date] = None, notes: Optional[str] = None):
        """Conduct framework review"""
        self.last_updated = review_date or timezone.now().date()
        self.review_date = None  # Clear scheduled review

        from .domain_events import FrameworkReviewed
        self._raise_event(FrameworkReviewed(
            aggregate_id=self.id,
            framework_id=self.framework_id,
            review_date=str(self.last_updated),
            notes=notes
        ))

    @property
    def is_published(self) -> bool:
        """Check if framework is published"""
        return self.status == 'published'

    @property
    def is_current(self) -> bool:
        """Check if framework is current (not deprecated/superseded)"""
        return self.status in ['published', 'draft']

    @property
    def is_overdue_for_review(self) -> bool:
        """Check if framework is overdue for review"""
        if not self.review_date:
            return False
        return timezone.now().date() > self.review_date

    @property
    def total_mappings(self) -> int:
        """Get total number of framework mappings"""
        return len(self.control_mappings)

    @property
    def total_relationships(self) -> int:
        """Get total number of framework relationships"""
        return len(self.related_framework_ids) + len(self.superseding_framework_ids) + len(self.superseded_by_framework_ids)

    def get_mappings_to_framework(self, target_framework_id: str) -> Dict[str, Any]:
        """Get mappings to a specific framework"""
        return self.control_mappings.get(target_framework_id, {})

    def is_superseded_by(self, framework_id: str) -> bool:
        """Check if this framework is superseded by another"""
        return framework_id in self.superseded_by_framework_ids

    def supersedes(self, framework_id: str) -> bool:
        """Check if this framework supersedes another"""
        return framework_id in self.superseding_framework_ids

    def __str__(self):
        return f"Framework({self.framework_id}: {self.name} v{self.version})"
