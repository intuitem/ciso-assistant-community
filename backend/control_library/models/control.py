"""
Control Aggregate

Aggregate for managing individual controls within frameworks,
including control statements, guidance, and implementation details.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class Control(AggregateRoot):
    """
    Control aggregate for comprehensive control management.

    Manages individual controls within frameworks, including statements,
    guidance, parameters, and implementation references.
    """

    # Basic identification
    control_id = models.CharField(
        max_length=100,
        help_text="Control identifier (e.g., 'AC-2', 'IA-5.1')"
    )

    title = models.CharField(
        max_length=500,
        help_text="Control title"
    )

    framework_id = models.UUIDField(
        db_index=True,
        help_text="ID of the framework this control belongs to"
    )

    framework_control_id = models.CharField(
        max_length=100,
        help_text="Unique control ID within the framework"
    )

    # Control classification
    CONTROL_TYPES = [
        ('preventive', 'Preventive'),
        ('detective', 'Detective'),
        ('corrective', 'Corrective'),
        ('deterrent', 'Deterrent'),
        ('compensating', 'Compensating'),
        ('recovery', 'Recovery'),
        ('directive', 'Directive'),
    ]

    control_type = models.CharField(
        max_length=20,
        choices=CONTROL_TYPES,
        default='preventive',
        help_text="Type of control"
    )

    # Control family/category
    family = models.CharField(
        max_length=100,
        help_text="Control family (e.g., 'Access Control', 'Incident Response')"
    )

    subfamily = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Control subfamily for further categorization"
    )

    # Control content
    statement = models.TextField(
        help_text="Control statement/requirement"
    )

    discussion = models.TextField(
        blank=True,
        null=True,
        help_text="Discussion/elaboration of the control"
    )

    guidance = models.TextField(
        blank=True,
        null=True,
        help_text="Implementation guidance"
    )

    # Control parameters
    parameters = models.JSONField(
        default=list,
        blank=True,
        help_text="Control parameters and their values"
    )

    # Control relationships
    parent_control_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Parent control ID (for hierarchical controls)"
    )

    child_control_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Child control IDs"
    )

    related_control_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Related control IDs within same framework"
    )

    # Control importance and priority
    PRIORITY_LEVELS = [
        ('very_low', 'Very Low'),
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('very_high', 'Very High'),
        ('critical', 'Critical'),
    ]

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_LEVELS,
        default='moderate',
        help_text="Control priority/importance"
    )

    # Control baseline inclusion
    BASELINE_LEVELS = [
        ('low', 'Low Baseline'),
        ('moderate', 'Moderate Baseline'),
        ('high', 'High Baseline'),
        ('privacy', 'Privacy Baseline'),
        ('li_saas', 'LI-SaaS Baseline'),
        ('custom', 'Custom Baseline'),
    ]

    baseline_inclusion = models.JSONField(
        default=list,
        blank=True,
        help_text="Baselines that include this control"
    )

    # Control status within framework
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('deprecated', 'Deprecated'),
        ('withdrawn', 'Withdrawn'),
        ('superseded', 'Superseded'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Control status"
    )

    # Implementation references
    implementation_references = models.JSONField(
        default=list,
        blank=True,
        help_text="References to implementation guidance"
    )

    assessment_methods = models.JSONField(
        default=list,
        blank=True,
        help_text="Methods for assessing control implementation"
    )

    testing_procedures = models.JSONField(
        default=list,
        blank=True,
        help_text="Procedures for testing control effectiveness"
    )

    # Control mappings to other frameworks
    control_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mappings to controls in other frameworks"
    )

    # Control enhancement/supplemental guidance
    enhancements = models.JSONField(
        default=list,
        blank=True,
        help_text="Control enhancements and supplemental guidance"
    )

    # Control metadata
    sort_order = models.IntegerField(
        default=0,
        help_text="Sort order within family"
    )

    version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Control version"
    )

    last_updated = models.DateField(
        null=True,
        blank=True,
        help_text="Last update date"
    )

    # Usage and implementation tracking
    implementation_count = models.IntegerField(
        default=0,
        help_text="Number of implementations of this control"
    )

    assessment_count = models.IntegerField(
        default=0,
        help_text="Number of assessments of this control"
    )

    average_compliance_score = models.FloatField(
        default=0.0,
        help_text="Average compliance score across assessments"
    )

    # Tags and metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Control tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional control properties"
    )

    class Meta:
        db_table = "controls"
        indexes = [
            models.Index(fields=['framework_id', 'control_id'], name='control_framework_id_idx'),
            models.Index(fields=['framework_id', 'family'], name='control_framework_family_idx'),
            models.Index(fields=['control_type'], name='control_type_idx'),
            models.Index(fields=['family'], name='control_family_idx'),
            models.Index(fields=['priority'], name='control_priority_idx'),
            models.Index(fields=['status'], name='control_status_idx'),
            models.Index(fields=['sort_order'], name='control_sort_idx'),
            models.Index(fields=['implementation_count'], name='control_implementation_idx'),
            models.Index(fields=['created_at'], name='control_created_idx'),
        ]
        ordering = ['framework_id', 'family', 'sort_order']
        unique_together = [['framework_id', 'framework_control_id']]

    def create_control(
        self,
        framework_id: uuid.UUID,
        framework_control_id: str,
        control_id: str,
        title: str,
        family: str,
        statement: str,
        control_type: str = 'preventive',
        discussion: Optional[str] = None,
        guidance: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new control"""
        self.framework_id = framework_id
        self.framework_control_id = framework_control_id
        self.control_id = control_id
        self.title = title
        self.family = family
        self.statement = statement
        self.control_type = control_type
        self.discussion = discussion
        self.guidance = guidance
        self.tags = tags if tags is not None else []

        from .domain_events import ControlCreated
        self._raise_event(ControlCreated(
            aggregate_id=self.id,
            framework_control_id=framework_control_id,
            control_id=control_id,
            title=title,
            family=family
        ))

    def update_content(
        self,
        statement: Optional[str] = None,
        discussion: Optional[str] = None,
        guidance: Optional[str] = None,
        parameters: Optional[List[Dict[str, Any]]] = None
    ):
        """Update control content"""
        if statement is not None:
            self.statement = statement
        if discussion is not None:
            self.discussion = discussion
        if guidance is not None:
            self.guidance = guidance
        if parameters is not None:
            self.parameters = parameters

        self.last_updated = timezone.now().date()

        from .domain_events import ControlContentUpdated
        self._raise_event(ControlContentUpdated(
            aggregate_id=self.id,
            control_id=self.control_id,
            framework_control_id=self.framework_control_id
        ))

    def add_enhancement(self, enhancement_id: str, title: str, description: str):
        """Add control enhancement"""
        enhancement = {
            'id': enhancement_id,
            'title': title,
            'description': description,
            'added_at': str(timezone.now())
        }

        if not self.enhancements:
            self.enhancements = []
        self.enhancements.append(enhancement)

        from .domain_events import ControlEnhancementAdded
        self._raise_event(ControlEnhancementAdded(
            aggregate_id=self.id,
            control_id=self.control_id,
            enhancement_id=enhancement_id,
            title=title
        ))

    def add_mapping(self, target_framework_id: str, target_control_id: str, mapping_type: str, confidence: str = 'high'):
        """Add mapping to control in another framework"""
        if not self.control_mappings:
            self.control_mappings = {}

        if target_framework_id not in self.control_mappings:
            self.control_mappings[target_framework_id] = []

        mapping = {
            'target_control_id': target_control_id,
            'mapping_type': mapping_type,
            'confidence': confidence,
            'mapped_at': str(timezone.now())
        }

        self.control_mappings[target_framework_id].append(mapping)

        from .domain_events import ControlMappingAdded
        self._raise_event(ControlMappingAdded(
            aggregate_id=self.id,
            control_id=self.control_id,
            target_framework_id=target_framework_id,
            target_control_id=target_control_id,
            mapping_type=mapping_type
        ))

    def add_related_control(self, related_control_id: str, relationship_type: str):
        """Add relationship to another control"""
        if relationship_type == 'child':
            if related_control_id not in self.child_control_ids:
                self.child_control_ids.append(related_control_id)
        elif relationship_type == 'related':
            if related_control_id not in self.related_control_ids:
                self.related_control_ids.append(related_control_id)

        from .domain_events import ControlRelationshipAdded
        self._raise_event(ControlRelationshipAdded(
            aggregate_id=self.id,
            control_id=self.control_id,
            related_control_id=related_control_id,
            relationship_type=relationship_type
        ))

    def add_baseline_inclusion(self, baseline: str):
        """Add baseline inclusion"""
        if baseline not in self.baseline_inclusion:
            self.baseline_inclusion.append(baseline)

    def update_priority(self, priority: str, justification: str):
        """Update control priority"""
        old_priority = self.priority
        self.priority = priority

        from .domain_events import ControlPriorityUpdated
        self._raise_event(ControlPriorityUpdated(
            aggregate_id=self.id,
            control_id=self.control_id,
            old_priority=old_priority,
            new_priority=priority,
            justification=justification
        ))

    def record_implementation(self):
        """Record control implementation"""
        self.implementation_count += 1

    def record_assessment(self, compliance_score: float):
        """Record control assessment"""
        self.assessment_count += 1

        # Update rolling average
        if self.assessment_count == 1:
            self.average_compliance_score = compliance_score
        else:
            self.average_compliance_score = (
                (self.average_compliance_score * (self.assessment_count - 1)) + compliance_score
            ) / self.assessment_count

    def deprecate_control(self, reason: str, replacement_control_id: Optional[str] = None):
        """Deprecate the control"""
        if self.status == 'active':
            self.status = 'deprecated'

            from .domain_events import ControlDeprecated
            self._raise_event(ControlDeprecated(
                aggregate_id=self.id,
                control_id=self.control_id,
                reason=reason,
                replacement_control_id=replacement_control_id
            ))

    @property
    def is_active(self) -> bool:
        """Check if control is active"""
        return self.status == 'active'

    @property
    def is_high_priority(self) -> bool:
        """Check if control is high priority"""
        return self.priority in ['high', 'very_high', 'critical']

    @property
    def has_enhancements(self) -> bool:
        """Check if control has enhancements"""
        return len(self.enhancements) > 0

    @property
    def has_mappings(self) -> bool:
        """Check if control has mappings to other frameworks"""
        return len(self.control_mappings) > 0

    @property
    def total_relationships(self) -> int:
        """Get total number of control relationships"""
        return len(self.child_control_ids) + len(self.related_control_ids)

    @property
    def implementation_rate(self) -> float:
        """Get implementation rate as percentage"""
        if self.assessment_count == 0:
            return 0.0
        return (self.implementation_count / self.assessment_count) * 100

    @property
    def compliance_rate(self) -> float:
        """Get average compliance rate"""
        return self.average_compliance_score

    def get_mappings_to_framework(self, target_framework_id: str) -> List[Dict[str, Any]]:
        """Get mappings to a specific framework"""
        return self.control_mappings.get(target_framework_id, [])

    def get_enhancement_by_id(self, enhancement_id: str) -> Optional[Dict[str, Any]]:
        """Get enhancement by ID"""
        for enhancement in self.enhancements:
            if enhancement.get('id') == enhancement_id:
                return enhancement
        return None

    def __str__(self):
        return f"Control({self.framework_control_id}: {self.title})"
