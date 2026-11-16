"""Summary briefing metrics: per-matrix top risk levels and the attention counts."""

import copy
from datetime import date, timedelta

import pytest

from core.helpers import count_top_risk_levels
from core.models import (
    AppliedControl,
    Finding,
    FindingsAssessment,
    Incident,
    Perimeter,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    TaskNode,
    TaskTemplate,
)
from iam.models import Folder
from privacy.test_data_breach import admin_client, domain  # noqa: F401
from test_fixtures import RISK_MATRIX_JSON_DEFINITION


def _scenarios(domain, json_def, levels):
    perimeter, _ = Perimeter.objects.get_or_create(name="p", folder=domain)
    matrix = RiskMatrix.objects.create(
        name=f"m{len(json_def['risk'])}",
        json_definition=json_def,
        folder=Folder.get_root_folder(),
    )
    ra = RiskAssessment.objects.create(
        name=f"ra{len(json_def['risk'])}",
        perimeter=perimeter,
        risk_matrix=matrix,
        folder=domain,
    )
    for i, (current, residual) in enumerate(levels):
        s = RiskScenario.objects.create(name=f"s{i}", risk_assessment=ra, folder=domain)
        # Levels are derived on save; pin them to test the counting alone.
        RiskScenario.objects.filter(pk=s.pk).update(
            current_level=current, residual_level=residual
        )


@pytest.mark.django_db
def test_top_levels_are_matrix_relative(domain):  # noqa: F811
    # 3 levels: only the top one counts.
    _scenarios(domain, RISK_MATRIX_JSON_DEFINITION, [(2, 0), (1, 1), (-1, -1)])
    # 5 levels: the top two count (3 and 4).
    five = copy.deepcopy(RISK_MATRIX_JSON_DEFINITION)
    five["risk"] = [dict(five["risk"][0], abbreviation=str(i)) for i in range(5)]
    # (4, -1): residual not assessed yet, so it stays at its current level.
    _scenarios(domain, five, [(4, 2), (3, 3), (2, 0), (4, -1)])

    qs = RiskScenario.objects.all()
    assert count_top_risk_levels(qs, "current_level") == 4
    assert count_top_risk_levels(qs, "residual_level") == 2
    # No inherent level anywhere: each scenario counts at its current level, until one is set lower.
    assert count_top_risk_levels(qs, "inherent_level") == 4
    qs.filter(name="s0", current_level=4).update(inherent_level=0)
    assert count_top_risk_levels(qs, "inherent_level") == 3


@pytest.mark.django_db
def test_get_metrics_exposes_briefing_counts(admin_client, domain):  # noqa: F811
    AppliedControl.objects.create(name="no status", folder=domain)
    AppliedControl.objects.create(name="active", folder=domain, status="active")
    Incident.objects.create(name="open", folder=domain)
    Incident.objects.create(name="closed", folder=domain, status=Incident.Status.CLOSED)
    fa = FindingsAssessment.objects.create(name="fa", folder=domain)
    Finding.objects.create(name="open", folder=domain, findings_assessment=fa)
    Finding.objects.create(
        name="done",
        folder=domain,
        findings_assessment=fa,
        status=Finding.Status.RESOLVED,
    )
    # Counted once however many of its occurrences are late.
    template = TaskTemplate.objects.create(name="t", folder=domain)
    yesterday = date.today() - timedelta(days=1)
    for days in (1, 45):
        TaskNode.objects.create(
            task_template=template,
            folder=domain,
            due_date=date.today() - timedelta(days=days),
        )
    done = TaskTemplate.objects.create(name="done", folder=domain)
    TaskNode.objects.create(
        task_template=done, folder=domain, due_date=yesterday, status="completed"
    )
    disabled = TaskTemplate.objects.create(name="off", folder=domain, enabled=False)
    TaskNode.objects.create(task_template=disabled, folder=domain, due_date=yesterday)

    res = admin_client.get("/api/get_metrics/")
    assert res.status_code == 200
    data = res.json()["results"]
    assert data["controls"]["no_status"] == 1
    assert data["risk"]["high_current"] == 0
    assert data["compliance"]["assessed_items"] == 0
    assert data["operations"] == {
        "open_incidents": 1,
        "open_findings": 1,
        "overdue_tasks": 1,
        "nis2_overdue_incidents": 0,
        "overdue_vulnerabilities": 0,
    }
    overdue = admin_client.get("/api/task-templates/?overdue=true").json()
    assert overdue["count"] == 1


@pytest.mark.django_db
def test_top_level_filter_matches_the_count(admin_client, domain):  # noqa: F811
    _scenarios(domain, RISK_MATRIX_JSON_DEFINITION, [(2, 0), (1, 2), (-1, -1)])

    current = admin_client.get("/api/risk-scenarios/?top_level=current").json()
    residual = admin_client.get("/api/risk-scenarios/?top_level=residual").json()
    assert [s["name"] for s in current["results"]] == ["s0"]
    assert [s["name"] for s in residual["results"]] == ["s1"]
    inherent = admin_client.get("/api/risk-scenarios/?top_level=inherent").json()
    assert [s["name"] for s in inherent["results"]] == ["s0"]


