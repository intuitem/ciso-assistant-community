"""
Nessus Scan Repository

Repository for NessusScan aggregates with specialized methods
for vulnerability scan management and correlation.
"""

from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timedelta

from core.domain.repository import BaseRepository
from ..aggregates.nessus_scan import NessusScan
from ..services.nessus_parser import NessusParser


class NessusScanRepository(BaseRepository[NessusScan]):
    """
    Repository for NessusScan aggregates.

    Provides methods for managing Nessus vulnerability scans
    and their correlation with STIG checklists.
    """

    def __init__(self):
        super().__init__(NessusScan)
        self.parser = NessusParser()

    def find_by_system_group(self, system_group_id: uuid.UUID) -> List[NessusScan]:
        """Find all scans for a system group"""
        return list(NessusScan.objects.filter(systemGroupId=system_group_id))

    def find_recent_scans(self, days: int = 30) -> List[NessusScan]:
        """Find scans from the last N days"""
        from django.utils import timezone
        cutoff_date = timezone.now() - timedelta(days=days)
        return list(NessusScan.objects.filter(created_at__gte=cutoff_date))

    def find_scans_by_status(self, status: str) -> List[NessusScan]:
        """Find scans by processing status"""
        return list(NessusScan.objects.filter(processing_status=status))

    def find_failed_scans(self) -> List[NessusScan]:
        """Find scans that failed processing"""
        return list(NessusScan.objects.filter(processing_status='failed'))

    def get_scan_statistics(self, system_group_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Get comprehensive scan statistics"""
        queryset = NessusScan.objects.all()
        if system_group_id:
            queryset = queryset.filter(systemGroupId=system_group_id)

        total_scans = queryset.count()
        completed_scans = queryset.filter(processing_status='completed').count()
        total_vulnerabilities = queryset.aggregate(
            total=models.Sum('total_vulnerabilities')
        )['total'] or 0

        # Severity breakdown
        severity_stats = queryset.aggregate(
            critical=models.Sum('critical_count'),
            high=models.Sum('high_count'),
            medium=models.Sum('medium_count'),
            low=models.Sum('low_count'),
            info=models.Sum('info_count')
        )

        return {
            'total_scans': total_scans,
            'completed_scans': completed_scans,
            'completion_rate': completed_scans / max(total_scans, 1),
            'total_vulnerabilities': total_vulnerabilities,
            'severity_breakdown': severity_stats,
            'scans_by_status': self._get_status_distribution(queryset)
        }

    def _get_status_distribution(self, queryset) -> Dict[str, int]:
        """Get scan count by processing status"""
        from django.db.models import Count
        status_counts = queryset.values('processing_status').annotate(
            count=Count('id')
        ).order_by('processing_status')

        return {item['processing_status']: item['count'] for item in status_counts}

    def process_scan_file(self, scan_id: uuid.UUID) -> bool:
        """Process a newly uploaded scan file"""
        try:
            scan = self.get_by_id(scan_id)
            if not scan or scan.processing_status != 'uploaded':
                return False

            # Mark as processing
            scan.mark_processing_started()
            self.save(scan)

            # Parse the XML content
            try:
                parsed_data = self.parser.parse_nessus_file(scan.raw_xml_content)
                summary = self.parser.extract_scan_summary(parsed_data)

                # Update scan with parsed metadata
                scan.mark_processing_completed(summary)
                self.save(scan)

                return True

            except Exception as e:
                scan.mark_processing_failed(str(e))
                self.save(scan)
                return False

        except Exception as e:
            # Log error but don't expose internal details
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing scan {scan_id}: {e}")
            return False

    def get_scans_for_correlation(self, system_group_id: uuid.UUID) -> List[NessusScan]:
        """Get scans suitable for correlation with checklists"""
        return list(NessusScan.objects.filter(
            systemGroupId=system_group_id,
            processing_status='completed'
        ).order_by('-scan_date'))

    def get_correlated_scans(self, checklist_id: uuid.UUID) -> List[NessusScan]:
        """Get scans that are correlated with a specific checklist"""
        # This requires a more complex query to check the correlated_checklist_ids array
        # For now, return all scans for the system (can be enhanced)
        checklist_scans = NessusScan.objects.filter(
            correlated_checklist_ids__contains=[str(checklist_id)]
        )
        return list(checklist_scans)

    def search_scans(self, query: str, system_group_id: Optional[uuid.UUID] = None) -> List[NessusScan]:
        """Search scans by filename or policy name"""
        queryset = NessusScan.objects.filter(
            filename__icontains=query
        ) | NessusScan.objects.filter(
            policy_name__icontains=query
        )

        if system_group_id:
            queryset = queryset.filter(systemGroupId=system_group_id)

        return list(queryset.distinct())

    def get_scan_vulnerability_trends(self, system_group_id: uuid.UUID,
                                     days: int = 90) -> Dict[str, Any]:
        """Get vulnerability trends over time for a system group"""
        from django.utils import timezone
        from django.db.models import Sum

        cutoff_date = timezone.now() - timedelta(days=days)

        # Group by date and sum vulnerabilities
        trends = NessusScan.objects.filter(
            systemGroupId=system_group_id,
            processing_status='completed',
            scan_date__gte=cutoff_date
        ).extra(
            select={'date': 'DATE(scan_date)'}
        ).values('date').annotate(
            total_vulns=Sum('total_vulnerabilities'),
            critical=Sum('critical_count'),
            high=Sum('high_count'),
            medium=Sum('medium_count'),
            low=Sum('low_count')
        ).order_by('date')

        return {
            'period_days': days,
            'system_group_id': str(system_group_id),
            'trends': list(trends)
        }

    def cleanup_old_scans(self, days_to_keep: int = 365) -> int:
        """Clean up old scan files (mark for archiving)"""
        from django.utils import timezone

        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        old_scans = NessusScan.objects.filter(
            created_at__lt=cutoff_date,
            processing_status='completed'
        )

        # Mark old scans as archived (could add an archived status)
        # For now, just return count
        return old_scans.count()

    def validate_scan_data(self, scan_id: uuid.UUID) -> Dict[str, Any]:
        """Validate scan data integrity"""
        try:
            scan = self.get_by_id(scan_id)
            if not scan:
                return {'valid': False, 'errors': ['Scan not found']}

            errors = []

            # Check required fields
            if not scan.raw_xml_content:
                errors.append('Missing raw XML content')

            if scan.processing_status == 'completed':
                if scan.total_hosts == 0:
                    errors.append('Completed scan has no hosts')
                if scan.total_vulnerabilities < 0:
                    errors.append('Invalid vulnerability count')

            # Validate XML structure if content exists
            if scan.raw_xml_content:
                try:
                    self.parser.parse_nessus_file(scan.raw_xml_content)
                except Exception as e:
                    errors.append(f'XML parsing error: {str(e)}')

            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': []  # Could add warnings for data quality issues
            }

        except Exception as e:
            return {
                'valid': False,
                'errors': [f'Validation error: {str(e)}']
            }
