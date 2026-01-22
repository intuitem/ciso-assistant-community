"""
Asset Repository

Repository for Asset aggregate with comprehensive querying capabilities.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.db.models import Q, Count, Avg, Max, Min
from core.domain.repository import Repository

from ..models.asset import Asset


class AssetRepository(Repository):
    """Repository for Asset aggregates"""

    def __init__(self):
        super().__init__(Asset)

    def find_by_asset_id(self, asset_id: str) -> Optional[Asset]:
        """Find asset by asset ID"""
        try:
            return self.model.objects.get(asset_id=asset_id)
        except self.model.DoesNotExist:
            return None

    def find_by_owner(self, owner_user_id: uuid.UUID) -> List[Asset]:
        """Find assets by owner"""
        return list(self.model.objects.filter(owner_user_id=owner_user_id))

    def find_by_type(self, asset_type: str) -> List[Asset]:
        """Find assets by type"""
        return list(self.model.objects.filter(asset_type=asset_type))

    def find_by_status(self, status: str) -> List[Asset]:
        """Find assets by status"""
        return list(self.model.objects.filter(status=status))

    def find_by_criticality(self, criticality_level: str) -> List[Asset]:
        """Find assets by criticality level"""
        return list(self.model.objects.filter(criticality_level=criticality_level))

    def find_critical_assets(self) -> List[Asset]:
        """Find all critical assets"""
        return list(self.model.objects.filter(
            criticality_level__in=['high', 'very_high', 'critical']
        ))

    def find_overdue_maintenance(self) -> List[Asset]:
        """Find assets overdue for maintenance"""
        from django.utils import timezone
        return list(self.model.objects.filter(
            next_maintenance_date__lt=timezone.now().date(),
            status='active'
        ))

    def find_end_of_life_assets(self) -> List[Asset]:
        """Find assets at end of life"""
        from django.utils import timezone
        return list(self.model.objects.filter(
            end_of_life_date__lt=timezone.now().date(),
            status__in=['active', 'maintenance']
        ))

    def find_by_location(self, location: str) -> List[Asset]:
        """Find assets by location"""
        return list(self.model.objects.filter(location__icontains=location))

    def find_related_assets(self, asset_id: str) -> List[Asset]:
        """Find assets related to the given asset"""
        asset = self.find_by_asset_id(asset_id)
        if not asset:
            return []

        related_ids = asset.related_asset_ids + asset.parent_asset_ids + asset.child_asset_ids
        if not related_ids:
            return []

        return list(self.model.objects.filter(asset_id__in=related_ids))

    def find_assets_by_service_dependency(self, service_id: str) -> List[Asset]:
        """Find assets that depend on or support a service"""
        return list(self.model.objects.filter(
            models.Q(dependent_service_ids__contains=[service_id]) |
            models.Q(supporting_service_ids__contains=[service_id])
        ))

    def search_assets(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Asset]:
        """Search assets with optional filters"""
        queryset = self.model.objects.all()

        # Text search
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(asset_id__icontains=query) |
                Q(category__icontains=query) |
                Q(tags__icontains=query)
            )

        # Apply filters
        if filters:
            if 'asset_type' in filters:
                queryset = queryset.filter(asset_type=filters['asset_type'])
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'criticality_level' in filters:
                queryset = queryset.filter(criticality_level=filters['criticality_level'])
            if 'sensitivity_level' in filters:
                queryset = queryset.filter(sensitivity_level=filters['sensitivity_level'])
            if 'owner_user_id' in filters:
                queryset = queryset.filter(owner_user_id=filters['owner_user_id'])
            if 'location' in filters:
                queryset = queryset.filter(location__icontains=filters['location'])

        return list(queryset)

    def get_asset_statistics(self) -> Dict[str, Any]:
        """Get comprehensive asset statistics"""
        stats = self.model.objects.aggregate(
            total_assets=Count('id'),
            active_assets=Count('id', filter=Q(status='active')),
            critical_assets=Count('id', filter=Q(criticality_level__in=['high', 'very_high', 'critical'])),
            high_risk_assets=Count('id', filter=Q(risk_score__gte=70)),
            average_risk_score=Avg('risk_score'),
            max_risk_score=Max('risk_score'),
            min_risk_score=Min('risk_score')
        )

        # Count by type
        type_counts = self.model.objects.values('asset_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # Count by status
        status_counts = self.model.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count')

        # Count by criticality
        criticality_counts = self.model.objects.values('criticality_level').annotate(
            count=Count('id')
        ).order_by('-count')

        stats.update({
            'type_breakdown': list(type_counts),
            'status_breakdown': list(status_counts),
            'criticality_breakdown': list(criticality_counts)
        })

        return stats

    def get_maintenance_schedule(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get upcoming maintenance schedule"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now().date() + timedelta(days=days_ahead)

        assets = self.model.objects.filter(
            next_maintenance_date__lte=cutoff_date,
            next_maintenance_date__gte=timezone.now().date(),
            status='active'
        ).order_by('next_maintenance_date')

        return [{
            'asset_id': asset.asset_id,
            'name': asset.name,
            'maintenance_date': asset.next_maintenance_date,
            'owner_username': asset.owner_username,
            'criticality_level': asset.criticality_level
        } for asset in assets]

    def get_asset_inventory_report(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate asset inventory report"""
        queryset = self.model.objects.all()

        if filters:
            if 'asset_type' in filters:
                queryset = queryset.filter(asset_type=filters['asset_type'])
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'owner_user_id' in filters:
                queryset = queryset.filter(owner_user_id=filters['owner_user_id'])
            if 'location' in filters:
                queryset = queryset.filter(location__icontains=filters['location'])

        assets = queryset.order_by('asset_type', 'category', 'name')

        return [{
            'asset_id': asset.asset_id,
            'name': asset.name,
            'type': asset.asset_type,
            'category': asset.category,
            'status': asset.status,
            'criticality_level': asset.criticality_level,
            'owner_username': asset.owner_username,
            'location': asset.location,
            'acquisition_date': asset.acquisition_date,
            'current_value': asset.current_value,
            'risk_score': asset.risk_score
        } for asset in assets]

    def get_asset_risk_summary(self) -> Dict[str, Any]:
        """Get asset risk summary"""
        # Risk score distribution
        risk_ranges = [
            (0, 20, 'Very Low'),
            (21, 40, 'Low'),
            (41, 60, 'Moderate'),
            (61, 80, 'High'),
            (81, 100, 'Critical')
        ]

        risk_distribution = {}
        for min_score, max_score, label in risk_ranges:
            count = self.model.objects.filter(
                risk_score__gte=min_score,
                risk_score__lte=max_score
            ).count()
            risk_distribution[label] = count

        # Assets by criticality
        criticality_summary = dict(
            self.model.objects.values('criticality_level').annotate(
                count=Count('id'),
                avg_risk=Avg('risk_score'),
                max_risk=Max('risk_score')
            ).values_list('criticality_level', 'count', 'avg_risk', 'max_risk')
        )

        return {
            'risk_distribution': risk_distribution,
            'criticality_summary': criticality_summary,
            'total_high_risk_assets': self.model.objects.filter(risk_score__gte=70).count(),
            'total_critical_assets': self.model.objects.filter(criticality_level='critical').count()
        }

    def bulk_update_status(self, asset_ids: List[str], new_status: str, user_id: uuid.UUID, username: str) -> int:
        """Bulk update asset status"""
        updated_count = self.model.objects.filter(asset_id__in=asset_ids).update(
            status=new_status,
            updated_by=user_id
        )

        # Log individual updates for audit trail
        assets = self.model.objects.filter(asset_id__in=asset_ids)
        for asset in assets:
            self.save(asset, user_id=user_id, username=username)

        return updated_count

    def bulk_update_criticality(self, asset_ids: List[str], criticality_level: str, user_id: uuid.UUID, username: str) -> int:
        """Bulk update asset criticality"""
        updated_count = self.model.objects.filter(asset_id__in=asset_ids).update(
            criticality_level=criticality_level,
            updated_by=user_id
        )

        # Log individual updates for audit trail
        assets = self.model.objects.filter(asset_id__in=asset_ids)
        for asset in assets:
            self.save(asset, user_id=user_id, username=username)

        return updated_count