@pytest.mark.django_db
def test_snapshot_matches_summary_and_trends_are_gated(
    admin_client, domain, monkeypatch
):  # noqa: F811
    from core.helpers import get_summary_trends
    from iam.models import User
    from metrology.models import BuiltinMetricSample

    AppliedControl.objects.create(name="no status", folder=domain)
    AppliedControl.objects.create(name="active", folder=domain, status="active")
    Incident.objects.create(name="open", folder=domain)
    fa = FindingsAssessment.objects.create(name="fa", folder=domain)
    Finding.objects.create(name="open", folder=domain, findings_assessment=fa)
    _scenarios(domain, RISK_MATRIX_JSON_DEFINITION, [(2, 0), (1, 1)])
    template = TaskTemplate.objects.create(name="t", folder=domain)
    for days in (1, 45):
        TaskNode.objects.create(
            task_template=template,
            folder=domain,
            due_date=date.today() - timedelta(days=days),
        )

    root = Folder.get_root_folder()
    snapshot = BuiltinMetricSample.compute_metrics(root)
    # The live trend point computes only this part; it must match the full snapshot.
    assert (
        BuiltinMetricSample._compute_summary_metrics(root).items() <= snapshot.items()
    )
    BuiltinMetricSample.update_or_create_snapshot(root)
    # A domain save leaves the stored root snapshot behind; the trend must still end on the live value.
    AppliedControl.objects.create(name="later", folder=domain, status="active")
    summary = admin_client.get("/api/get_metrics/").json()["results"]

    assert snapshot["controls_no_status"] == summary["controls"]["no_status"]
    assert snapshot["incidents_open"] == summary["operations"]["open_incidents"]
    assert snapshot["findings_open"] == summary["operations"]["open_findings"]
    assert snapshot["total_risk_scenarios"] == summary["risk"]["scenarios"]
    assert (
        snapshot["partially_compliant_items"]
        == summary["compliance"]["partially_compliant_items"]
    )
    assert snapshot["risk_scenarios_high_current"] == summary["risk"]["high_current"]
    assert snapshot["task_templates_overdue"] == summary["operations"]["overdue_tasks"]

    trends = summary["trends"]
    assert trends["active_controls"][-1][1] == summary["controls"]["active"]
    assert trends["incidents_open"][-1][1] == 1

    nobody = User.objects.create_user(email="no-global-view@tests.local")
    assert get_summary_trends(nobody) is None

    assert admin_client.get("/api/analytics/export/xlsx/").status_code == 200

    admin = User.objects.get(email="admin@breach-tests.local")
    monkeypatch.setattr(
        "core.utils.get_respondent_scoped_folder_ids", lambda user: {root.id}
    )
    assert get_summary_trends(admin) is None


