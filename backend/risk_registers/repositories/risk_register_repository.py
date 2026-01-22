"""
Risk Register Repository

Repository for managing RiskRegister aggregates with support for
consolidated risk reporting and cross-domain risk analysis.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.utils import timezone

from core.domain.repository import Repository
from ..models.risk_register import RiskRegister


class RiskRegisterRepository(Repository[RiskRegister]):
    """
    Repository for RiskRegister aggregates.

    Provides methods for managing consolidated risk registers,
    cross-domain risk analysis, and organizational risk reporting.
    """

    def __init__(self):
        super().__init__(RiskRegister)

    def find_by_scope(self, scope: str) -> List[RiskRegister]:
        """Find risk registers by scope"""
        return list(self.model.objects.filter(scope=scope, status='active'))

    def find_by_owner(self, owner_user_id: uuid.UUID) -> List[RiskRegister]:
        """Find risk registers owned by a specific user"""
        return list(self.model.objects.filter(owner_user_id=owner_user_id))

    def find_active_registers(self) -> List[RiskRegister]:
        """Find all active risk registers"""
        return list(self.model.objects.filter(status='active'))

    def find_overdue_for_report(self) -> List[RiskRegister]:
        """Find registers overdue for reporting"""
        today = timezone.now().date()
        return list(self.model.objects.filter(
            status='active',
            next_report_date__isnull=False,
            next_report_date__lt=today
        ))

    def find_overdue_for_review(self) -> List[RiskRegister]:
        """Find registers overdue for review"""
        today = timezone.now().date()
        return list(self.model.objects.filter(
            status='active',
            next_review_date__isnull=False,
            next_review_date__lt=today
        ))

    def get_enterprise_risk_summary(self) -> Dict[str, Any]:
        """Get enterprise-wide risk summary across all active registers"""
        active_registers = self.find_active_registers()

        total_registers = len(active_registers)
        total_risks = sum(register.total_risks for register in active_registers)
        total_critical = sum(register.critical_risks for register in active_registers)
        total_high = sum(register.high_risks for register in active_registers)
        total_moderate = sum(register.moderate_risks for register in active_registers)
        total_low = sum(register.low_risks for register in active_registers)

        total_requiring_treatment = sum(register.risks_requiring_treatment for register in active_registers)
        total_under_treatment = sum(register.risks_under_treatment for register in active_registers)
        total_effectively_treated = sum(register.risks_effectively_treated for register in active_registers)

        # Calculate enterprise treatment effectiveness
        treatment_effectiveness = round(
            (total_effectively_treated / total_requiring_treatment * 100) if total_requiring_treatment > 0 else 0, 2
        )

        return {
            'total_registers': total_registers,
            'total_risks': total_risks,
            'risk_distribution': {
                'critical': total_critical,
                'high': total_high,
                'moderate': total_moderate,
                'low': total_low,
            },
            'treatment_summary': {
                'requiring_treatment': total_requiring_treatment,
                'under_treatment': total_under_treatment,
                'effectively_treated': total_effectively_treated,
                'treatment_effectiveness_percentage': treatment_effectiveness,
            },
            'registers_overdue_reports': len(self.find_overdue_for_report()),
            'registers_overdue_reviews': len(self.find_overdue_for_review()),
            'generated_at': str(timezone.now())
        }

    def get_risk_heat_map_enterprise(self) -> Dict[str, Any]:
        """Generate enterprise-wide risk heat map"""
        active_registers = self.find_active_registers()

        # Aggregate heat map data from all registers
        # Initialize 5x5 matrix
        matrix = [[0 for _ in range(5)] for _ in range(5)]

        for register in active_registers:
            register_heat_map = register.risk_heat_map
            if register_heat_map and 'matrix' in register_heat_map:
                register_matrix = register_heat_map['matrix']
                for i in range(5):
                    for j in range(5):
                        if i < len(register_matrix) and j < len(register_matrix[i]):
                            matrix[i][j] += register_matrix[i][j]

        return {
            'matrix': matrix,
            'labels': {
                'likelihood': ['Very Low (1)', 'Low (2)', 'Moderate (3)', 'High (4)', 'Very High (5)'],
                'impact': ['Very Low (1)', 'Low (2)', 'Moderate (3)', 'High (4)', 'Very High (5)']
            },
            'total_risks': sum(sum(row) for row in matrix),
            'generated_at': str(timezone.now())
        }

    def get_top_enterprise_risks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top enterprise risks across all registers"""
        # This would require cross-aggregate queries
        # For now, return aggregated data from registers
        active_registers = self.find_active_registers()

        top_risks = []
        for register in active_registers:
            register_top_risks = register.get_top_risks(limit=5)  # Get 5 from each register
            for risk in register_top_risks:
                risk['register_id'] = register.register_id
                risk['register_name'] = register.name
                top_risks.append(risk)

        # Sort by risk score and limit
        top_risks.sort(key=lambda x: x.get('score', 0), reverse=True)
        return top_risks[:limit]

    def get_risk_trends_enterprise(self, months: int = 12) -> Dict[str, Any]:
        """Get enterprise risk trends over time"""
        # This would aggregate trends from all registers
        # For now, return placeholder structure
        return {
            'periods': [f'Month {i+1}' for i in range(months)],
            'total_risks': [0] * months,
            'critical_risks': [0] * months,
            'high_risks': [0] * months,
            'treatment_effectiveness': [0.0] * months,
            'generated_at': str(timezone.now())
        }

    def get_register_performance_comparison(self) -> List[Dict[str, Any]]:
        """Compare performance across risk registers"""
        active_registers = self.find_active_registers()

        comparison_data = []
        for register in active_registers:
            comparison_data.append({
                'register_id': register.register_id,
                'register_name': register.name,
                'scope': register.scope,
                'total_risks': register.total_risks,
                'critical_risks': register.critical_risks,
                'high_risks': register.high_risks,
                'treatment_effectiveness': register.treatment_effectiveness,
                'risks_within_appetite': register.risks_within_appetite,
                'risks_exceeding_appetite': register.risks_exceeding_appetite,
                'is_overdue_report': register.is_overdue_for_report,
                'is_overdue_review': register.is_overdue_for_review,
            })

        return comparison_data

    def get_compliance_alignment_report(self) -> Dict[str, Any]:
        """Get report on how risk registers align with compliance requirements"""
        active_registers = self.find_active_registers()

        compliance_coverage = {}
        for register in active_registers:
            for framework in register.compliance_frameworks:
                if framework not in compliance_coverage:
                    compliance_coverage[framework] = {
                        'registers': 0,
                        'total_risks': 0,
                        'critical_risks': 0,
                        'treated_risks': 0,
                    }

                compliance_coverage[framework]['registers'] += 1
                compliance_coverage[framework]['total_risks'] += register.total_risks
                compliance_coverage[framework]['critical_risks'] += register.critical_risks
                compliance_coverage[framework]['treated_risks'] += register.risks_effectively_treated

        return {
            'compliance_coverage': compliance_coverage,
            'total_registers': len(active_registers),
            'generated_at': str(timezone.now())
        }

    def consolidate_all_registers(self) -> int:
        """Trigger statistics consolidation for all active registers"""
        active_registers = self.find_active_registers()
        consolidated_count = 0

        for register in active_registers:
            register.consolidate_statistics()
            register.save()
            consolidated_count += 1

        return consolidated_count

    def generate_enterprise_report(self, report_date: Optional[timezone.date] = None) -> Dict[str, Any]:
        """Generate comprehensive enterprise risk report"""
        report_date = report_date or timezone.now().date()

        # Update report dates for all registers
        active_registers = self.find_active_registers()
        for register in active_registers:
            register.generate_report(report_date)
            register.save()

        return {
            'report_date': str(report_date),
            'enterprise_summary': self.get_enterprise_risk_summary(),
            'heat_map': self.get_risk_heat_map_enterprise(),
            'top_risks': self.get_top_enterprise_risks(limit=25),
            'register_comparison': self.get_register_performance_comparison(),
            'compliance_alignment': self.get_compliance_alignment_report(),
            'generated_at': str(timezone.now())
        }

    def get_registers_by_risk_level(self, risk_level: str) -> List[RiskRegister]:
        """Find registers containing risks of a specific level"""
        # This would require checking the actual risk aggregates
        # For now, return all active registers (placeholder)
        return self.find_active_registers()

    def get_register_health_score(self, register_id: str) -> Dict[str, Any]:
        """Calculate health score for a specific register"""
        try:
            register = self.model.objects.get(register_id=register_id)
        except self.model.DoesNotExist:
            return {}

        # Calculate health score based on various factors
        health_factors = {
            'up_to_date_reports': 1 if not register.is_overdue_for_report else 0,
            'up_to_date_reviews': 1 if not register.is_overdue_for_review else 0,
            'treatment_effectiveness': min(register.treatment_effectiveness / 100, 1),
            'risks_within_appetite': min(register.risks_within_appetite / register.total_risks, 1) if register.total_risks > 0 else 1,
            'data_completeness': 1 if register.total_risks > 0 else 0,
        }

        overall_health = round(sum(health_factors.values()) / len(health_factors) * 100, 2)

        return {
            'register_id': register_id,
            'overall_health_score': overall_health,
            'health_factors': health_factors,
            'recommendations': self._generate_health_recommendations(health_factors),
            'calculated_at': str(timezone.now())
        }

    def _generate_health_recommendations(self, health_factors: Dict[str, float]) -> List[str]:
        """Generate health improvement recommendations"""
        recommendations = []

        if health_factors['up_to_date_reports'] < 1:
            recommendations.append("Generate overdue risk reports to maintain compliance")
        if health_factors['up_to_date_reviews'] < 1:
            recommendations.append("Conduct overdue risk register reviews")
        if health_factors['treatment_effectiveness'] < 0.8:
            recommendations.append("Improve risk treatment effectiveness through better planning")
        if health_factors['risks_within_appetite'] < 0.8:
            recommendations.append("Address risks exceeding organizational appetite")
        if health_factors['data_completeness'] < 1:
            recommendations.append("Complete risk register data collection")

        return recommendations

    def archive_inactive_registers(self, older_than_days: int = 365) -> int:
        """Archive registers that haven't been updated recently"""
        cutoff_date = timezone.now() - timezone.timedelta(days=older_than_days)

        inactive_registers = self.model.objects.filter(
            status='active',
            updated_at__lt=cutoff_date
        )

        archived_count = 0
        for register in inactive_registers:
            register.archive_register("Automated archival due to inactivity")
            register.save()
            archived_count += 1

        return archived_count
