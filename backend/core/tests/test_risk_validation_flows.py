"""Focused coverage for risk-owner decisions in the generic validation flow."""

from types import SimpleNamespace

import pytest
from iam.models import Folder, User
from rest_framework import serializers
from test_fixtures import RISK_MATRIX_JSON_DEFINITION

from core.models import AppliedControl, RiskAssessment, RiskMatrix, RiskScenario
from core.serializers import RiskScenarioReadSerializer, ValidationFlowWriteSerializer


@pytest.fixture
def risk_case(db):
    folder = Folder.objects.create(
        name="Risk validation test", parent_folder=Folder.get_root_folder()
    )
    matrix = RiskMatrix.objects.create(
        name="Matrix", folder=folder, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    assessment = RiskAssessment.objects.create(
        name="Assessment",
        folder=folder,
        risk_matrix=matrix,
        risk_tolerance=1,
    )
    scenario = RiskScenario.objects.create(
        ref_id="RISK-001",
        name="Service outage",
        folder=folder,
        risk_assessment=assessment,
        current_proba=2,
        current_impact=2,
        residual_proba=1,
        residual_impact=1,
        treatment="mitigate",
    )
    owner = User.objects.create_superuser(email="owner@example.test")
    requester = User.objects.create_superuser(email="requester@example.test")
    outsider = User.objects.create_superuser(email="outsider@example.test")
    scenario.owner.add(owner.actor)
    return SimpleNamespace(
        folder=folder,
        assessment=assessment,
        scenario=scenario,
        owner=owner,
        requester=requester,
        outsider=outsider,
    )


def create_flow(case, approver=None, scenarios=None, **overrides):
    scenarios = scenarios or [case.scenario]
    data = {
        "folder": str(case.folder.pk),
        "risk_scenarios": [str(scenario.pk) for scenario in scenarios],
        "approver": str((approver or case.owner).pk),
    }
    data.update(overrides)
    serializer = ValidationFlowWriteSerializer(
        data=data,
        context={"request": SimpleNamespace(user=case.requester)},
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def accept_flow(case, flow):
    serializer = ValidationFlowWriteSerializer(
        flow,
        data={"status": "accepted"},
        partial=True,
        context={"request": SimpleNamespace(user=case.owner)},
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save()


@pytest.mark.django_db
def test_owner_can_approve_treatment_and_residual_risk(risk_case, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "core.tasks.send_validation_flow_created_notification",
        lambda flow: sent.append(flow.pk),
    )

    flow = create_flow(risk_case)
    assert flow.subject == "Risk treatment and residual risk — RISK-001"
    assert list(flow.risk_scenarios.all()) == [risk_case.scenario]
    assert flow.events.first().event_type == "submitted"
    assert sent == [flow.pk]

    flow = accept_flow(risk_case, flow)
    assert flow.status == "accepted"
    assert flow.events.first().event_actor == risk_case.owner
    assert not flow.is_stale


@pytest.mark.django_db
def test_non_owner_cannot_be_selected_as_risk_approver(risk_case):
    with pytest.raises(
        serializers.ValidationError, match="riskValidationOwnerRequired"
    ):
        create_flow(risk_case, approver=risk_case.outsider)


@pytest.mark.django_db
def test_same_owner_can_approve_multiple_risks(risk_case):
    second_scenario = RiskScenario.objects.create(
        ref_id="RISK-002",
        name="Second service outage",
        folder=risk_case.folder,
        risk_assessment=risk_case.assessment,
        current_proba=2,
        current_impact=2,
        residual_proba=1,
        residual_impact=1,
        treatment="mitigate",
    )
    second_scenario.owner.add(risk_case.owner.actor)

    flow = create_flow(
        risk_case,
        scenarios=[risk_case.scenario, second_scenario],
    )

    assert set(flow.risk_scenarios.all()) == {
        risk_case.scenario,
        second_scenario,
    }
    assert flow.subject == "Risk treatment and residual risk — RISK-001, RISK-002"


@pytest.mark.django_db
def test_incomplete_risk_cannot_be_submitted(risk_case):
    risk_case.scenario.residual_proba = -1
    risk_case.scenario.save()

    with pytest.raises(
        serializers.ValidationError, match="riskValidationTreatmentRequired"
    ):
        create_flow(risk_case)


@pytest.mark.django_db
def test_changed_risk_is_stale_and_cannot_be_approved(risk_case):
    flow = create_flow(risk_case)
    risk_case.scenario.name = "Changed service outage"
    risk_case.scenario.save()
    flow.refresh_from_db()

    assert flow.is_stale
    serializer = ValidationFlowWriteSerializer(
        flow,
        data={"status": "accepted"},
        partial=True,
        context={"request": SimpleNamespace(user=risk_case.owner)},
    )
    with pytest.raises(serializers.ValidationError, match="riskValidationOutdated"):
        serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
def test_control_change_marks_request_stale(risk_case):
    flow = create_flow(risk_case)
    control = AppliedControl.objects.create(
        name="Recovery plan", folder=risk_case.folder, status="to_do"
    )
    risk_case.scenario.applied_controls.add(control)
    flow.refresh_from_db()

    assert flow.is_stale


@pytest.mark.django_db
def test_risk_summary_uses_residual_tolerance_and_latest_flow(risk_case):
    serializer = RiskScenarioReadSerializer()
    assert (
        serializer.get_risk_owner_validation_status(risk_case.scenario)
        == "notRequested"
    )
    assert serializer.get_residual_above_tolerance(risk_case.scenario) == "NO"

    flow = create_flow(risk_case)
    assert (
        serializer.get_risk_owner_validation_status(risk_case.scenario) == "submitted"
    )

    risk_case.assessment.risk_tolerance = 0
    risk_case.assessment.save()
    risk_case.scenario.refresh_from_db()
    assert serializer.get_residual_above_tolerance(risk_case.scenario) == "YES"
    assert flow.is_stale