@pytest.mark.django_db
def test_attention_counts_match_their_list_filters(admin_client, domain):  # noqa: F811
    from django.utils import timezone

    from core.models import Evidence, RiskAcceptance, SecurityException, Vulnerability
    from privacy.models import RightRequest
    from tprm.models import Contract

    today = date.today()
    past, ahead = today - timedelta(days=3), today + timedelta(days=10)
    far = today + timedelta(days=90)

    late = Incident.objects.create(
        name="late",
        folder=domain,
        nis2_significant=True,
        reported_at=timezone.now() - timedelta(days=4),
    )
    Incident.objects.create(
        name="fresh",
        folder=domain,
        nis2_significant=True,
        reported_at=timezone.now() - timedelta(hours=1),
    )
    Incident.objects.create(
        name="dismissed",
        folder=domain,
        nis2_significant=True,
        reported_at=timezone.now() - timedelta(days=4),
        status=Incident.Status.DISMISSED,
    )
    Vulnerability.objects.create(name="late", folder=domain, due_date=past)
    Vulnerability.objects.create(
        name="fixed", folder=domain, due_date=past, status=Vulnerability.Status.FIXED
    )
    RightRequest.objects.create(
        name="due", folder=domain, requested_on=past, due_date=ahead - timedelta(days=5)
    )
    RightRequest.objects.create(
        name="later", folder=domain, requested_on=past, due_date=far
    )
    RightRequest.objects.create(
        name="done", folder=domain, requested_on=past, due_date=past, status="done"
    )
    RiskAcceptance.objects.create(
        name="lapsed", folder=domain, state="accepted", expiry_date=past
    )
    RiskAcceptance.objects.create(
        name="valid", folder=domain, state="accepted", expiry_date=far
    )
    SecurityException.objects.create(
        name="lapsed",
        folder=domain,
        status=SecurityException.Status.APPROVED,
        expiration_date=past,
    )
    SecurityException.objects.create(
        name="ended",
        folder=domain,
        status=SecurityException.Status.EXPIRED,
        expiration_date=past,
    )
    _scenarios(domain, RISK_MATRIX_JSON_DEFINITION, [])
    RiskAssessment.objects.update(due_date=past)
    Evidence.objects.create(name="soon", folder=domain, expiry_date=ahead)
    Evidence.objects.create(name="later", folder=domain, expiry_date=far)
    Contract.objects.create(
        name="ending", folder=domain, status=Contract.Status.ACTIVE, end_date=ahead
    )
    Contract.objects.create(name="draft", folder=domain, end_date=ahead)

    data = admin_client.get("/api/get_metrics/").json()["results"]
    assert data["operations"]["nis2_overdue_incidents"] == 1
    assert data["operations"]["overdue_vulnerabilities"] == 1
    assert data["privacy"]["right_requests_due"] == 1
    assert data["risk"]["expired_acceptances"] == 1
    assert data["risk"]["expired_exceptions"] == 1
    assert data["risk"]["overdue_assessments"] == 1
    assert data["compliance"]["expiring_evidences"] == 1
    assert data["compliance"]["evidences_to_review"] == 0
    assert data["compliance"]["overdue_audits"] == 0
    assert data["third_party"] == {"overdue_assessments": 0, "ending_contracts": 1}

    # The briefing rows link to these lists: each must show what was counted.
    def listed(url):
        return [r["name"] for r in admin_client.get(url).json()["results"]]

    soon = ahead + timedelta(days=20)
    assert listed("/api/incidents/?nis2_overdue=true") == [late.name]
    assert listed("/api/vulnerabilities/?state=overdue") == ["late"]
    assert listed(
        f"/api/privacy/right-requests/?due_date__lte={today + timedelta(days=7)}&status=new&status=in_progress&status=on_hold"
    ) == ["due"]
    assert listed(f"/api/risk-acceptances/?state=accepted&expiry_date__lt={today}") == [
        "lapsed"
    ]
    assert listed(
        f"/api/security-exceptions/?status=approved&expiration_date__lt={today}"
    ) == ["lapsed"]
    assert listed(
        f"/api/evidences/?expiry_date__gte={today}&expiry_date__lte={soon}"
    ) == ["soon"]
    assert listed(
        f"/api/contracts/?status=active&end_date__gte={today}&end_date__lte={soon}"
    ) == ["ending"]


@pytest.mark.django_db
def test_deprecated_items_and_their_children_are_left_out(admin_client, domain):  # noqa: F811
    from core.models import Assessment
    from metrology.models import BuiltinMetricSample

    past = date.today() - timedelta(days=3)
    for status in ("to_do", "deprecated", "--"):
        AppliedControl.objects.create(
            name=status, folder=domain, status=status, priority=1, eta=past
        )
    _scenarios(domain, RISK_MATRIX_JSON_DEFINITION, [(2, 0)])
    retired = RiskAssessment.objects.get()
    retired.status = Assessment.Status.DEPRECATED
    retired.save()
    five = copy.deepcopy(RISK_MATRIX_JSON_DEFINITION)
    five["risk"] = [dict(five["risk"][0], abbreviation=str(i)) for i in range(5)]
    _scenarios(domain, five, [(4, 2)])
    old = FindingsAssessment.objects.create(
        name="old", folder=domain, status=Assessment.Status.DEPRECATED
    )
    live = FindingsAssessment.objects.create(name="live", folder=domain)
    Finding.objects.create(name="in old", folder=domain, findings_assessment=old)
    Finding.objects.create(name="in live", folder=domain, findings_assessment=live)
    Finding.objects.create(name="unbound", folder=domain)

    data = admin_client.get("/api/get_metrics/").json()["results"]
    assert data["controls"]["eta_missed"] == 2  # unset status still counts
    assert data["controls"]["p1"] == 2
    assert data["controls"]["total"] == 3
    assert data["risk"]["scenarios"] == 1
    assert data["risk"]["assessments"] == 1
    assert data["risk"]["high_current"] == 1
    assert data["operations"]["open_findings"] == 2

    snapshot = BuiltinMetricSample.compute_metrics(Folder.get_root_folder())
    assert snapshot["controls_eta_missed"] == 2
    assert snapshot["controls_p1_pending"] == 2
    assert snapshot["total_risk_scenarios"] == 1
    assert snapshot["findings_open"] == 2

    def listed(url):
        return sorted(r["name"] for r in admin_client.get(url).json()["results"])

    assert listed("/api/findings/?deprecated_assessment=false") == [
        "in live",
        "unbound",
    ]
    assert listed("/api/findings/?deprecated_assessment=true") == ["in old"]
    assert len(listed("/api/risk-scenarios/?deprecated_assessment=false")) == 1
    assert (
        admin_client.get(
            "/api/requirement-assessments/?deprecated_assessment=false"
        ).status_code
        == 200
    )
