"""
Service Repository

Repository for Service aggregate with comprehensive querying capabilities.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.db.models import Q, Count, Avg, Max, Min
from core.domain.repository import Repository

from ..models.service import Service


class ServiceRepository(Repository):
    """Repository for Service aggregates"""

    def __init__(self):
        super().__init__(Service)

    def find_by_service_id(self, service_id: str) -> Optional[Service]:
        """Find service by service ID"""
        try:
            return self.model.objects.get(service_id=service_id)
        except self.model.DoesNotExist:
            return None

    def find_by_owner(self, owner_user_id: uuid.UUID) -> List[Service]:
        """Find services by owner"""
        return list(self.model.objects.filter(owner_user_id=owner_user_id))

    def find_by_type(self, service_type: str) -> List[Service]:
        """Find services by type"""
        return list(self.model.objects.filter(service_type=service_type))

    def find_by_status(self, status: str) -> List[Service]:
        """Find services by status"""
        return list(self.model.objects.filter(status=status))

    def find_by_criticality(self, criticality_level: str) -> List[Service]:
        """Find services by criticality level"""
        return list(self.model.objects.filter(criticality_level=criticality_level))

    def find_critical_services(self) -> List[Service]:
        """Find all critical services"""
        return list(self.model.objects.filter(
            criticality_level__in=['high', 'very_high', 'critical']
        ))

    def find_services_with_incidents(self) -> List[Service]:
        """Find services with open incidents"""
        return list(self.model.objects.filter(open_incident_count__gt=0))

    def find_overdue_reviews(self) -> List[Service]:
        """Find services overdue for review"""
        from django.utils import timezone
        return list(self.model.objects.filter(
            next_review_date__lt=timezone.now().date(),
            status='active'
        ))

    def find_end_of_life_services(self) -> List[Service]:
        """Find services at end of life"""
        from django.utils import timezone
        return list(self.model.objects.filter(
            end_of_life_date__lt=timezone.now().date(),
            status__in=['active', 'maintenance']
        ))

    def find_dependent_services(self, service_id: str) -> List[Service]:
        """Find services that depend on the given service"""
        service = self.find_by_service_id(service_id)
        if not service:
            return []

        if not service.dependent_service_ids:
            return []

        return list(self.model.objects.filter(service_id__in=service.dependent_service_ids))

    def find_supporting_services(self, service_id: str) -> List[Service]:
        """Find services that support the given service"""
        service = self.find_by_service_id(service_id)
        if not service:
            return []

        if not service.supporting_service_ids:
            return []

        return list(self.model.objects.filter(service_id__in=service.supporting_service_ids))

    def search_services(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Service]:
        """Search services with optional filters"""
        queryset = self.model.objects.all()

        # Text search
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(service_id__icontains=query) |
                Q(category__icontains=query) |
                Q(tags__icontains=query)
            )

        # Apply filters
        if filters:
            if 'service_type' in filters:
                queryset = queryset.filter(service_type=filters['service_type'])
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'criticality_level' in filters:
                queryset = queryset.filter(criticality_level=filters['criticality_level'])
            if 'owner_user_id' in filters:
                queryset = queryset.filter(owner_user_id=filters['owner_user_id'])
            if 'portfolio' in filters:
                queryset = queryset.filter(portfolio=filters['portfolio'])

        return list(queryset)

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get comprehensive service statistics"""
        stats = self.model.objects.aggregate(
            total_services=Count('id'),
            active_services=Count('id', filter=Q(status='active')),
            critical_services=Count('id', filter=Q(criticality_level__in=['high', 'very_high', 'critical'])),
            services_with_incidents=Count('id', filter=Q(open_incident_count__gt=0)),
            average_availability=Avg('availability_percentage'),
            average_response_time=Avg('average_response_time'),
            total_incidents=Count('incident_count')
        )

        # Count by type
        type_counts = self.model.objects.values('service_type').annotate(
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

        # SLA compliance
        sla_compliant = self.model.objects.filter(
            availability_percentage__gte=models.F('sla_availability_target')
        ).count()

        total_with_sla = self.model.objects.filter(
            sla_availability_target__isnull=False
        ).count()

        sla_compliance_rate = (sla_compliant / total_with_sla * 100) if total_with_sla > 0 else 0

        stats.update({
            'type_breakdown': list(type_counts),
            'status_breakdown': list(status_counts),
            'criticality_breakdown': list(criticality_counts),
            'sla_compliance_rate': round(sla_compliance_rate, 2),
            'services_meeting_sla': sla_compliant,
            'services_with_sla_targets': total_with_sla
        })

        return stats

    def get_service_catalog(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get service catalog with optional filters"""
        queryset = self.model.objects.all()

        if filters:
            if 'service_type' in filters:
                queryset = queryset.filter(service_type=filters['service_type'])
            if 'status' in filters:
                queryset = queryset.filter(status=filters['status'])
            if 'portfolio' in filters:
                queryset = queryset.filter(portfolio=filters['portfolio'])

        services = queryset.order_by('service_type', 'category', 'name')

        return [{
            'service_id': service.service_id,
            'name': service.name,
            'type': service.service_type,
            'category': service.category,
            'status': service.status,
            'criticality_level': service.criticality_level,
            'owner_username': service.owner_username,
            'description': service.description,
            'availability_percentage': service.availability_percentage,
            'sla_availability_target': service.sla_availability_target,
            'open_incidents': service.open_incident_count
        } for service in services]

    def get_service_health_dashboard(self) -> Dict[str, Any]:
        """Get service health dashboard data"""
        # Overall health metrics
        health_metrics = {
            'total_services': self.model.objects.count(),
            'healthy_services': self.model.objects.filter(
                availability_percentage__gte=99.5,
                open_incident_count=0
            ).count(),
            'degraded_services': self.model.objects.filter(
                Q(availability_percentage__lt=99.5, availability_percentage__gte=95) |
                Q(open_incident_count__gt=0)
            ).count(),
            'unhealthy_services': self.model.objects.filter(
                Q(availability_percentage__lt=95) |
                Q(open_incident_count__gt=2)
            ).count()
        }

        # Services by health status
        health_status = {
            'healthy': health_metrics['healthy_services'],
            'degraded': health_metrics['degraded_services'],
            'unhealthy': health_metrics['unhealthy_services']
        }

        # Top services by incidents
        top_incident_services = self.model.objects.filter(
            incident_count__gt=0
        ).order_by('-incident_count')[:10].values(
            'service_id', 'name', 'incident_count', 'open_incident_count'
        )

        # Services missing SLA targets
        services_missing_sla = self.model.objects.filter(
            status='active',
            sla_availability_target__isnull=True
        ).count()

        # Upcoming service reviews
        from django.utils import timezone
        from datetime import timedelta
        upcoming_reviews = self.model.objects.filter(
            next_review_date__lte=timezone.now().date() + timedelta(days=30),
            next_review_date__gte=timezone.now().date()
        ).count()

        return {
            'health_metrics': health_metrics,
            'health_status_breakdown': health_status,
            'top_incident_services': list(top_incident_services),
            'services_missing_sla': services_missing_sla,
            'upcoming_reviews': upcoming_reviews,
            'overall_health_percentage': round(
                (health_metrics['healthy_services'] / health_metrics['total_services'] * 100)
                if health_metrics['total_services'] > 0 else 0, 2
            )
        }

    def get_service_dependency_map(self, service_id: str) -> Dict[str, Any]:
        """Get dependency map for a service"""
        service = self.find_by_service_id(service_id)
        if not service:
            return {'error': 'Service not found'}

        # Get dependent services
        dependent_services = []
        for dep_id in service.dependent_service_ids:
            dep_service = self.find_by_service_id(dep_id)
            if dep_service:
                dependent_services.append({
                    'service_id': dep_service.service_id,
                    'name': dep_service.name,
                    'type': dep_service.service_type,
                    'status': dep_service.status,
                    'criticality': dep_service.criticality_level
                })

        # Get supporting services
        supporting_services = []
        for sup_id in service.supporting_service_ids:
            sup_service = self.find_by_service_id(sup_id)
            if sup_service:
                supporting_services.append({
                    'service_id': sup_service.service_id,
                    'name': sup_service.name,
                    'type': sup_service.service_type,
                    'status': sup_service.status,
                    'criticality': sup_service.criticality_level
                })

        return {
            'service': {
                'service_id': service.service_id,
                'name': service.name,
                'type': service.service_type,
                'status': service.status
            },
            'dependent_services': dependent_services,
            'supporting_services': supporting_services,
            'total_dependencies': len(dependent_services),
            'total_supporting': len(supporting_services)
        }

    def get_service_performance_report(self, service_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get service performance report"""
        queryset = self.model.objects.all()

        if service_ids:
            queryset = queryset.filter(service_id__in=service_ids)

        services = queryset.filter(status='active')

        return [{
            'service_id': service.service_id,
            'name': service.name,
            'availability_percentage': service.availability_percentage,
            'sla_target': service.sla_availability_target,
            'sla_compliant': service.availability_percentage >= (service.sla_availability_target or 0),
            'average_response_time': service.average_response_time,
            'error_rate_percentage': service.error_rate_percentage,
            'throughput_requests_per_minute': service.throughput_requests_per_minute,
            'open_incidents': service.open_incident_count,
            'customer_satisfaction_score': service.customer_satisfaction_score
        } for service in services]

    def bulk_update_status(self, service_ids: List[str], new_status: str, user_id: uuid.UUID, username: str) -> int:
        """Bulk update service status"""
        updated_count = self.model.objects.filter(service_id__in=service_ids).update(
            status=new_status,
            updated_by=user_id
        )

        # Log individual updates for audit trail
        services = self.model.objects.filter(service_id__in=service_ids)
        for service in services:
            self.save(service, user_id=user_id, username=username)

        return updated_count

    def bulk_update_metrics(self, service_metrics: Dict[str, Dict[str, Any]], user_id: uuid.UUID, username: str) -> int:
        """Bulk update service metrics"""
        updated_count = 0

        for service_id, metrics in service_metrics.items():
            service = self.find_by_service_id(service_id)
            if service:
                service.update_metrics(metrics)
                self.save(service, user_id=user_id, username=username)
                updated_count += 1

        return updated_count
