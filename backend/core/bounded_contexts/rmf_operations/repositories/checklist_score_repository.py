"""
ChecklistScore Repository

Repository for ChecklistScore aggregates.
"""

from typing import Optional, List, Dict
import uuid

from core.domain.repository import BaseRepository
from ..aggregates.checklist_score import ChecklistScore


class ChecklistScoreRepository(BaseRepository[ChecklistScore]):
    """
    Repository for ChecklistScore aggregates.

    Provides methods for querying and managing checklist scores.
    """

    def __init__(self):
        super().__init__(ChecklistScore)

    def find_by_checklist(self, checklist_id: uuid.UUID) -> Optional[ChecklistScore]:
        """Find score for a specific checklist"""
        try:
            return ChecklistScore.objects.get(checklistId=checklist_id)
        except ChecklistScore.DoesNotExist:
            return None

    def find_by_system_group(self, system_group_id: uuid.UUID) -> List[ChecklistScore]:
        """Find all scores for checklists in a system group"""
        return list(ChecklistScore.objects.filter(systemGroupId=system_group_id))

    def find_scores_with_open_findings(self, min_open_count: int = 1) -> List[ChecklistScore]:
        """Find scores with open findings above threshold"""
        return list(ChecklistScore.objects.filter(
            totalCat1Open__gte=min_open_count
        ) | ChecklistScore.objects.filter(
            totalCat2Open__gte=min_open_count
        ) | ChecklistScore.objects.filter(
            totalCat3Open__gte=min_open_count
        ))

    def find_scores_with_critical_findings(self) -> List[ChecklistScore]:
        """Find scores with critical (CAT I) open findings"""
        return list(ChecklistScore.objects.filter(totalCat1Open__gt=0))

    def get_system_level_score(self, system_group_id: uuid.UUID) -> Dict[str, int]:
        """Calculate aggregated score for a system group"""
        scores = self.find_by_system_group(system_group_id)

        total_checklists = len(scores)
        total_open = sum(score.totalOpen for score in scores)
        total_cat1_open = sum(score.totalCat1Open for score in scores)
        total_cat2_open = sum(score.totalCat2Open for score in scores)
        total_cat3_open = sum(score.totalCat3Open for score in scores)

        return {
            'total_checklists': total_checklists,
            'total_open': total_open,
            'total_cat1_open': total_cat1_open,
            'total_cat2_open': total_cat2_open,
            'total_cat3_open': total_cat3_open
        }

    def get_compliance_summary(self, system_group_id: Optional[uuid.UUID] = None) -> Dict[str, float]:
        """Get compliance summary for checklists or system"""
        if system_group_id:
            scores = self.find_by_system_group(system_group_id)
        else:
            scores = list(ChecklistScore.objects.all())

        total_checklists = len(scores)
        compliant_checklists = sum(1 for score in scores if score.is_compliant())
        total_compliance_percentage = sum(score.get_compliance_percentage() for score in scores) / max(total_checklists, 1)

        return {
            'total_checklists': total_checklists,
            'compliant_checklists': compliant_checklists,
            'compliance_percentage': round(total_compliance_percentage, 1),
            'non_compliant_checklists': total_checklists - compliant_checklists
        }

    def find_recently_calculated_scores(self, hours: int = 24) -> List[ChecklistScore]:
        """Find scores calculated within the last N hours"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_time = timezone.now() - timedelta(hours=hours)
        return list(ChecklistScore.objects.filter(lastCalculatedAt__gte=cutoff_time))

    def update_score_from_findings(self, checklist_id: uuid.UUID, findings_data: Dict) -> bool:
        """Update score from vulnerability findings data"""
        try:
            score = ChecklistScore.objects.get(checklistId=checklist_id)
            score.update_from_findings(findings_data)
            score.save()
            return True
        except ChecklistScore.DoesNotExist:
            return False

    def bulk_recalculate_scores(self, checklist_ids: List[uuid.UUID]) -> int:
        """Trigger recalculation for multiple checklists"""
        # In a real implementation, this would queue jobs to recalculate scores
        # For now, just return the count
        return len(checklist_ids)

    def get_scores_by_stig_type(self, stig_type: str) -> List[ChecklistScore]:
        """Get scores for checklists of a specific STIG type"""
        return list(ChecklistScore.objects.filter(stigType=stig_type))

    def get_top_non_compliant_scores(self, limit: int = 10) -> List[ChecklistScore]:
        """Get scores with lowest compliance percentages"""
        return list(ChecklistScore.objects.all().order_by(
            ChecklistScore.objects.annotate(
                compliance_pct=(ChecklistScore.totalNotAFinding + ChecklistScore.totalNotApplicable) /
                              ChecklistScore.totalVulnerabilities * 100
            ).values('compliance_pct')
        )[:limit])

    def get_score_trends(self, checklist_id: uuid.UUID, days: int = 30) -> List[Dict]:
        """Get score trends over time (would require historical data)"""
        # This would typically query historical score data
        # For now, return current score as a single data point
        score = self.find_by_checklist(checklist_id)
        if score:
            return [{
                'date': score.lastCalculatedAt.isoformat(),
                'total_open': score.totalOpen,
                'compliance_percentage': score.get_compliance_percentage()
            }]
        return []

    def search_scores(self, query: str) -> List[ChecklistScore]:
        """Search scores by hostname or STIG type"""
        return list(ChecklistScore.objects.filter(
            hostName__icontains=query
        ) | ChecklistScore.objects.filter(
            stigType__icontains=query
        ))

    def get_score_distribution(self) -> Dict[str, int]:
        """Get distribution of scores by compliance ranges"""
        scores = list(ChecklistScore.objects.all())

        ranges = {
            'excellent': 0,  # 90-100%
            'good': 0,       # 80-89%
            'fair': 0,       # 70-79%
            'poor': 0        # <70%
        }

        for score in scores:
            pct = score.get_compliance_percentage()
            if pct >= 90:
                ranges['excellent'] += 1
            elif pct >= 80:
                ranges['good'] += 1
            elif pct >= 70:
                ranges['fair'] += 1
            else:
                ranges['poor'] += 1

        return ranges
