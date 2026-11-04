"""Validation flows on a single risk scenario (and, the same way, a requirement)."""

import pytest

from core.models import (
    Perimeter,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    ValidationFlow,
)
from iam.models import Folder, User
from privacy.test_data_breach import admin_client, domain  # noqa: F401
from test_fixtures import RISK_MATRIX_JSON_DEFINITION


@pytest.mark.django_db
def test_flow_on_a_risk_scenario_is_filterable_and_listed(admin_client, domain):  # noqa: F811
    perimeter = Perimeter.objects.create(name="p", folder=domain)
    matrix = RiskMatrix.objects.create(
        name="m",
        json_definition=RISK_MATRIX_JSON_DEFINITION,
        folder=Folder.get_root_folder(),
    )
    assessment = RiskAssessment.objects.create(
        name="ra", perimeter=perimeter, risk_matrix=matrix, folder=domain
    )
    scenario = RiskScenario.objects.create(
        name="Ransomware", risk_assessment=assessment, folder=domain
    )
    other = RiskScenario.objects.create(
        name="Phishing", risk_assessment=assessment, folder=domain
    )
    approver = User.objects.create(email="approver@test.local")
    flow = ValidationFlow.objects.create(folder=domain, approver=approver)
    flow.risk_scenarios.add(scenario)

    res = admin_client.get(f"/api/validation-flows/?risk_scenarios={scenario.id}")
    assert res.status_code == 200
    (row,) = res.json()["results"]
    assert row["id"] == str(flow.id)
    assert [s["id"] for s in row["risk_scenarios"]] == [str(scenario.id)]
    assert "risk_scenarios" in row["linked_models"]

    res = admin_client.get(f"/api/validation-flows/?risk_scenarios={other.id}")
    assert res.json()["results"] == []

    assert "risk_scenarios" in flow.linked_models
