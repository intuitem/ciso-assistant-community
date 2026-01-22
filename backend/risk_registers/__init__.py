"""
Risk Registers Bounded Context

This bounded context manages comprehensive risk management including:
- Asset risk assessments with CVSS scoring
- Risk treatment planning and tracking
- Risk register consolidation and reporting
- Risk heat maps and analytics
- Multi-domain risk aggregation

Key aggregates:
- AssetRisk: Individual asset risk assessments
- RiskRegister: Master risk registers with aggregation

Key services:
- RiskAssessmentService: Risk calculation and assessment
- RiskReportingService: Analytics and reporting

API endpoints:
- /api/risks/asset-risks/ - Asset risk management
- /api/risks/registers/ - Risk register management
- /api/risks/reporting/ - Risk reporting and analytics
"""

__version__ = "1.0.0"
__description__ = "Risk Registers Bounded Context for comprehensive risk management"
