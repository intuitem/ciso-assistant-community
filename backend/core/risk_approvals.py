"""Scenario-level decisions using the validation flow event trail.

Snapshots are semantic: changing a label unrelated to the decision does not
invalidate it. Plans and existing controls are captured, not merely linked.
No decision changes a scenario's treatment option or locks its whole study.
"""

import json

from django.contrib.auth.models import Permission
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.models import Actor, FlowEvent, RiskScenario, ValidationFlow
from global_settings.utils import ff_is_enabled
from iam.models import RoleAssignment, User


def risk_approvals_enabled():
    """Return whether both flags required by risk approvals are enabled."""
    return ff_is_enabled("validation_flows") and ff_is_enabled("risk_owner_approvals")


def _require_risk_approvals_enabled():
    """Reject risk-approval writes while the optional workflow is disabled."""
    if not risk_approvals_enabled():
        raise PermissionDenied("riskApprovalFeatureDisabled")


def owner_can_approve(scenario, user):
    """Check named ownership, object visibility and approval permission."""
    if not user or not user.is_active:
        return False
    scenario_owner_ids = {actor.pk for actor in scenario.owner.all()}
    return (
        bool(scenario_owner_ids & {actor.pk for actor in Actor.get_all_for_user(user)})
        and RoleAssignment.is_object_readable(user, RiskScenario, scenario.pk)
        and RoleAssignment.is_access_allowed(
            user,
            Permission.objects.get(codename="change_validationflow"),
            scenario.folder,
        )
    )


def management_can_accept(scenario, user):
    """Check access and the existing risk-acceptance approval permission."""
    if not user or not user.is_active:
        return False
    return RoleAssignment.is_object_readable(user, RiskScenario, scenario.pk) and (
        RoleAssignment.is_access_allowed(
            user,
            Permission.objects.get(codename="approve_riskacceptance"),
            scenario.folder,
        )
    )


def residual_risk_above_tolerance(scenario):
    """Return whether a rated residual risk exceeds a configured tolerance."""
    tolerance = scenario.risk_assessment.risk_tolerance
    return tolerance >= 0 and scenario.residual_level > tolerance


def approval_candidates(scenario):
    """Return active named users allowed to approve the scenario."""
    # Resolve teams and entity representatives through the application's actor
    # rules. The actual decision still belongs to one named, authorised user.
    return [
        {"id": str(user.pk), "email": user.email, "name": str(user)}
        for user in User.objects.filter(is_active=True).order_by("email")
        if owner_can_approve(scenario, user)
    ]


def management_approval_candidates(scenario):
    """Return users authorised to accept an above-tolerance residual risk."""
    return [
        {"id": str(user.pk), "email": user.email, "name": str(user)}
        for user in User.objects.filter(is_active=True).order_by("email")
        if management_can_accept(scenario, user)
    ]


def _values(obj, fields):
    """Copy decision-relevant model fields into a serialisable mapping."""
    return {field: getattr(obj, field) for field in fields}


def _controls(manager, planned=False):
    """Capture control content while ignoring progress on planned controls."""
    return [
        {
            **_values(
                control,
                ["name", "description", "eta", "start_date"]
                + ([] if planned else ["status"]),
            ),
            "id": str(control.pk),
            "owners": sorted(str(owner.pk) for owner in control.owner.all()),
            "owner_names": [
                str(owner)
                for owner in sorted(control.owner.all(), key=lambda item: item.pk)
            ],
        }
        for control in sorted(manager.all(), key=lambda item: item.pk)
    ]


