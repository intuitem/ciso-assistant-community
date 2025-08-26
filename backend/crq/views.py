from core.views import BaseModelViewSet as AbstractBaseModelViewSet

from .models import (
    QuantitativeRiskStudy,
    QuantitativeRiskScenario,
    QuantitativeRiskHypothesis,
    QuantitativeRiskAggregation,
)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "crq.serializers"


class QuantitativeRiskStudyViewSet(BaseModelViewSet):
    model = QuantitativeRiskStudy
    filterset_fields = [
        "folder",
        "authors",
        "reviewers",
        "status",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]


class QuantitativeRiskScenarioViewSet(BaseModelViewSet):
    model = QuantitativeRiskScenario
    filterset_fields = [
        "quantitative_risk_study",
        "assets",
        "threats",
        "vulnerabilities",
        "qualifications",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]


class QuantitativeRiskHypothesisViewSet(BaseModelViewSet):
    model = QuantitativeRiskHypothesis
    filterset_fields = [
        "quantitative_risk_study",
        "quantitative_risk_scenario",
        "quantitative_risk_aggregations",
        "existing_applied_controls",
        "added_applied_controls",
        "removed_applied_controls",
        "status",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]


class QuantitativeRiskAggregationViewSet(BaseModelViewSet):
    model = QuantitativeRiskAggregation
    filterset_fields = [
        "quantitative_risk_study",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["-created_at"]
