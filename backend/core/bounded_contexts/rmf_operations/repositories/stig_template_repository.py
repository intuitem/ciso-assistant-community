"""
STIG Template Repository

Repository for StigTemplate aggregates with specialized methods
for template library management and usage analytics.
"""

from typing import Optional, List, Dict, Any
import uuid

from django.db import models
from django.db.models import Sum

from core.domain.repository import BaseRepository
from ..aggregates.stig_template import StigTemplate


class StigTemplateRepository(BaseRepository[StigTemplate]):
    """
    Repository for StigTemplate aggregates.

    Provides methods for managing STIG templates and their usage
    across the organization.
    """

    def __init__(self):
        super().__init__(StigTemplate)

    def find_by_stig_type(self, stig_type: str) -> List[StigTemplate]:
        """Find all templates for a specific STIG type"""
        return list(StigTemplate.objects.filter(stig_type=stig_type))

    def find_active_templates(self, stig_type: Optional[str] = None) -> List[StigTemplate]:
        """Find all active templates, optionally filtered by STIG type"""
        queryset = StigTemplate.objects.filter(is_active=True)
        if stig_type:
            queryset = queryset.filter(stig_type=stig_type)
        return list(queryset.order_by('-usage_count', '-last_used_at'))

    def find_popular_templates(self, limit: int = 10) -> List[StigTemplate]:
        """Find most popular templates by usage count"""
        return list(StigTemplate.objects.filter(is_active=True).order_by('-usage_count')[:limit])

    def find_recently_used(self, limit: int = 10) -> List[StigTemplate]:
        """Find recently used templates"""
        return list(StigTemplate.objects.filter(
            is_active=True,
            last_used_at__isnull=False
        ).order_by('-last_used_at')[:limit])

    def find_templates_by_compatibility(self, system_type: str) -> List[StigTemplate]:
        """Find templates compatible with a specific system type"""
        # This would require a more complex query to check the JSON array
        # For now, return all active templates
        return list(StigTemplate.objects.filter(is_active=True))

    def search_templates(self, query: str, stig_type: Optional[str] = None) -> List[StigTemplate]:
        """Search templates by name, description, or STIG type"""
        queryset = StigTemplate.objects.filter(is_active=True).filter(
            name__icontains=query
        ) | StigTemplate.objects.filter(
            description__icontains=query
        ) | StigTemplate.objects.filter(
            stig_type__icontains=query
        )

        if stig_type:
            queryset = queryset.filter(stig_type=stig_type)

        return list(queryset.distinct().order_by('-usage_count'))

    def get_template_usage_stats(self) -> Dict[str, Any]:
        """Get comprehensive template usage statistics"""
        total_templates = StigTemplate.objects.count()
        active_templates = StigTemplate.objects.filter(is_active=True).count()
        total_usage = StigTemplate.objects.aggregate(
            total_usage=Sum('usage_count')
        )['total_usage'] or 0

        # STIG type distribution
        stig_types = StigTemplate.objects.values('stig_type').annotate(
            count=models.Count('id'),
            total_usage=Sum('usage_count')
        ).order_by('-count')

        return {
            'total_templates': total_templates,
            'active_templates': active_templates,
            'inactive_templates': total_templates - active_templates,
            'total_usage_count': total_usage,
            'stig_type_distribution': list(stig_types),
            'most_used_templates': self.find_popular_templates(5),
            'recently_used_templates': self.find_recently_used(5)
        }

    def create_from_checklist(self, checklist_id: uuid.UUID, name: str,
                            description: Optional[str] = None) -> Optional[StigTemplate]:
        """Create a template from an existing checklist"""
        try:
            from ..repositories.stig_checklist_repository import StigChecklistRepository
            checklist_repo = StigChecklistRepository()
            checklist = checklist_repo.get_by_id(checklist_id)

            if not checklist:
                return None

            # Extract raw CKL content from the checklist's rawCklData JSON
            raw_content = ''
            if checklist.rawCklData:
                raw_content = checklist.rawCklData.get('raw_content', str(checklist.rawCklData))

            template = StigTemplate()
            template.create_template(
                name=name,
                stig_type=checklist.stigType or '',
                stig_release=checklist.stigRelease or '',
                stig_version=checklist.version or '',
                raw_ckl_content=raw_content,
                description=description,
                created_from_checklist_id=checklist_id
            )

            self.save(template)
            return template

        except Exception as e:
            # Log error but don't expose internal details
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating template from checklist: {e}")
            return None

    def increment_usage(self, template_id: uuid.UUID) -> bool:
        """Increment usage count for a template"""
        try:
            template = self.get_by_id(template_id)
            if template:
                template.mark_used()
                self.save(template)
                return True
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error incrementing template usage: {e}")
            return False

    def deactivate_unused_templates(self, days_unused: int = 365) -> int:
        """Deactivate templates that haven't been used for specified days"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days_unused)
        unused_templates = StigTemplate.objects.filter(
            is_active=True,
            last_used_at__lt=cutoff_date
        )

        count = 0
        for template in unused_templates:
            template.deactivate()
            self.save(template)
            count += 1

        return count

    def validate_template_content(self, template_id: uuid.UUID) -> Dict[str, Any]:
        """Validate template content and structure"""
        try:
            template = self.get_by_id(template_id)
            if not template:
                return {'valid': False, 'errors': ['Template not found']}

            errors = []

            # Check required fields
            if not template.raw_ckl_content:
                errors.append('Missing CKL content')

            if not template.stig_type:
                errors.append('Missing STIG type')

            if not template.stig_release:
                errors.append('Missing STIG release')

            # Validate CKL content structure (basic check)
            if template.raw_ckl_content:
                try:
                    from ..services.ckl_parser import CKLParser
                    parser = CKLParser()
                    # Try to parse - if it fails, content is invalid
                    parser.parse_ckl(template.raw_ckl_content)
                except Exception as e:
                    errors.append(f'Invalid CKL content: {str(e)}')

            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': []  # Could add content quality warnings
            }

        except Exception as e:
            return {
                'valid': False,
                'errors': [f'Validation error: {str(e)}']
            }
