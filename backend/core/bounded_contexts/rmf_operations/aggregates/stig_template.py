"""
STIG Template Aggregate

Aggregate for managing STIG templates and checklist versions.
Provides template library management for different systems and STIG types.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class StigTemplate(AggregateRoot):
    """
    STIG Template aggregate for managing checklist templates.

    Templates serve as master versions of STIG checklists that can be
    used to create multiple checklist instances for different systems.
    """

    # Template identification
    name = models.CharField(
        max_length=255,
        help_text="Template name (e.g., 'Windows Server 2019 Member Server')"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Template description and usage notes"
    )

    # STIG metadata
    stig_type = models.CharField(
        max_length=255,
        db_index=True,
        help_text="STIG type (e.g., 'Windows Server 2019')"
    )
    stig_release = models.CharField(
        max_length=100,
        help_text="STIG release version"
    )
    stig_version = models.CharField(
        max_length=50,
        help_text="STIG version number"
    )

    # Template classification
    template_type = models.CharField(
        max_length=20,
        choices=[
            ('user', 'User Template'),
            ('system', 'System Template'),
            ('benchmark', 'Benchmark Template'),
        ],
        default='user',
        help_text="Type of template (user-created, system, or benchmark)"
    )

    # Template content
    raw_ckl_content = models.TextField(
        help_text="Raw CKL template content for instantiation"
    )

    # Template metadata
    benchmark_title = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Official benchmark title"
    )
    benchmark_date = models.DateField(
        null=True,
        blank=True,
        help_text="Benchmark publication date"
    )

    # Usage tracking
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of checklists created from this template"
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this template was last used to create a checklist"
    )

    # Template status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is available for use"
    )
    is_official = models.BooleanField(
        default=False,
        help_text="Whether this is an official DISA template"
    )

    # Relationships
    created_from_checklist_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of checklist this template was created from"
    )

    # Tags and organization
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Template tags for organization"
    )

    # System compatibility
    compatible_systems = models.JSONField(
        default=list,
        blank=True,
        help_text="List of compatible system types"
    )

    class Meta:
        db_table = "rmf_operations_stig_templates"
        indexes = [
            models.Index(fields=['stig_type', 'template_type'], name='rmf_template_stig_type_idx'),
            models.Index(fields=['is_active', 'template_type'], name='rmf_template_active_type_idx'),
            models.Index(fields=['created_at'], name='rmf_template_created_idx'),
            models.Index(fields=['usage_count'], name='rmf_template_usage_idx'),
        ]
        ordering = ['-usage_count', '-last_used_at', 'name']

    def create_template(
        self,
        name: str,
        stig_type: str,
        stig_release: str,
        stig_version: str,
        raw_ckl_content: str,
        template_type: str = 'user',
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_from_checklist_id: Optional[uuid.UUID] = None
    ):
        """Create a new STIG template"""
        self.name = name
        self.stig_type = stig_type
        self.stig_release = stig_release
        self.stig_version = stig_version
        self.raw_ckl_content = raw_ckl_content
        self.template_type = template_type
        self.description = description
        self.tags = tags if tags is not None else []
        self.created_from_checklist_id = created_from_checklist_id
        self.is_active = True

        from ..domain_events import StigTemplateCreated
        self._raise_event(StigTemplateCreated(
            aggregate_id=self.id,
            template_name=name,
            stig_type=stig_type,
            template_type=template_type
        ))

    def update_content(self, raw_ckl_content: str, stig_version: Optional[str] = None):
        """Update template content"""
        old_version = self.stig_version
        self.raw_ckl_content = raw_ckl_content
        if stig_version:
            self.stig_version = stig_version

        from ..domain_events import StigTemplateUpdated
        self._raise_event(StigTemplateUpdated(
            aggregate_id=self.id,
            old_version=old_version,
            new_version=self.stig_version
        ))

    def mark_used(self):
        """Mark template as used and update usage statistics"""
        self.usage_count += 1
        self.last_used_at = timezone.now()

    def activate(self):
        """Activate template for use"""
        if not self.is_active:
            self.is_active = True

            from ..domain_events import StigTemplateActivated
            self._raise_event(StigTemplateActivated(
                aggregate_id=self.id,
                template_name=self.name
            ))

    def deactivate(self):
        """Deactivate template"""
        if self.is_active:
            self.is_active = False

            from ..domain_events import StigTemplateDeactivated
            self._raise_event(StigTemplateDeactivated(
                aggregate_id=self.id,
                template_name=self.name
            ))

    def add_compatible_system(self, system_type: str):
        """Add a compatible system type"""
        if system_type not in self.compatible_systems:
            self.compatible_systems.append(system_type)

    def remove_compatible_system(self, system_type: str):
        """Remove a compatible system type"""
        if system_type in self.compatible_systems:
            self.compatible_systems.remove(system_type)

    @property
    def full_stig_identifier(self) -> str:
        """Get full STIG identifier"""
        return f"{self.stig_type} Release {self.stig_release} v{self.stig_version}"

    @property
    def is_outdated(self) -> bool:
        """Check if template might be outdated based on usage patterns"""
        if not self.last_used_at:
            return False

        # Consider outdated if not used in 6 months
        six_months_ago = timezone.now() - timezone.timedelta(days=180)
        return self.last_used_at < six_months_ago

    def __str__(self):
        return f"StigTemplate({self.name} - {self.full_stig_identifier})"
