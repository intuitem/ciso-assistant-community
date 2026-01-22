"""
Risk Reporting Service

Service for generating risk reports, dashboards, and analytics
across the risk management domain.
"""

import uuid
from typing import Dict, List, Optional, Any
from django.utils import timezone
from datetime import timedelta

from ..repositories.asset_risk_repository import AssetRiskRepository
from ..repositories.risk_register_repository import RiskRegisterRepository


class RiskReportingService:
    """
    Service for risk reporting and analytics.

    Provides methods for generating risk reports, heat maps,
    trends analysis, and executive dashboards.
    """

    def __init__(self):
        self.asset_risk_repo = AssetRiskRepository()
        self.risk_register_repo = RiskRegisterRepository()

    def generate_risk_dashboard_data(self, scope: str = 'enterprise',
                                   filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive risk dashboard data.

        Args:
            scope: 'enterprise', 'asset', or 'register'
            filters: Optional filters for the data

        Returns:
            Dict with dashboard data
        """
        filters = filters or {}

        if scope == 'enterprise':
            return self._generate_enterprise_dashboard(filters)
        elif scope == 'asset' and 'asset_id' in filters:
            return self._generate_asset_dashboard(uuid.UUID(filters['asset_id']), filters)
        elif scope == 'register' and 'register_id' in filters:
            return self._generate_register_dashboard(filters['register_id'], filters)
        else:
            raise ValueError(f"Invalid scope '{scope}' or missing required filters")

    def _generate_enterprise_dashboard(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate enterprise-wide risk dashboard"""
        enterprise_summary = self.risk_register_repo.get_enterprise_risk_summary()

        # Get additional metrics
        risk_trends = self.asset_risk_repo.get_risk_trends(
            asset_ids=filters.get('asset_ids'),
            months=filters.get('months', 12)
        )

        heat_map = self.risk_register_repo.get_risk_heat_map_enterprise()

        top_risks = self.risk_register_repo.get_top_enterprise_risks(
            limit=filters.get('top_risks_limit', 20)
        )

        # Calculate key performance indicators
        kpis = self._calculate_risk_kpis(enterprise_summary)

        return {
            'scope': 'enterprise',
            'summary': enterprise_summary,
            'kpis': kpis,
            'heat_map': heat_map,
            'top_risks': top_risks,
            'trends': risk_trends,
            'generated_at': str(timezone.now())
        }

    def _generate_asset_dashboard(self, asset_id: uuid.UUID, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate asset-specific risk dashboard"""
        asset_risks = self.asset_risk_repo.find_by_asset(asset_id)
        asset_stats = self.asset_risk_repo.get_risk_statistics_for_asset(asset_id)

        # Get risk heat map for this asset
        heat_map = self.asset_risk_repo.get_risk_heat_map_data(asset_ids=[asset_id])

        # Get treatment effectiveness
        treatment_report = self.asset_risk_repo.get_treatment_effectiveness_report(asset_ids=[asset_id])

        # Get risks requiring attention
        attention_risks = self.asset_risk_repo.get_risks_requiring_attention(asset_ids=[asset_id])

        return {
            'scope': 'asset',
            'asset_id': str(asset_id),
            'total_risks': len(asset_risks),
            'statistics': asset_stats,
            'heat_map': heat_map,
            'treatment_effectiveness': treatment_report,
            'attention_required': len(attention_risks),
            'attention_risks': [{
                'id': str(r.id),
                'risk_id': r.risk_id,
                'title': r.risk_title,
                'level': r.residual_risk_level,
                'score': r.residual_risk_score
            } for r in attention_risks[:10]],  # Top 10
            'generated_at': str(timezone.now())
        }

    def _generate_register_dashboard(self, register_id: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate risk register dashboard"""
        # Get register health score
        health_score = self.risk_register_repo.get_register_health_score(register_id)

        # Get register comparison data
        comparison = self.risk_register_repo.get_register_performance_comparison()

        # Find this register in comparison
        register_data = None
        for reg in comparison:
            if reg['register_id'] == register_id:
                register_data = reg
                break

        return {
            'scope': 'register',
            'register_id': register_id,
            'health_score': health_score,
            'performance': register_data,
            'comparison': comparison,
            'generated_at': str(timezone.now())
        }

    def _calculate_risk_kpis(self, enterprise_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate key risk performance indicators"""
        total_risks = enterprise_summary['total_risks']
        treatment_summary = enterprise_summary['treatment_summary']

        # Risk Distribution KPI
        risk_distribution = enterprise_summary['risk_distribution']
        high_critical_count = risk_distribution['high'] + risk_distribution['critical']
        high_critical_percentage = (high_critical_count / total_risks * 100) if total_risks > 0 else 0

        # Treatment Effectiveness KPI
        treatment_effectiveness = treatment_summary['treatment_effectiveness_percentage']

        # Risk Appetite Compliance KPI
        # Simplified: assume moderate appetite means high+critical should be < 20%
        appetite_compliance = 100 - high_critical_percentage  # Higher is better

        # Overall Risk Health Score
        health_score = (
            (100 - high_critical_percentage) * 0.4 +  # Risk distribution (40%)
            treatment_effectiveness * 0.4 +           # Treatment effectiveness (40%)
            appetite_compliance * 0.2                 # Appetite compliance (20%)
        )

        return {
            'high_critical_percentage': round(high_critical_percentage, 2),
            'treatment_effectiveness_percentage': treatment_effectiveness,
            'appetite_compliance_score': round(appetite_compliance, 2),
            'overall_health_score': round(health_score, 2),
            'risk_distribution_status': self._get_kpi_status(high_critical_percentage, 'risk_distribution'),
            'treatment_status': self._get_kpi_status(100 - treatment_effectiveness, 'treatment'),
            'appetite_status': self._get_kpi_status(100 - appetite_compliance, 'appetite')
        }

    def _get_kpi_status(self, value: float, kpi_type: str) -> str:
        """Get status indicator for KPI value"""
        if kpi_type == 'risk_distribution':
            if value <= 10:
                return 'excellent'
            elif value <= 20:
                return 'good'
            elif value <= 30:
                return 'moderate'
            else:
                return 'poor'
        elif kpi_type == 'treatment':
            if value <= 20:
                return 'excellent'
            elif value <= 40:
                return 'good'
            elif value <= 60:
                return 'moderate'
            else:
                return 'poor'
        elif kpi_type == 'appetite':
            if value <= 10:
                return 'excellent'
            elif value <= 25:
                return 'good'
            elif value <= 50:
                return 'moderate'
            else:
                return 'poor'
        return 'unknown'

    def generate_risk_register_report(self, register_id: str, report_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Generate detailed risk register report.

        Args:
            register_id: ID of the risk register
            report_type: Type of report ('comprehensive', 'executive', 'technical')

        Returns:
            Dict with report data
        """
        # Get register health and performance
        health_score = self.risk_register_repo.get_register_health_score(register_id)

        # Get enterprise comparison
        comparison = self.risk_register_repo.get_register_performance_comparison()

        # Get risk trends
        trends = self.asset_risk_repo.get_risk_trends(months=12)

        # Get top risks (placeholder - would filter by register)
        top_risks = self.asset_risk_repo.get_top_risks(limit=25)

        if report_type == 'executive':
            return self._generate_executive_report(register_id, health_score, comparison)
        elif report_type == 'technical':
            return self._generate_technical_report(register_id, health_score, trends, top_risks)
        else:  # comprehensive
            return self._generate_comprehensive_report(register_id, health_score, comparison, trends, top_risks)

    def _generate_executive_report(self, register_id: str, health_score: Dict, comparison: List[Dict]) -> Dict[str, Any]:
        """Generate executive summary report"""
        return {
            'report_type': 'executive',
            'register_id': register_id,
            'health_score': health_score['overall_health_score'],
            'key_metrics': {
                'risk_distribution': health_score.get('health_factors', {}).get('risks_within_appetite', 0),
                'treatment_effectiveness': health_score.get('health_factors', {}).get('treatment_effectiveness', 0),
                'compliance_status': 'compliant' if health_score['overall_health_score'] >= 80 else 'needs_attention'
            },
            'recommendations': health_score.get('recommendations', []),
            'generated_at': str(timezone.now())
        }

    def _generate_technical_report(self, register_id: str, health_score: Dict, trends: Dict, top_risks: List) -> Dict[str, Any]:
        """Generate technical detail report"""
        return {
            'report_type': 'technical',
            'register_id': register_id,
            'health_factors': health_score.get('health_factors', {}),
            'trends_analysis': trends,
            'top_risks': top_risks,
            'technical_metrics': {
                'data_completeness': health_score.get('health_factors', {}).get('data_completeness', 0),
                'update_frequency': health_score.get('health_factors', {}).get('up_to_date_reports', 0),
                'review_compliance': health_score.get('health_factors', {}).get('up_to_date_reviews', 0)
            },
            'generated_at': str(timezone.now())
        }

    def _generate_comprehensive_report(self, register_id: str, health_score: Dict, comparison: List[Dict],
                                     trends: Dict, top_risks: List) -> Dict[str, Any]:
        """Generate comprehensive report"""
        return {
            'report_type': 'comprehensive',
            'register_id': register_id,
            'executive_summary': self._generate_executive_report(register_id, health_score, comparison),
            'technical_details': self._generate_technical_report(register_id, health_score, trends, top_risks),
            'comparative_analysis': comparison,
            'action_items': health_score.get('recommendations', []),
            'generated_at': str(timezone.now())
        }

    def generate_risk_heat_map_report(self, scope: str = 'enterprise',
                                    filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate risk heat map report.

        Args:
            scope: Scope of the heat map ('enterprise', 'asset', 'register')
            filters: Optional filters

        Returns:
            Dict with heat map data and analysis
        """
        if scope == 'enterprise':
            heat_map = self.risk_register_repo.get_risk_heat_map_enterprise()
        elif scope == 'asset' and filters and 'asset_id' in filters:
            heat_map = self.asset_risk_repo.get_risk_heat_map_data(
                asset_ids=[uuid.UUID(filters['asset_id'])]
            )
        else:
            raise ValueError(f"Invalid scope '{scope}' or missing filters")

        # Analyze heat map patterns
        analysis = self._analyze_heat_map(heat_map)

        return {
            'scope': scope,
            'heat_map': heat_map,
            'analysis': analysis,
            'generated_at': str(timezone.now())
        }

    def _analyze_heat_map(self, heat_map: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze heat map patterns and provide insights"""
        matrix = heat_map.get('matrix', [])
        if not matrix or len(matrix) != 5:
            return {'error': 'Invalid heat map matrix'}

        analysis = {
            'total_risks': sum(sum(row) for row in matrix),
            'high_risk_zones': [],
            'dominant_patterns': [],
            'insights': []
        }

        # Identify high-risk zones (likelihood >= 3, impact >= 3)
        high_risk_zones = []
        for i in range(3, 5):  # High/Very High likelihood
            for j in range(3, 5):  # High/Very High impact
                if matrix[i][j] > 0:
                    high_risk_zones.append({
                        'likelihood': i + 1,
                        'impact': j + 1,
                        'count': matrix[i][j]
                    })

        analysis['high_risk_zones'] = high_risk_zones

        # Identify dominant patterns
        max_count = max(max(row) for row in matrix) if matrix else 0
        if max_count > 0:
            dominant_cells = []
            for i in range(5):
                for j in range(5):
                    if matrix[i][j] == max_count:
                        dominant_cells.append({
                            'likelihood': i + 1,
                            'impact': j + 1,
                            'count': matrix[i][j]
                        })
            analysis['dominant_patterns'] = dominant_cells

        # Generate insights
        insights = []
        if high_risk_zones:
            insights.append(f"Found {len(high_risk_zones)} high-risk zones requiring immediate attention")

        if analysis['total_risks'] > 50:
            insights.append("Large number of risks suggests need for prioritization framework")

        # Risk concentration analysis
        total = analysis['total_risks']
        if total > 0:
            high_risk_count = sum(zone['count'] for zone in high_risk_zones)
            concentration = (high_risk_count / total) * 100
            if concentration > 30:
                insights.append(".1f")
            elif concentration < 10:
                insights.append(".1f")

        analysis['insights'] = insights

        return analysis

    def generate_risk_trends_report(self, months: int = 12,
                                  filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate risk trends report.

        Args:
            months: Number of months to analyze
            filters: Optional filters

        Returns:
            Dict with trends analysis
        """
        trends = self.asset_risk_repo.get_risk_trends(
            asset_ids=filters.get('asset_ids') if filters else None,
            months=months
        )

        # Analyze trends
        analysis = self._analyze_trends(trends)

        return {
            'periods': trends.get('periods', []),
            'trends': trends,
            'analysis': analysis,
            'generated_at': str(timezone.now())
        }

    def _analyze_trends(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze risk trends and provide insights"""
        periods = trends.get('periods', [])
        total_risks = trends.get('total_risks', [])
        critical_risks = trends.get('critical_risks', [])
        treatment_effectiveness = trends.get('treatment_effectiveness', [])

        analysis = {
            'trend_direction': 'stable',
            'significant_changes': [],
            'insights': []
        }

        if len(total_risks) >= 2:
            # Analyze total risk trend
            first_half = total_risks[:len(total_risks)//2]
            second_half = total_risks[len(total_risks)//2:]

            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0

            if second_avg > first_avg * 1.2:
                analysis['trend_direction'] = 'increasing'
                analysis['insights'].append("Risk count is increasing over time")
            elif second_avg < first_avg * 0.8:
                analysis['trend_direction'] = 'decreasing'
                analysis['insights'].append("Risk count is decreasing over time")

        if len(critical_risks) >= 2:
            # Analyze critical risk trend
            first_half = critical_risks[:len(critical_risks)//2]
            second_half = critical_risks[len(critical_risks)//2:]

            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0

            if second_avg > first_avg * 1.5:
                analysis['significant_changes'].append("Critical risks are significantly increasing")
            elif second_avg < first_avg * 0.5:
                analysis['significant_changes'].append("Critical risks are significantly decreasing")

        # Analyze treatment effectiveness
        if treatment_effectiveness:
            avg_effectiveness = sum(treatment_effectiveness) / len(treatment_effectiveness)
            if avg_effectiveness >= 80:
                analysis['insights'].append("Strong risk treatment effectiveness")
            elif avg_effectiveness <= 50:
                analysis['insights'].append("Risk treatment effectiveness needs improvement")

        return analysis
