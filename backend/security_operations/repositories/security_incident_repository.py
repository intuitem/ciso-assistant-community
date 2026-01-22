"""
Security Incident Repository

Repository for managing SecurityIncident aggregates with support for
incident response workflows and security metrics.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.utils import timezone

from core.domain.repository import Repository
from ..models.security_incident import SecurityIncident


class SecurityIncidentRepository(Repository[SecurityIncident]):
    """
    Repository for SecurityIncident aggregates.

    Provides methods for querying incidents by status, severity,
    response metrics, and security analytics.
    """

    def __init__(self):
        super().__init__(SecurityIncident)

    def find_by_status(self, status: str) -> List[SecurityIncident]:
        """Find incidents by status"""
        return list(self.model.objects.filter(status=status).order_by('-detection_date'))

    def find_by_severity(self, severity: str) -> List[SecurityIncident]:
        """Find incidents by severity"""
        return list(self.model.objects.filter(severity=severity).order_by('-detection_date'))

    def find_active_incidents(self) -> List[SecurityIncident]:
        """Find active (non-closed) incidents"""
        return list(self.model.objects.exclude(
            status__in=['resolved', 'closed', 'false_positive']
        ).order_by('-detection_date'))

    def find_overdue_incidents(self) -> List[SecurityIncident]:
        """Find incidents that may be overdue for response"""
        # Simplified overdue check - could be enhanced with SLA logic
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        return list(self.model.objects.filter(
            detection_date__lt=seven_days_ago,
            status__in=['detected', 'investigating']
        ).order_by('detection_date'))

    def find_by_category(self, category: str) -> List[SecurityIncident]:
        """Find incidents by category"""
        return list(self.model.objects.filter(category=category).order_by('-detection_date'))

    def find_assigned_to_user(self, user_id: uuid.UUID) -> List[SecurityIncident]:
        """Find incidents assigned to a specific user"""
        return list(self.model.objects.filter(
            assigned_analyst_user_id=user_id
        ).order_by('-detection_date'))

    def get_incident_statistics(self) -> Dict[str, Any]:
        """Get comprehensive incident statistics"""
        incidents = list(self.model.objects.all())

        stats = {
            'total_incidents': len(incidents),
            'active_incidents': len([i for i in incidents if i.is_active]),
            'resolved_incidents': len([i for i in incidents if i.status == 'resolved']),
            'closed_incidents': len([i for i in incidents if i.status == 'closed']),
            'severity_distribution': {},
            'category_distribution': {},
            'status_distribution': {},
            'average_resolution_time_hours': 0,
            'resolution_sla_compliance': 0.0,
            'generated_at': str(timezone.now())
        }

        # Calculate distributions
        for incident in incidents:
            stats['severity_distribution'][incident.severity] = \
                stats['severity_distribution'].get(incident.severity, 0) + 1
            stats['category_distribution'][incident.category] = \
                stats['category_distribution'].get(incident.category, 0) + 1
            stats['status_distribution'][incident.status] = \
                stats['status_distribution'].get(incident.status, 0) + 1

        # Calculate resolution metrics
        resolved_incidents = [i for i in incidents if i.status in ['resolved', 'closed'] and i.total_response_time_hours]
        if resolved_incidents:
            total_hours = sum(i.total_response_time_hours for i in resolved_incidents)
            stats['average_resolution_time_hours'] = round(total_hours / len(resolved_incidents), 1)

            sla_compliant = len([i for i in resolved_incidents if i.response_time_sla_met])
            stats['resolution_sla_compliance'] = round((sla_compliant / len(resolved_incidents)) * 100, 1)

        return stats

    def get_security_incident_trends(self, months: int = 12) -> Dict[str, Any]:
        """Get incident trends over time"""
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=months * 30)

        incidents = list(self.model.objects.filter(
            detection_date__gte=start_date,
            detection_date__lte=end_date
        ).order_by('detection_date'))

        # Group by month
        monthly_stats = {}
        for incident in incidents:
            month_key = incident.detection_date.strftime('%Y-%m')
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {
                    'total': 0,
                    'by_severity': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0},
                    'by_category': {}
                }

            monthly_stats[month_key]['total'] += 1
            monthly_stats[month_key]['by_severity'][incident.severity] += 1
            monthly_stats[month_key]['by_category'][incident.category] = \
                monthly_stats[month_key]['by_category'].get(incident.category, 0) + 1

        return {
            'period_months': months,
            'monthly_stats': monthly_stats,
            'generated_at': str(timezone.now())
        }
