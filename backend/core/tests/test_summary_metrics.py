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
    _scenarios(domain, five, [(4, 2), (3, 3), (2, 0)])

    qs = RiskScenario.objects.all()
    assert count_top_risk_levels(qs, "current_level") == 3
    assert count_top_risk_levels(qs, "residual_level") == 1


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
    template = TaskTemplate.objects.create(name="t", folder=domain)
    yesterday = date.today() - timedelta(days=1)
    TaskNode.objects.create(task_template=template, folder=domain, due_date=yesterday)
    TaskNode.objects.create(
        task_template=template,
        folder=domain,
        due_date=yesterday - timedelta(days=1),
        status="completed",
    )
    # Overdue but outside the 30-day window: only in the total.
    TaskNode.objects.create(
        task_template=template,
        folder=domain,
        due_date=date.today() - timedelta(days=45),
    )

    res = admin_client.get("/api/get_metrics/")
    assert res.status_code == 200
    data = res.json()["results"]
    assert data["controls"]["no_status"] == 1
    assert data["risk"]["high_current"] == 0
    assert data["operations"] == {
        "open_incidents": 1,
        "open_findings": 1,
        "overdue_tasks": 1,
        "overdue_tasks_total": 2,
    }


@pytest.mark.django_db
def test_top_level_filter_matches_the_count(admin_client, domain):  # noqa: F811
    _scenarios(domain, RISK_MATRIX_JSON_DEFINITION, [(2, 0), (1, 2), (-1, -1)])

    current = admin_client.get("/api/risk-scenarios/?top_level=current").json()
    residual = admin_client.get("/api/risk-scenarios/?top_level=residual").json()
    assert [s["name"] for s in current["results"]] == ["s0"]
    assert [s["name"] for s in residual["results"]] == ["s1"]
