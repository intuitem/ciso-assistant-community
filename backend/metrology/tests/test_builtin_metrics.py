"""Tests for the builtin metric registry and computation logic."""

import pytest

from core.models import (
    AppliedControl,
    Incident,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    SecurityException,
    Severity,
    Perimeter,
    Terminology,
)
from iam.models import Folder
from metrology.builtin_metrics import (
    BUILTIN_METRICS,
    get_available_metrics_for_model,
)
from metrology.models import BuiltinMetricSample


def _qualification(name):
    """Get-or-create a qualification terminology row."""
    obj, _ = Terminology.objects.get_or_create(
        field_path=Terminology.FieldPath.QUALIFICATIONS,
        name=name,
        defaults={"is_visible": True},
    )
    return obj


@pytest.fixture
def domain():
    return Folder.objects.create(
        name="Test Domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def root():
    return Folder.get_root_folder()


@pytest.mark.django_db
class TestBuiltinMetricsRegistry:
    def test_folder_registry_contains_new_metrics(self):
        keys = set(get_available_metrics_for_model("Folder").keys())
        for expected in [
            "incidents_detection_breakdown",
            "incidents_qualifications_breakdown",
            "task_templates_status_breakdown",
            "security_exceptions_status_breakdown",
            "security_exceptions_severity_breakdown",
            "total_security_exceptions",
            "total_risk_acceptances",
            "total_frameworks_in_use",
            "risk_scenarios_qualifications_breakdown",
        ]:
            assert expected in keys, f"missing {expected} from Folder registry"

    def test_risk_assessment_has_qualifications_breakdown(self):
        keys = set(get_available_metrics_for_model("RiskAssessment").keys())
        assert "qualifications_breakdown" in keys


@pytest.mark.django_db
class TestFolderMetricsCompute:
    def test_empty_folder_returns_zero_counts(self, domain):
        m = BuiltinMetricSample.compute_metrics(domain)
        assert m["total_incidents"] == 0
        assert m["total_controls"] == 0
        assert m["total_security_exceptions"] == 0
        assert m["total_risk_acceptances"] == 0
        assert m["total_frameworks_in_use"] == 0
        assert m["incidents_severity_breakdown"] == {}
        assert m["incidents_detection_breakdown"] == {}
        assert m["security_exceptions_status_breakdown"] == {}

    def test_incident_breakdowns(self, domain):
        Incident.objects.create(
            name="Inc A",
            folder=domain,
            severity=Incident.Severity.SEV1,
            detection=Incident.Detection.INTERNAL,
        )
        Incident.objects.create(
            name="Inc B",
            folder=domain,
            severity=Incident.Severity.SEV1,
            detection=Incident.Detection.EXTERNAL,
        )
        Incident.objects.create(
            name="Inc C",
            folder=domain,
            severity=Incident.Severity.SEV3,
            detection=Incident.Detection.INTERNAL,
        )

        m = BuiltinMetricSample.compute_metrics(domain)
        assert m["total_incidents"] == 3
        # Severity labels are humanized (Critical, Moderate, ...)
        assert m["incidents_severity_breakdown"].get("Critical") == 2
        assert m["incidents_severity_breakdown"].get("Moderate") == 1
        assert m["incidents_detection_breakdown"].get("Internal") == 2
        assert m["incidents_detection_breakdown"].get("External") == 1

    def test_incident_qualifications(self, domain):
        inc = Incident.objects.create(name="Inc Q", folder=domain)
        q1 = _qualification("authenticity")
        q2 = _qualification("availability")
        inc.qualifications.add(q1, q2)

        m = BuiltinMetricSample.compute_metrics(domain)
        assert m["incidents_qualifications_breakdown"] == {
            "authenticity": 1,
            "availability": 1,
        }

    def test_security_exception_breakdowns(self, domain):
        SecurityException.objects.create(
            name="Exc 1",
            folder=domain,
            status=SecurityException.Status.DRAFT,
            severity=Severity.LOW,
        )
        SecurityException.objects.create(
            name="Exc 2",
            folder=domain,
            status=SecurityException.Status.APPROVED,
            severity=Severity.HIGH,
        )

        m = BuiltinMetricSample.compute_metrics(domain)
        assert m["total_security_exceptions"] == 2
        assert m["security_exceptions_status_breakdown"].get("draft") == 1
        assert m["security_exceptions_status_breakdown"].get("approved") == 1

    def test_root_folder_aggregates_globally(self, root, domain):
        # Create a control in a domain — it should show up at root scope.
        AppliedControl.objects.create(name="Ctrl A", folder=domain, status="active")
        AppliedControl.objects.create(name="Ctrl B", folder=domain, status="to_do")

        root_metrics = BuiltinMetricSample.compute_metrics(root)
        # At least the two we just created (other tests may have left rows
        # in the same db transaction scope, but per-test rollback isolates us).
        assert root_metrics["total_controls"] >= 2
        assert root_metrics["controls_status_breakdown"].get("active", 0) >= 1


@pytest.mark.django_db
class TestRiskAssessmentMetrics:
    def test_qualifications_breakdown(self, domain):
        matrix = RiskMatrix.objects.first()
        if matrix is None:
            pytest.skip("RiskMatrix fixture not available in this test db.")
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        ra = RiskAssessment.objects.create(
            name="RA", folder=domain, perimeter=perimeter, risk_matrix=matrix
        )
        scenario = RiskScenario.objects.create(name="S", risk_assessment=ra)
        scenario.qualifications.add(_qualification("financial"))

        m = BuiltinMetricSample.compute_metrics(ra)
        assert m["qualifications_breakdown"] == {"financial": 1}


def test_metric_type_chart_types_consistent():
    """Every registered metric_type has at least one allowed chart type."""
    from metrology.builtin_metrics import METRIC_TYPE_CHART_TYPES

    for model_metrics in BUILTIN_METRICS.values():
        for meta in model_metrics.values():
            mtype = meta["type"]
            assert mtype in METRIC_TYPE_CHART_TYPES
            assert len(METRIC_TYPE_CHART_TYPES[mtype]) > 0