def snapshot(scenario, stage):
    """Build the semantic scenario state covered by an approval request."""
    data = {
        "scenario": {
            "id": str(scenario.pk),
            **_values(scenario, ["ref_id", "name", "description", "justification"]),
        },
        "folder": str(scenario.folder_id),
        "study": str(scenario.risk_assessment_id),
        "matrix": scenario.risk_assessment.risk_matrix.json_definition,
        "owners": sorted(str(owner.pk) for owner in scenario.owner.all()),
        "assets": [
            {"id": str(asset.pk), "name": asset.name, "description": asset.description}
            for asset in sorted(scenario.assets.all(), key=lambda item: item.pk)
        ],
        "threats": sorted(str(threat.pk) for threat in scenario.threats.all()),
        "vulnerabilities": sorted(
            str(vulnerability.pk) for vulnerability in scenario.vulnerabilities.all()
        ),
        "assessment": _values(
            scenario,
            [
                "inherent_proba",
                "inherent_impact",
                "inherent_level",
                "current_proba",
                "current_impact",
                "current_level",
                "strength_of_knowledge",
                "existing_controls",
            ],
        ),
        "existing_controls": _controls(scenario.existing_applied_controls),
    }
    if stage in ("treatment", "residual_acceptance"):
        data["treatment"] = _values(
            scenario,
            ["treatment", "residual_proba", "residual_impact", "residual_level"],
        )
        data["planned_controls"] = _controls(scenario.applied_controls, planned=True)
        data["risk_governance"] = {
            "risk_tolerance": scenario.risk_assessment.risk_tolerance,
            "residual_risk_above_tolerance": residual_risk_above_tolerance(scenario),
        }
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def is_current(flow, scenario=None):
    """Check that content, authority and prerequisite approval still match."""
    if not flow.risk_scenario_id or not flow.risk_snapshot:
        return False
    if scenario is None:
        # Callers may retain a flow instance while its scenario is edited elsewhere.
        # Compare against persisted content, never the FK's stale instance cache.
        scenario = RiskScenario.objects.select_related(
            "risk_assessment__risk_matrix"
        ).get(pk=flow.risk_scenario_id)
    authorised = (
        management_can_accept(scenario, flow.approver)
        if flow.risk_approval_stage == "residual_acceptance"
        else owner_can_approve(scenario, flow.approver)
    )
    if not authorised:
        return False
    if flow.risk_snapshot.get("content") != snapshot(
        scenario, flow.risk_approval_stage
    ):
        return False
    prerequisite = {
        "treatment": ("assessment_approval", "assessment"),
        "residual_acceptance": ("treatment_approval", "treatment"),
    }.get(flow.risk_approval_stage)
    if prerequisite:
        snapshot_key, stage = prerequisite
        prior = ValidationFlow.objects.filter(
            pk=flow.risk_snapshot.get(snapshot_key),
            risk_scenario=scenario,
            risk_approval_stage=stage,
            status="accepted",
        ).first()
        return bool(prior and is_current(prior, scenario=scenario))
    return True


def approval_summary(scenario):
    """Return the auditable current state of every approval stage for a scenario."""
    flows = sorted(
        scenario.risk_approvals.all(), key=lambda flow: flow.created_at, reverse=True
    )

    def stage_status(stage):
        matching = [flow for flow in flows if flow.risk_approval_stage == stage]
        for flow in matching:
            if flow.status in (
                "accepted",
                "submitted",
                "change_requested",
            ) and is_current(flow, scenario=scenario):
                return flow.status
        if any(
            flow.status in ("accepted", "submitted", "change_requested")
            for flow in matching
        ):
            return "outdated"
        return matching[0].status if matching else "not_requested"

    assessment = stage_status("assessment")
    treatment = stage_status("treatment")
    tolerance = scenario.risk_assessment.risk_tolerance
    if tolerance < 0:
        residual_acceptance = "tolerance_required"
    elif not residual_risk_above_tolerance(scenario):
        residual_acceptance = "not_required"
    elif treatment != "accepted":
        residual_acceptance = "waiting_for_treatment"
    else:
        residual_acceptance = stage_status("residual_acceptance")

    return {
        "assessment": assessment,
        "treatment": treatment,
        "residual_acceptance": residual_acceptance,
        "complete": treatment == "accepted"
        and residual_acceptance in ("accepted", "not_required"),
    }


def capture(scenario, stage, approver):
    """Validate a request and capture its immutable decision state."""
    if stage == "residual_acceptance":
        if not management_can_accept(scenario, approver):
            raise ValidationError({"approver": "riskApprovalManagementRequired"})
    elif not owner_can_approve(scenario, approver):
        raise ValidationError({"approver": "riskApprovalOwnerRequired"})
    if scenario.current_proba < 0 or scenario.current_impact < 0:
        raise ValidationError("riskApprovalRatingRequired")
    data = {"content": snapshot(scenario, stage)}
    if stage in ("treatment", "residual_acceptance"):
        if scenario.risk_assessment.risk_tolerance < 0:
            raise ValidationError("riskApprovalToleranceRequired")
        if (
            scenario.treatment in ("open", "cancelled")
            or min(scenario.residual_proba, scenario.residual_impact) < 0
        ):
            raise ValidationError("riskApprovalTreatmentRequired")
        prerequisite_stage = "assessment" if stage == "treatment" else "treatment"
        prior = next(
            (
                flow
                for flow in scenario.risk_approvals.filter(
                    risk_approval_stage=prerequisite_stage, status="accepted"
                ).order_by("-created_at")
                if is_current(flow)
            ),
            None,
        )
        if prior is None:
            error = (
                "riskApprovalAssessmentFirst"
                if stage == "treatment"
                else "riskApprovalTreatmentFirst"
            )
            raise ValidationError(error)
        if stage == "residual_acceptance":
            if not residual_risk_above_tolerance(scenario):
                raise ValidationError("riskApprovalManagementNotRequired")
            data["treatment_approval"] = str(prior.pk)
        else:
            data["assessment_approval"] = str(prior.pk)
    return data


