"""
Asset Risk Repository

Repository for managing AssetRisk aggregates with audit logging and
query optimization for risk management operations.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.utils import timezone

from core.domain.repository import Repository
from ..models.asset_risk import AssetRisk


class AssetRiskRepository(Repository[AssetRisk]):
    """
    Repository for AssetRisk aggregates.

    Provides methods for querying, saving, and managing asset risks
    with support for audit logging and risk management workflows.
    """

    def __init__(self):
        super().__init__(AssetRisk)

    def find_by_asset(self, asset_id: uuid.UUID) -> List[AssetRisk]:
        """Find all risks for a specific asset"""
        return list(self.model.objects.filter(asset_id=asset_id))

    def find_by_risk_level(self, risk_level: str, asset_ids: Optional[List[uuid.UUID]] = None) -> List[AssetRisk]:
        """Find risks by residual risk level"""
        query = self.model.objects.filter(residual_risk_level=risk_level)
        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)
        return list(query)

    def find_requiring_treatment(self, asset_ids: Optional[List[uuid.UUID]] = None) -> List[AssetRisk]:
        """Find risks that require treatment"""
        query = self.model.objects.filter(requires_treatment=True)
        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)
        return list(query.order_by('-residual_risk_score'))

    def find_overdue_for_review(self, asset_ids: Optional[List[uuid.UUID]] = None) -> List[AssetRisk]:
        """Find risks overdue for review"""
        today = timezone.now().date()
        query = self.model.objects.filter(
            next_review_date__isnull=False,
            next_review_date__lt=today
        )
        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)
        return list(query)

    def find_by_category(self, category: str, asset_ids: Optional[List[uuid.UUID]] = None) -> List[AssetRisk]:
        """Find risks by category"""
        query = self.model.objects.filter(risk_category=category)
        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)
        return list(query.order_by('-residual_risk_score'))

    def find_by_owner(self, owner_user_id: uuid.UUID) -> List[AssetRisk]:
        """Find risks owned by a specific user"""
        return list(self.model.objects.filter(risk_owner_user_id=owner_user_id))

    def find_by_treatment_owner(self, treatment_owner_user_id: uuid.UUID) -> List[AssetRisk]:
        """Find risks where treatment is owned by a specific user"""
        return list(self.model.objects.filter(treatment_owner_user_id=treatment_owner_user_id))

    def find_by_treatment_status(self, status: str, asset_ids: Optional[List[uuid.UUID]] = None) -> List[AssetRisk]:
        """Find risks by treatment status"""
        query = self.model.objects.filter(treatment_status=status)
        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)
        return list(query.order_by('-residual_risk_score'))

    def get_risk_statistics_for_asset(self, asset_id: uuid.UUID) -> Dict[str, Any]:
        """Get risk statistics for a specific asset"""
        risks = self.find_by_asset(asset_id)

        stats = {
            'total_risks': len(risks),
            'critical_risks': len([r for r in risks if r.residual_risk_level == 'critical']),
            'high_risks': len([r for r in risks if r.residual_risk_level == 'high']),
            'moderate_risks': len([r for r in risks if r.residual_risk_level == 'moderate']),
            'low_risks': len([r for r in risks if r.residual_risk_level == 'low']),
            'requiring_treatment': len([r for r in risks if r.requires_treatment]),
            'under_treatment': len([r for r in risks if r.treatment_status in ['in_progress', 'implemented']]),
            'effectively_treated': len([r for r in risks if r.treatment_status == 'effective']),
            'overdue_reviews': len([r for r in risks if r.is_overdue_for_review]),
            'highest_risk_score': max([r.residual_risk_score for r in risks]) if risks else 0,
            'average_risk_score': round(sum([r.residual_risk_score for r in risks]) / len(risks), 2) if risks else 0,
        }

        return stats

    def get_risk_heat_map_data(self, asset_ids: Optional[List[uuid.UUID]] = None) -> Dict[str, Any]:
        """Generate risk heat map data (5x5 likelihood vs impact matrix)"""
        query = self.model.objects.all()
        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)

        risks = list(query)

        # Initialize 5x5 matrix (likelihood 1-5 vs impact 1-5)
        matrix = [[0 for _ in range(5)] for _ in range(5)]

        for risk in risks:
            likelihood_idx = risk.residual_likelihood - 1  # 0-based index
            impact_idx = risk.residual_impact - 1         # 0-based index

            if 0 <= likelihood_idx < 5 and 0 <= impact_idx < 5:
                matrix[likelihood_idx][impact_idx] += 1

        return {
            'matrix': matrix,
            'labels': {
                'likelihood': ['Very Low (1)', 'Low (2)', 'Moderate (3)', 'High (4)', 'Very High (5)'],
                'impact': ['Very Low (1)', 'Low (2)', 'Moderate (3)', 'High (4)', 'Very High (5)']
            },
            'total_risks': len(risks),
            'generated_at': str(timezone.now())
        }

    def get_top_risks(self, limit: int = 10, asset_ids: Optional[List[uuid.UUID]] = None) -> List[AssetRisk]:
        """Get top risks by residual risk score"""
        query = self.model.objects.all()
        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)

        return list(query.order_by('-residual_risk_score')[:limit])

    def get_risks_requiring_attention(self, asset_ids: Optional[List[uuid.UUID]] = None) -> List[AssetRisk]:
        """Get risks requiring immediate attention"""
        query = self.model.objects.filter(
            residual_risk_level__in=['high', 'critical'],
            requires_treatment=True
        ).exclude(treatment_status='effective')

        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)

        return list(query.order_by('-residual_risk_score'))

    def bulk_update_treatment_status(self, risk_ids: List[str], new_status: str,
                                   treatment_details: Optional[Dict[str, Any]] = None) -> int:
        """Bulk update treatment status for multiple risks"""
        risks = self.model.objects.filter(id__in=risk_ids)
        updated_count = 0

        for risk in risks:
            old_status = risk.treatment_status
            risk.treatment_status = new_status

            if treatment_details:
                if 'implementation_date' in treatment_details and new_status == 'implemented':
                    risk.treatment_implemented_date = treatment_details['implementation_date']
                if 'effective_date' in treatment_details and new_status == 'effective':
                    risk.treatment_effective_date = treatment_details['effective_date']

            # Update residual risk if treatment becomes effective
            if new_status == 'effective' and treatment_details and 'residual_likelihood' in treatment_details:
                risk.residual_likelihood = treatment_details['residual_likelihood']
                risk.residual_impact = treatment_details['residual_impact']
                risk.residual_risk_score = risk._calculate_risk_score(
                    risk.residual_likelihood, risk.residual_impact
                )
                risk.residual_risk_level = risk._get_risk_level(risk.residual_risk_score)
                risk.requires_treatment = risk.residual_risk_score >= risk.risk_threshold

            risk.save()
            updated_count += 1

        return updated_count

    def get_risk_trends(self, asset_ids: Optional[List[uuid.UUID]] = None,
                        months: int = 12) -> Dict[str, Any]:
        """Get risk trends over time"""
        # This would typically involve time-series analysis
        # For now, return placeholder structure
        return {
            'periods': [f'Month {i+1}' for i in range(months)],
            'total_risks': [0] * months,
            'critical_risks': [0] * months,
            'high_risks': [0] * months,
            'treatment_effectiveness': [0.0] * months,
            'generated_at': str(timezone.now())
        }

    def get_risk_distribution_by_category(self, asset_ids: Optional[List[uuid.UUID]] = None) -> Dict[str, int]:
        """Get risk distribution by category"""
        query = self.model.objects.all()
        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)

        from django.db.models import Count
        distribution = dict(query.values('risk_category').annotate(
            count=Count('id')
        ).values_list('risk_category', 'count'))

        return distribution

    def get_treatment_effectiveness_report(self, asset_ids: Optional[List[uuid.UUID]] = None) -> Dict[str, Any]:
        """Generate treatment effectiveness report"""
        query = self.model.objects.all()
        if asset_ids:
            query = query.filter(asset_id__in=asset_ids)

        risks = list(query)

        total_requiring_treatment = len([r for r in risks if r.requires_treatment])
        effectively_treated = len([r for r in risks if r.treatment_status == 'effective'])
        under_treatment = len([r for r in risks if r.treatment_status in ['planned', 'in_progress', 'implemented']])

        return {
            'total_requiring_treatment': total_requiring_treatment,
            'effectively_treated': effectively_treated,
            'under_treatment': under_treatment,
            'treatment_effectiveness_percentage': round(
                (effectively_treated / total_requiring_treatment * 100) if total_requiring_treatment > 0 else 0, 2
            ),
            'untreated_count': total_requiring_treatment - effectively_treated - under_treatment,
            'generated_at': str(timezone.now())
        }

    def find_similar_risks(self, risk_id: str, limit: int = 5) -> List[AssetRisk]:
        """Find similar risks based on category and severity"""
        try:
            risk = self.model.objects.get(id=risk_id)
        except self.model.DoesNotExist:
            return []

        similar_risks = self.model.objects.filter(
            risk_category=risk.risk_category,
            residual_risk_level=risk.residual_risk_level
        ).exclude(id=risk_id)[:limit]

        return list(similar_risks)
