"""
Framework Repository

Repository for Framework aggregate with comprehensive querying capabilities.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.db.models import Q, Count, Avg
from core.domain.repository import Repository

from ..models.framework import Framework


class FrameworkRepository(Repository):
    """Repository for Framework aggregates"""

    def __init__(self):
        super().__init__(Framework)

    def find_by_framework_id(self, framework_id: str) -> Optional[Framework]:
        """Find framework by framework ID"""
        try:
            return self.model.objects.get(framework_id=framework_id)
        except self.model.DoesNotExist:
            return None

    def find_by_type(self, framework_type: str) -> List[Framework]:
        """Find frameworks by type"""
        return list(self.model.objects.filter(framework_type=framework_type))

    def find_by_provider(self, provider: str) -> List[Framework]:
        """Find frameworks by provider"""
        return list(self.model.objects.filter(provider__icontains=provider))

    def find_published_frameworks(self) -> List[Framework]:
        """Find all published frameworks"""
        return list(self.model.objects.filter(status='published'))

    def find_current_frameworks(self) -> List[Framework]:
        """Find all current (non-deprecated) frameworks"""
        return list(self.model.objects.filter(status__in=['published', 'draft']))

    def find_frameworks_by_status(self, status: str) -> List[Framework]:
        """Find frameworks by status"""
        return list(self.model.objects.filter(status=status))

    def find_overdue_reviews(self) -> List[Framework]:
        """Find frameworks overdue for review"""
        from django.utils import timezone
        return list(self.model.objects.filter(
            review_date__lt=timezone.now().date(),
            status='published'
        ))

    def search_frameworks(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Framework]:
        """Search frameworks with optional filters"""
        queryset = self.model.objects.all()

        # Text search
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(framework_id__icontains=query) |
                Q(provider__icontains=query) |
                Q(tags__icontains=query)
            )

        # Apply filters
        if filters:
            if 'framework_type' in filters:
                queryset = queryset.filter(framework_type=filters['framework_type'])
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'provider' in filters:
                queryset = queryset.filter(provider__icontains=filters['provider'])

        return list(queryset)

    def get_framework_statistics(self) -> Dict[str, Any]:
        """Get comprehensive framework statistics"""
        stats = self.model.objects.aggregate(
            total_frameworks=Count('id'),
            published_frameworks=Count('id', filter=Q(status='published')),
            total_controls=Count('control_count'),
            average_controls_per_framework=Avg('control_count'),
            total_usage=Count('usage_count')
        )

        # Count by type
        type_counts = self.model.objects.values('framework_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # Count by status
        status_counts = self.model.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        # Count by provider
        provider_counts = self.model.objects.values('provider').annotate(
            count=Count('id')
        ).order_by('-count')

        # Most used frameworks
        top_frameworks = self.model.objects.filter(
            usage_count__gt=0
        ).order_by('-usage_count')[:10].values(
            'framework_id', 'name', 'usage_count', 'active_assessments'
        )

        stats.update({
            'type_breakdown': list(type_counts),
            'status_breakdown': list(status_counts),
            'provider_breakdown': list(provider_counts),
            'top_frameworks': list(top_frameworks)
        })

        return stats

    def get_framework_adoption_report(self) -> List[Dict[str, Any]]:
        """Get framework adoption report"""
        frameworks = self.model.objects.filter(
            status='published'
        ).order_by('-usage_count')

        return [{
            'framework_id': fw.framework_id,
            'name': fw.name,
            'type': fw.framework_type,
            'provider': fw.provider,
            'version': fw.version,
            'control_count': fw.control_count,
            'usage_count': fw.usage_count,
            'active_assessments': fw.active_assessments,
            'publication_date': fw.publication_date,
            'adoption_rate': fw.usage_count if fw.usage_count > 0 else 0
        } for fw in frameworks]

    def find_related_frameworks(self, framework_id: str) -> List[Framework]:
        """Find frameworks related to the given framework"""
        framework = self.find_by_framework_id(framework_id)
        if not framework:
            return []

        related_ids = (framework.related_framework_ids +
                      framework.superseding_framework_ids +
                      framework.superseded_by_framework_ids)

        if not related_ids:
            return []

        return list(self.model.objects.filter(framework_id__in=related_ids))

    def get_framework_mapping_network(self) -> Dict[str, Any]:
        """Get framework mapping network for visualization"""
        frameworks = self.model.objects.filter(status='published')

        nodes = []
        edges = []

        # Create nodes
        for fw in frameworks:
            nodes.append({
                'id': fw.framework_id,
                'label': fw.name,
                'type': fw.framework_type,
                'provider': fw.provider,
                'control_count': fw.control_count
            })

        # Create edges from mappings
        for fw in frameworks:
            for target_id, mappings in fw.control_mappings.items():
                if mappings:  # Only add edge if there are mappings
                    edges.append({
                        'source': fw.framework_id,
                        'target': target_id,
                        'mapping_count': len(mappings)
                    })

        return {
            'nodes': nodes,
            'edges': edges,
            'total_frameworks': len(nodes),
            'total_mappings': len(edges)
        }

    def bulk_update_status(self, framework_ids: List[str], new_status: str, user_id: uuid.UUID, username: str) -> int:
        """Bulk update framework status"""
        updated_count = self.model.objects.filter(framework_id__in=framework_ids).update(
            status=new_status,
            updated_by=user_id
        )

        # Log individual updates for audit trail
        frameworks = self.model.objects.filter(framework_id__in=framework_ids)
        for framework in frameworks:
            self.save(framework, user_id=user_id, username=username)

        return updated_count

    def get_framework_health_report(self) -> Dict[str, Any]:
        """Get framework health and maintenance report"""
        from django.utils import timezone

        total_frameworks = self.model.objects.count()
        published_frameworks = self.model.objects.filter(status='published').count()
        draft_frameworks = self.model.objects.filter(status='draft').count()
        deprecated_frameworks = self.model.objects.filter(status='deprecated').count()

        # Overdue reviews
        overdue_reviews = self.model.objects.filter(
            review_date__lt=timezone.now().date(),
            status='published'
        ).count()

        # Frameworks without review dates
        no_review_date = self.model.objects.filter(
            review_date__isnull=True,
            status='published'
        ).count()

        # Recently updated frameworks
        recently_updated = self.model.objects.filter(
            updated_at__gte=timezone.now() - timezone.timedelta(days=90)
        ).count()

        return {
            'total_frameworks': total_frameworks,
            'published_frameworks': published_frameworks,
            'draft_frameworks': draft_frameworks,
            'deprecated_frameworks': deprecated_frameworks,
            'overdue_reviews': overdue_reviews,
            'missing_review_dates': no_review_date,
            'recently_updated': recently_updated,
            'health_score': self._calculate_health_score(
                published_frameworks, overdue_reviews, no_review_date, total_frameworks
            )
        }

    def _calculate_health_score(self, published: int, overdue: int, missing_reviews: int, total: int) -> float:
        """Calculate framework health score (0-100)"""
        if total == 0:
            return 0.0

        # Base score from published frameworks
        base_score = (published / total) * 100

        # Penalty for overdue reviews
        overdue_penalty = (overdue / total) * 20

        # Penalty for missing review dates
        missing_penalty = (missing_reviews / total) * 10

        health_score = base_score - overdue_penalty - missing_penalty
        return max(0.0, min(100.0, health_score))

    def get_framework_compliance_matrix(self) -> Dict[str, Any]:
        """Get framework compliance matrix showing overlaps and gaps"""
        frameworks = self.model.objects.filter(status='published')

        matrix = {}
        all_controls = set()

        # Collect all unique controls across frameworks
        for fw in frameworks:
            # This would need to be implemented to get actual control lists
            # For now, return placeholder
            pass

        return {
            'frameworks': [fw.framework_id for fw in frameworks],
            'total_unique_controls': len(all_controls),
            'overlap_analysis': {},  # Would contain overlap statistics
            'gap_analysis': {}  # Would contain gap analysis
        }