@transaction.atomic
def create_approval(data, user):
    """Create a locked risk-approval request and its initial history event."""
    _require_risk_approvals_enabled()
    data = data.copy()
    scenario = RiskScenario.objects.select_for_update().get(pk=data["risk_scenario"].pk)
    if not RoleAssignment.is_object_readable(user, RiskScenario, scenario.pk):
        raise PermissionDenied()
    if data["folder"].pk != scenario.folder_id:
        raise ValidationError({"folder": "riskApprovalSameDomain"})
    stage = data.get("risk_approval_stage")
    if stage not in ValidationFlow.RiskApprovalStage.values:
        raise ValidationError({"risk_approval_stage": "riskApprovalStageRequired"})
    # A risk decision must not silently lock another bundled object.
    for field in ValidationFlow._meta.many_to_many:
        if data.pop(field.name, None):
            raise ValidationError("riskApprovalSingleScenario")
    data.pop("confirm_residual_risk", None)
    notes = data.pop("event_notes", None) or data.get("request_notes")
    data["risk_snapshot"] = capture(scenario, stage, data.get("approver"))
    data["requester"] = user
    flow = ValidationFlow.objects.create(**data)
    FlowEvent.objects.create(
        validation_flow=flow,
        folder=flow.folder,
        event_actor=user,
        event_type=flow.status,
        event_notes=notes,
        risk_snapshot=flow.risk_snapshot,
    )
    _notify_after_commit(flow, created=True)
    return flow


@transaction.atomic
def update_approval(flow, data, user):
    """Apply one authorised state transition to a locked approval request."""
    _require_risk_approvals_enabled()
    flow = ValidationFlow.objects.select_for_update().get(pk=flow.pk)
    allowed = {"status", "event_notes", "confirm_residual_risk"}
    if set(data) - allowed or "status" not in data:
        raise ValidationError("riskApprovalImmutable")
    old, new = flow.status, data["status"]
    transitions = {
        "submitted": {"accepted", "rejected", "change_requested", "dropped"},
        "accepted": {"revoked"},
        "change_requested": {"submitted", "dropped"},
    }
    if new not in transitions.get(old, set()):
        raise ValidationError("riskApprovalInvalidTransition")
    authorised = user.pk == flow.approver_id
    if old == "change_requested":
        authorised = user.pk == flow.requester_id
    elif old == "submitted" and new == "dropped":
        authorised = user.pk in (flow.requester_id, flow.approver_id)
    if not authorised:
        raise PermissionDenied("validationOnlyApproverCanModify")
    scenario = RiskScenario.objects.select_for_update().get(pk=flow.risk_scenario_id)
    flow.risk_scenario = scenario
    residual_accepted = False
    if new == "accepted":
        if flow.validation_deadline and flow.validation_deadline < timezone.localdate():
            raise ValidationError("riskApprovalDeadlinePassed")
        if not is_current(flow):
            raise ValidationError("riskApprovalStale")
        # Within tolerance, the approved treatment completes the workflow
        # automatically. Only an above-tolerance management decision records an
        # explicit residual-risk acceptance.
        residual_accepted = flow.risk_approval_stage == "residual_acceptance"
        if residual_accepted and data.get("confirm_residual_risk") is not True:
            raise ValidationError("riskApprovalResidualConfirmation")
    elif new == "submitted":
        flow.risk_snapshot = capture(scenario, flow.risk_approval_stage, flow.approver)
    flow.status = new
    flow.save(update_fields=["status", "risk_snapshot", "updated_at"])
    FlowEvent.objects.create(
        validation_flow=flow,
        folder=flow.folder,
        event_actor=user,
        event_type=new,
        event_notes=data.get("event_notes"),
        risk_snapshot=flow.risk_snapshot,
        residual_risk_accepted=residual_accepted,
    )
    _notify_after_commit(flow, actor=user)
    return flow


def _notify_after_commit(flow, created=False, actor=None):
    """Send notifications after commit without affecting saved decisions."""

    def send():
        import structlog

        from core.tasks import (
            send_validation_flow_created_notification,
            send_validation_flow_updated_notification,
        )

        try:
            if created:
                send_validation_flow_created_notification(flow)
            else:
                recipient = (
                    flow.requester if actor.pk == flow.approver_id else flow.approver
                )
                if recipient and recipient.email:
                    send_validation_flow_updated_notification(
                        flow.pk,
                        recipient.email,
                        flow.get_status_display(),
                        str(actor),
                        flow.last_event_notes,
                    )
        # A notification backend failure must not roll back the recorded request.
        except Exception:  # noqa: BLE001
            structlog.get_logger(__name__).exception(
                "Risk approval notification failed"
            )

    transaction.on_commit(send)
