"""
Audit Log Repository

Repository for the AuditLog aggregate with specialized query methods
for compliance reporting and audit trail analysis.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from django.db.models import Q, Count, F
from django.utils import timezone

from core.domain.repository import BaseRepository
from ..aggregates.audit_log import AuditLog


class AuditLogRepository(BaseRepository[AuditLog]):
    """
    Repository for the AuditLog aggregate.

    Provides specialized methods for audit trail queries and reporting.
    """

    def __init__(self):
        super().__init__(AuditLog)

    def get_user_activity(self, user_id: str, days: int = 30) -> List[AuditLog]:
        """Get audit logs for a specific user within the last N days"""
        since_date = timezone.now() - timedelta(days=days)
        return list(self.model.objects.filter(
            user_id=user_id,
            created_at__gte=since_date
        ).order_by('-created_at'))

    def get_entity_history(self, entity_type: str, entity_id: str,
                          limit: int = 50) -> List[AuditLog]:
        """Get audit history for a specific entity"""
        return list(self.model.objects.filter(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by('-created_at')[:limit])

    def get_recent_activity(self, hours: int = 24, limit: int = 100) -> List[AuditLog]:
        """Get recent audit activity within the last N hours"""
        since_date = timezone.now() - timedelta(hours=hours)
        return list(self.model.objects.filter(
            created_at__gte=since_date
        ).order_by('-created_at')[:limit])

    def get_failed_operations(self, days: int = 7) -> List[AuditLog]:
        """Get failed operations within the last N days"""
        since_date = timezone.now() - timedelta(days=days)
        return list(self.model.objects.filter(
            success=False,
            created_at__gte=since_date
        ).order_by('-created_at'))

    def get_action_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get summary statistics of actions performed"""
        since_date = timezone.now() - timedelta(days=days)

        # Aggregate by action type
        actions = self.model.objects.filter(
            created_at__gte=since_date
        ).values('action_type').annotate(
            count=Count('id'),
            success_count=Count('id', filter=Q(success=True)),
            failure_count=Count('id', filter=Q(success=False))
        ).order_by('-count')

        # Aggregate by entity type
        entities = self.model.objects.filter(
            created_at__gte=since_date
        ).values('entity_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # Aggregate by user
        users = self.model.objects.filter(
            created_at__gte=since_date
        ).values('user_id', 'username').annotate(
            count=Count('id')
        ).order_by('-count')[:10]  # Top 10 active users

        return {
            'actions': list(actions),
            'entities': list(entities),
            'users': list(users),
            'total_logs': self.model.objects.filter(created_at__gte=since_date).count(),
            'period_days': days
        }

    def search_audit_logs(self, query: str, limit: int = 50) -> List[AuditLog]:
        """Search audit logs by entity name or other text fields"""
        return list(self.model.objects.filter(
            Q(entity_name__icontains=query) |
            Q(username__icontains=query) |
            Q(action_type__icontains=query) |
            Q(entity_type__icontains=query)
        ).order_by('-created_at')[:limit])

    def get_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance-focused audit report"""
        logs = self.model.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).order_by('created_at')

        # Group by date for timeline
        daily_activity = {}
        for log in logs:
            date_key = log.created_at.date().isoformat()
            if date_key not in daily_activity:
                daily_activity[date_key] = {
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'by_action': {},
                    'by_user': {}
                }

            daily_activity[date_key]['total'] += 1
            if log.success:
                daily_activity[date_key]['successful'] += 1
            else:
                daily_activity[date_key]['failed'] += 1

            # Count by action
            action_key = log.action_type
            if action_key not in daily_activity[date_key]['by_action']:
                daily_activity[date_key]['by_action'][action_key] = 0
            daily_activity[date_key]['by_action'][action_key] += 1

            # Count by user
            user_key = str(log.user_id)
            if user_key not in daily_activity[date_key]['by_user']:
                daily_activity[date_key]['by_user'][user_key] = {
                    'username': log.username,
                    'count': 0
                }
            daily_activity[date_key]['by_user'][user_key]['count'] += 1

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_logs': logs.count(),
                'successful_operations': logs.filter(success=True).count(),
                'failed_operations': logs.filter(success=False).count(),
                'unique_users': logs.values('user_id').distinct().count()
            },
            'daily_activity': daily_activity
        }
