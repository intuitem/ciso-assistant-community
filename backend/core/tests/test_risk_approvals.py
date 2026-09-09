"""Risk-owner decisions must be scoped, versioned and independent of treatment choice."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from core.models import (
    AppliedControl,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    ValidationFlow,
)
from core.risk_approvals import (
    approval_candidates,
    approval_summary,
    is_current,
    management_approval_candidates,
)
from core.serializers import ValidationFlowReadSerializer, ValidationFlowWriteSerializer
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import Folder, User
from test_fixtures import RISK_MATRIX_JSON_DEFINITION


@pytest.fixture(autouse=True)
def enable_risk_approvals(db):
    flags, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    flags.value = {
        **(flags.value or {}),
        "validation_flows": True,
        "risk_owner_approvals": True,
    }
    flags.save(update_fields=["value"])
    clear_feature_flags_cache()
    yield
    clear_feature_flags_cache()


@pytest.fixture
def setup_risk(db):
    folder = Folder.objects.create(
        name="Risk approval test", parent_folder=Folder.get_root_folder()
    )
    matrix = RiskMatrix.objects.create(
        name="Matrix", folder=folder, json_definition=RISK_MATRIX_JSON_DEFINITION
    )
    study = RiskAssessment.objects.create(
        name="Study", folder=folder, risk_matrix=matrix, risk_tolerance=1
    )
    scenario = RiskScenario.objects.create(
        name="Service outage",
        folder=folder,
        risk_assessment=study,
        current_proba=2,
        current_impact=2,
        residual_proba=1,
        residual_impact=1,
        treatment="mitigate",
    )
    owner = User.objects.create_superuser(email="owner@example.test")
    requester = User.objects.create_superuser(email="requester@example.test")
    scenario.owner.add(owner.actor)
    control = AppliedControl.objects.create(
        name="Recovery plan", folder=folder, status="to_do"
    )
    scenario.applied_controls.add(control)
    return SimpleNamespace(
        folder=folder,
        study=study,
        scenario=scenario,
        owner=owner,
        requester=requester,
        control=control,
    )


def create(risk, stage="assessment", **overrides):
    data = {
        "folder": str(risk.folder.pk),
        "risk_scenario": str(risk.scenario.pk),
        "risk_approval_stage": stage,
        "approver": str(risk.owner.pk),
    } | overrides
    serializer = ValidationFlowWriteSerializer(
        data=data, context={"request": SimpleNamespace(user=risk.requester)}
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def decide(flow, user, status="accepted", **extras):
    serializer = ValidationFlowWriteSerializer(
        flow,
        data={"status": status} | extras,
        partial=True,
        context={"request": SimpleNamespace(user=user)},
    )
    serializer.is_valid(raise_exception=True)
    return serializer.save()


@pytest.mark.django_db
def test_within_tolerance_treatment_completes_without_separate_acceptance(setup_risk):
    r = setup_risk
    r.study.risk_tolerance = r.scenario.residual_level
    r.study.save(update_fields=["risk_tolerance"])
    rating = decide(create(r), r.owner)
    flow = create(r, "treatment")
    flow = decide(flow, r.owner)
    r.scenario.refresh_from_db()
    r.study.refresh_from_db()
    assert r.scenario.treatment == "mitigate"
    assert not r.study.is_locked
    assert is_current(flow) and is_current(rating)
    assert not flow.events.first().residual_risk_accepted
    assert flow.events.first().risk_snapshot == flow.risk_snapshot
    with pytest.raises(ValidationError, match="riskApprovalManagementNotRequired"):
        create(r, "residual_acceptance", approver=str(r.requester.pk))


@pytest.mark.django_db
def test_approval_summary_tracks_each_stage_and_completion(setup_risk):
    r = setup_risk
    summary = approval_summary(r.scenario)
    assert summary == {
        "assessment": "not_requested",
        "treatment": "not_requested",
        "residual_acceptance": "not_required",
        "complete": False,
    }

    assessment = create(r)
    assert approval_summary(r.scenario)["assessment"] == "submitted"
    decide(assessment, r.owner)
    treatment = create(r, "treatment")
    assert approval_summary(r.scenario)["treatment"] == "submitted"
    decide(treatment, r.owner)
    assert approval_summary(r.scenario) == {
        "assessment": "accepted",
        "treatment": "accepted",
        "residual_acceptance": "not_required",
        "complete": True,
    }


@pytest.mark.django_db
def test_above_tolerance_summary_waits_for_management(setup_risk):
    r = setup_risk
    r.study.risk_tolerance = 0
    r.study.save(update_fields=["risk_tolerance"])
    assert (
        approval_summary(r.scenario)["residual_acceptance"] == "waiting_for_treatment"
    )
    decide(create(r), r.owner)
    decide(create(r, "treatment"), r.owner)
    assert approval_summary(r.scenario)["residual_acceptance"] == "not_requested"


@pytest.mark.django_db
def test_risk_approval_creation_enqueues_notification(
    setup_risk, django_capture_on_commit_callbacks, monkeypatch
):
    sent = []
    monkeypatch.setattr(
        "core.tasks.send_validation_flow_created_notification",
        lambda flow: sent.append(flow.pk),
    )
    with django_capture_on_commit_callbacks(execute=True):
        flow = create(setup_risk)
    assert sent == [flow.pk]


@pytest.mark.django_db
def test_risk_approval_email_names_risk_and_requested_stage(setup_risk, monkeypatch):
    from core import tasks

    flow = create(setup_risk)
    rendered = {}

    monkeypatch.setattr(tasks, "check_email_configuration", lambda *args: True)
    monkeypatch.setattr("core.email_utils.get_locale_for_email", lambda email: "de")

    def capture_template(name, context, **kwargs):
        rendered.update(name=name, context=context, kwargs=kwargs)
        return {"subject": "subject", "body": "body"}

    monkeypatch.setattr("core.email_utils.render_email_template", capture_template)
    monkeypatch.setattr(tasks, "send_notification_email", lambda *args: None)
    tasks.send_validation_flow_created_notification.call_local(flow)

    assert rendered["name"] == "risk_approval_created"
    assert rendered["context"]["risk_ref_id"] == setup_risk.scenario.ref_id
    assert rendered["context"]["risk_name"] == setup_risk.scenario.name
    assert rendered["context"]["risk_approval_stage"] == "Einstufung"


@pytest.mark.django_db
def test_above_tolerance_requires_separate_management_acceptance(setup_risk):
    r = setup_risk
    r.study.risk_tolerance = 0
    r.study.save(update_fields=["risk_tolerance"])
    decide(create(r), r.owner)
    treatment = decide(create(r, "treatment"), r.owner)
    assert not treatment.events.first().residual_risk_accepted

    acceptance = create(r, "residual_acceptance", approver=str(r.requester.pk))
    with pytest.raises(ValidationError, match="riskApprovalResidualConfirmation"):
        decide(acceptance, r.requester)
    acceptance = decide(acceptance, r.requester, confirm_residual_risk=True)
    assert is_current(acceptance)
    assert acceptance.events.first().residual_risk_accepted
    r.scenario.refresh_from_db()
    assert r.scenario.treatment == "mitigate"


@pytest.mark.django_db
def test_above_tolerance_acceptance_requires_management_permission(setup_risk):
    r = setup_risk
    r.study.risk_tolerance = 0
    r.study.save(update_fields=["risk_tolerance"])
    decide(create(r), r.owner)
    decide(create(r, "treatment"), r.owner)
    ordinary_user = User.objects.create_user(email="ordinary@example.test")
    with pytest.raises(ValidationError, match="riskApprovalManagementRequired"):
        create(
            r,
            "residual_acceptance",
            approver=str(ordinary_user.pk),
        )
    assert str(ordinary_user.pk) not in [
        item["id"] for item in management_approval_candidates(r.scenario)
    ]
    assert str(r.requester.pk) in [
        item["id"] for item in management_approval_candidates(r.scenario)
    ]


@pytest.mark.django_db
def test_tolerance_change_invalidates_treatment_and_management_decisions(setup_risk):
    r = setup_risk
    r.study.risk_tolerance = 0
    r.study.save(update_fields=["risk_tolerance"])
    decide(create(r), r.owner)
    treatment = decide(create(r, "treatment"), r.owner)
    acceptance = decide(
        create(r, "residual_acceptance", approver=str(r.requester.pk)),
        r.requester,
        confirm_residual_risk=True,
    )
    r.study.risk_tolerance = r.scenario.residual_level
    r.study.save(update_fields=["risk_tolerance"])
    assert not is_current(treatment)
    assert not is_current(acceptance)


@pytest.mark.django_db
def test_treatment_requires_current_approved_assessment(setup_risk):
    with pytest.raises(ValidationError, match="riskApprovalAssessmentFirst"):
        create(setup_risk, "treatment")


@pytest.mark.django_db
def test_treatment_requires_configured_risk_tolerance(setup_risk):
    r = setup_risk
    decide(create(r), r.owner)
    r.study.risk_tolerance = -1
    r.study.save(update_fields=["risk_tolerance"])
    with pytest.raises(ValidationError, match="riskApprovalToleranceRequired"):
        create(r, "treatment")


@pytest.mark.django_db
def test_only_named_owner_can_decide_even_for_admin(setup_risk):
    r = setup_risk
    flow = create(r)
    with pytest.raises(PermissionDenied):
        decide(flow, r.requester)
    with pytest.raises(ValidationError, match="riskApprovalOwnerRequired"):
        create(r, approver=str(r.requester.pk))


@pytest.mark.django_db
def test_owner_without_domain_permission_cannot_be_selected(setup_risk):
    r = setup_risk
    owner = User.objects.create_user(email="no-permission@example.test")
    r.scenario.owner.add(owner.actor)
    with pytest.raises(ValidationError, match="riskApprovalOwnerRequired"):
        create(r, approver=str(owner.pk))
    assert str(owner.pk) not in [item["id"] for item in approval_candidates(r.scenario)]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,value",
    [
        ("current_impact", 1),
        ("justification", "New evidence"),
        ("description", "Changed scope"),
    ],
)
def test_changed_rating_cannot_be_approved(setup_risk, field, value):
    r = setup_risk
    flow = create(r)
    setattr(r.scenario, field, value)
    r.scenario.save()
    with pytest.raises(ValidationError, match="riskApprovalStale"):
        decide(flow, r.owner)


@pytest.mark.django_db
def test_resubmission_preserves_previous_version(setup_risk):
    r = setup_risk
    flow = create(r)
    first = flow.risk_snapshot
    flow = decide(flow, r.owner, "change_requested", event_notes="Review likelihood")
    r.scenario.current_proba = 1
    r.scenario.save()
    flow = decide(flow, r.requester, "submitted")
    assert flow.risk_snapshot != first
    assert flow.events.last().risk_snapshot == first
    assert decide(flow, r.owner).status == "accepted"


@pytest.mark.django_db
def test_changed_plan_invalidates_treatment_but_not_rating(setup_risk):
    r = setup_risk
    rating = decide(create(r), r.owner)
    treatment = decide(create(r, "treatment"), r.owner, confirm_residual_risk=True)
    r.control.eta = timezone.localdate() + timedelta(days=60)
    r.control.save()
    assert is_current(rating)
    assert not is_current(treatment)
    assert treatment.status == "accepted"  # historical decision retained


@pytest.mark.django_db
def test_planned_control_progress_does_not_invalidate_plan(setup_risk):
    r = setup_risk
    decide(create(r), r.owner)
    flow = decide(create(r, "treatment"), r.owner, confirm_residual_risk=True)
    r.control.status = "in_progress"
    r.control.save()
    assert is_current(flow)


@pytest.mark.django_db
def test_owner_removal_invalidates_approval(setup_risk):
    r = setup_risk
    flow = decide(create(r), r.owner)
    r.scenario.owner.clear()
    assert not is_current(flow)


@pytest.mark.django_db
def test_revoked_rating_invalidates_treatment(setup_risk):
    r = setup_risk
    rating = decide(create(r), r.owner)
    treatment = decide(create(r, "treatment"), r.owner, confirm_residual_risk=True)
    decide(rating, r.owner, "revoked")
    assert not is_current(treatment)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "change",
    [
        {"risk_scenario": None},
        {"risk_approval_stage": "treatment"},
        {"request_notes": "Different decision"},
        {"status": "accepted", "risk_scenario": None},
    ],
)
def test_submitted_request_cannot_be_repurposed(setup_risk, change):
    r = setup_risk
    flow = create(r)
    serializer = ValidationFlowWriteSerializer(
        flow,
        data=change,
        partial=True,
        context={"request": SimpleNamespace(user=r.owner)},
    )
    with pytest.raises(ValidationError, match="riskApprovalImmutable"):
        serializer.is_valid(raise_exception=True)
        serializer.save()


@pytest.mark.django_db
def test_cannot_bundle_risk_approval_with_study(setup_risk):
    r = setup_risk
    with pytest.raises(ValidationError, match="riskApprovalSingleScenario"):
        create(r, risk_assessments=[str(r.study.pk)])
    assert not r.scenario.risk_approvals.exists()


@pytest.mark.django_db
def test_cross_domain_request_rejected(setup_risk):
    r = setup_risk
    with pytest.raises(ValidationError, match="riskApprovalSameDomain"):
        create(r, folder=str(Folder.get_root_folder().pk))


@pytest.mark.django_db
def test_cannot_approve_twice_or_after_deadline(setup_risk):
    r = setup_risk
    flow = decide(create(r), r.owner)
    with pytest.raises(ValidationError, match="riskApprovalInvalidTransition"):
        decide(flow, r.owner)
    late = create(r, validation_deadline=str(timezone.localdate() - timedelta(days=1)))
    with pytest.raises(ValidationError, match="riskApprovalDeadlinePassed"):
        decide(late, r.owner)


@pytest.mark.django_db
def test_read_serializer_includes_current_state_and_history(setup_risk):
    r = setup_risk
    flow = decide(create(r), r.owner)
    data = ValidationFlowReadSerializer(
        flow, context={"request": SimpleNamespace(user=r.owner)}
    ).data
    assert data["risk_approval_current"] is True
    assert str(data["risk_scenario"]["id"]) == str(r.scenario.pk)
    assert len(data["events"]) == 2
    assert data["events"][0]["risk_snapshot"]


@pytest.mark.django_db
def test_existing_study_validation_still_locks_study(setup_risk):
    r = setup_risk
    serializer = ValidationFlowWriteSerializer(
        data={
            "folder": str(r.folder.pk),
            "approver": str(r.owner.pk),
            "risk_assessments": [str(r.study.pk)],
        },
        context={"request": SimpleNamespace(user=r.requester)},
    )
    serializer.is_valid(raise_exception=True)
    decide(serializer.save(), r.owner)
    r.study.refresh_from_db()
    assert r.study.is_locked


@pytest.mark.django_db
def test_api_create_filter_decide_and_preserve_history(setup_risk):
    r = setup_risk
    client = APIClient()
    client.force_authenticate(r.requester)
    response = client.post(
        "/api/validation-flows/",
        {
            "folder": str(r.folder.pk),
            "risk_scenario": str(r.scenario.pk),
            "risk_approval_stage": "assessment",
            "approver": str(r.owner.pk),
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    pk = response.data["id"]
    url = f"/api/validation-flows/{pk}/"
    assert client.patch(url, {"status": "accepted"}, format="json").status_code == 403
    client.force_authenticate(r.owner)
    assert client.patch(url, {"status": "accepted"}, format="json").status_code == 200
    result = client.get("/api/validation-flows/", {"risk_scenario": str(r.scenario.pk)})
    assert result.status_code == 200, result.data
    assert str(pk) in [str(flow["id"]) for flow in result.data["results"]]
    assert client.get(url).data["risk_approval_current"] is True
    assert client.delete(url).status_code == 400
    assert ValidationFlow.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_api_options_and_cross_domain_access(setup_risk):
    r = setup_risk
    client = APIClient()
    client.force_authenticate(r.requester)
    url = f"/api/risk-scenarios/{r.scenario.pk}/approval-options/"
    response = client.get(url)
    assert response.status_code == 200, response.data
    assert str(r.owner.pk) in [user["id"] for user in response.data["approvers"]]
    assert str(r.requester.pk) in [
        user["id"] for user in response.data["management_approvers"]
    ]
    assert response.data["residual_risk_above_tolerance"] is False
    assert response.data["risk_tolerance_configured"] is True
    outsider = User.objects.create_user(email="outsider@example.test")
    client.force_authenticate(outsider)
    assert client.get(url).status_code in (403, 404)
    assert client.post(
        "/api/validation-flows/",
        {
            "folder": str(r.folder.pk),
            "risk_scenario": str(r.scenario.pk),
            "risk_approval_stage": "assessment",
            "approver": str(r.owner.pk),
        },
        format="json",
    ).status_code in (400, 403)


@pytest.mark.parametrize(
    ("validation_flows", "risk_owner_approvals"),
    [(False, True), (True, False), (False, False)],
)
@pytest.mark.django_db
def test_feature_flags_block_new_requests_and_decisions_but_preserve_history(
    setup_risk, validation_flows, risk_owner_approvals
):
    r = setup_risk
    flow = create(r)
    flags = GlobalSettings.objects.get(name=GlobalSettings.Names.FEATURE_FLAGS)
    flags.value = {
        **flags.value,
        "validation_flows": validation_flows,
        "risk_owner_approvals": risk_owner_approvals,
    }
    flags.save(update_fields=["value"])
    clear_feature_flags_cache()

    with pytest.raises(PermissionDenied, match="riskApprovalFeatureDisabled"):
        create(r)
    with pytest.raises(PermissionDenied, match="riskApprovalFeatureDisabled"):
        decide(flow, r.owner)

    client = APIClient()
    client.force_authenticate(r.requester)
    options_url = f"/api/risk-scenarios/{r.scenario.pk}/approval-options/"
    assert client.get(options_url).status_code == 403
    assert (
        client.post(
            "/api/validation-flows/",
            {
                "folder": str(r.folder.pk),
                "risk_scenario": str(r.scenario.pk),
                "risk_approval_stage": "assessment",
                "approver": str(r.owner.pk),
            },
            format="json",
        ).status_code
        == 403
    )
    assert client.get(f"/api/validation-flows/{flow.pk}/").status_code == 200
    assert ValidationFlow.objects.filter(pk=flow.pk, status="submitted").exists()


@pytest.mark.django_db
def test_api_batch_cannot_reassign_or_delete_decision(setup_risk):
    r = setup_risk
    flow = decide(create(r), r.owner)
    client = APIClient()
    client.force_authenticate(r.owner)
    for payload in [
        {"action": "delete"},
        {"action": "change_field", "field": "approver", "value": str(r.requester.pk)},
    ]:
        response = client.post(
            "/api/validation-flows/batch-action/",
            {"ids": [str(flow.pk)]} | payload,
            format="json",
        )
        assert response.status_code in (200, 207, 400), response.data
        flow.refresh_from_db()
        assert flow.approver_id == r.owner.pk


@pytest.mark.django_db
def test_unrated_and_unselected_treatment_cannot_be_submitted(setup_risk):
    r = setup_risk
    r.scenario.current_proba = -1
    r.scenario.save()
    with pytest.raises(ValidationError, match="riskApprovalRatingRequired"):
        create(r)
    r.scenario.current_proba = 2
    r.scenario.save()
    decide(create(r), r.owner)
    r.scenario.treatment = "open"
    r.scenario.save()
    with pytest.raises(ValidationError, match="riskApprovalTreatmentRequired"):
        create(r, "treatment")
