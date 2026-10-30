"""update_object: mostly about what it refuses. Results, scores, treatments
and approvals stay human."""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
    SecurityException,
)
from iam.models import Folder
from automation.workflows.actions import (
    UPDATABLE_MODELS,
    required_permissions,
    validate_update_config,
)
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowNode,
    WorkflowVersion,
)
from automation.workflows.validation import validate_graph
from automation.workflows.tests.helpers import publisher_user


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "source": source["id"],
        "target": target["id"],
        **kwargs,
    }


def make_domain(name, parent=None):
    return Folder.objects.create(
        name=name,
        parent_folder=parent or Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def update_flow(folder, config):
    workflow = Workflow.objects.create(name=f"Update {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    update = node(
        "action", label="Apply", action_config={"type": "update_object", **config}
    )
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [start, update, end],
            "edges": [edge(start, update), edge(update, end)],
        },
    )
    return version


def output(instance):
    return instance.node_outputs["apply"]


def make_requirement_assessment(domain):
    framework = Framework.objects.create(
        name="FW", urn=f"urn:test:{uuid.uuid4()}", folder=Folder.get_root_folder()
    )
    requirement = RequirementNode.objects.create(
        name="Req",
        urn=f"urn:test:{uuid.uuid4()}:r1",
        framework=framework,
        assessable=True,
        folder=Folder.get_root_folder(),
    )
    perimeter = Perimeter.objects.create(name="P", folder=domain)
    assessment = ComplianceAssessment.objects.create(
        name="Audit", framework=framework, perimeter=perimeter, folder=domain
    )
    return RequirementAssessment.objects.create(
        compliance_assessment=assessment,
        requirement=requirement,
        folder=domain,
        result="non_compliant",
        score=1,
        is_scored=True,
    )


@pytest.mark.django_db
class TestSimpleFieldWrites:
    def test_writes_whitelisted_fields(self):
        domain = make_domain("Writes")
        control = AppliedControl.objects.create(name="Patch", folder=domain)
        due = (timezone.localdate() + timedelta(days=30)).isoformat()
        version = update_flow(
            domain,
            {
                "model": "applied_control",
                "id": str(control.id),
                "fields": {"status": "in_progress", "eta": due, "priority": 1},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        control.refresh_from_db()
        assert control.status == "in_progress"
        assert control.eta.isoformat() == due
        assert control.priority == 1
        assert output(instance)["updated_fields"] == ["eta", "priority", "status"]
        assert output(instance)["object_id"] == str(control.id)

    def test_unlisted_fields_are_ignored_not_written(self):
        domain = make_domain("Ignored")
        control = AppliedControl.objects.create(name="Keep me", folder=domain)
        version = update_flow(
            domain,
            {
                "model": "applied_control",
                "id": str(control.id),
                "fields": {"name": "Renamed", "status": "active"},
            },
        )
        start_instance(version)
        control.refresh_from_db()
        # Identity is stable, so create_object's upsert keeps matching.
        assert control.name == "Keep me"
        assert control.status == "active"

    def test_empty_values_leave_the_column_alone(self):
        domain = make_domain("Empty")
        control = AppliedControl.objects.create(
            name="C", folder=domain, status="active"
        )
        version = update_flow(
            domain,
            {
                "model": "applied_control",
                "id": str(control.id),
                "fields": {"status": "", "description": "note"},
            },
        )
        start_instance(version)
        control.refresh_from_db()
        assert control.status == "active"
        assert control.description == "note"

    def test_target_id_is_templatable(self):
        domain = make_domain("Templated id")
        control = AppliedControl.objects.create(name="C", folder=domain)
        version = update_flow(
            domain,
            {
                "model": "applied_control",
                "id": "{{payload.object_id}}",
                "fields": {"status": "active"},
            },
        )
        start_instance(version, payload={"object_id": str(control.id)})
        control.refresh_from_db()
        assert control.status == "active"


@pytest.mark.django_db
class TestIntegrityGuardrail:
    """Record that time passed, attach work, never render the judgment."""

    def test_requirement_result_and_score_are_not_writable(self):
        domain = make_domain("Audit integrity")
        assessment = make_requirement_assessment(domain)
        version = update_flow(
            domain,
            {
                "model": "requirement_assessment",
                "id": str(assessment.id),
                "fields": {
                    "result": "compliant",
                    "score": 5,
                    "status": "in_progress",
                },
            },
        )
        instance = start_instance(version)
        assessment.refresh_from_db()
        assert assessment.result == "non_compliant"
        assert assessment.score == 1
        # Progress still moves: what a workflow may say is "work happened".
        assert assessment.status == "in_progress"
        assert instance.status == WorkflowInstance.Status.COMPLETED

    def test_a_value_outside_the_column_choices_is_refused(self):
        """save() enforces max_length and clean() but never choices."""
        domain = make_domain("Choices")
        control = AppliedControl.objects.create(name="C", folder=domain, status="to_do")
        version = update_flow(
            domain,
            {
                "model": "applied_control",
                "id": str(control.id),
                "fields": {"status": "banana"},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        control.refresh_from_db()
        assert control.status == "to_do"

    def test_incident_status_and_severity_are_not_writable(self):
        """Their TimelineEntry is written by IncidentViewSet.perform_update."""
        assert not {"status", "severity"} & set(UPDATABLE_MODELS["incident"].fields)

    def test_transition_guarded_models_are_not_updatable(self):
        """RiskAcceptance.set_state stamps revoked_at and reverts scenario
        treatments; ValidationFlow's transitions live in the write serializer
        with a FlowEvent per move. A column write would skip both."""
        assert "risk_acceptance" not in UPDATABLE_MODELS
        assert "validation_flow" not in UPDATABLE_MODELS

    def test_exception_may_expire_but_never_be_approved(self):
        domain = make_domain("Exception")
        exception = SecurityException.objects.create(name="SE", folder=domain)
        approve = update_flow(
            domain,
            {
                "model": "security_exception",
                "id": str(exception.id),
                "fields": {"status": "approved"},
            },
        )
        assert start_instance(approve).status == WorkflowInstance.Status.FAILED

        expire = update_flow(
            domain,
            {
                "model": "security_exception",
                "id": str(exception.id),
                "fields": {"status": "expired"},
            },
        )
        assert start_instance(expire).status == WorkflowInstance.Status.COMPLETED
        exception.refresh_from_db()
        assert exception.status == "expired"

    def test_evidence_may_expire_but_never_be_approved(self):
        domain = make_domain("Evidence review")
        evidence = Evidence.objects.create(name="Report", folder=domain)
        approve = update_flow(
            domain,
            {
                "model": "evidence",
                "id": str(evidence.id),
                "fields": {"status": "approved"},
            },
        )
        assert start_instance(approve).status == WorkflowInstance.Status.FAILED

        expire = update_flow(
            domain,
            {
                "model": "evidence",
                "id": str(evidence.id),
                "fields": {"status": "expired"},
            },
        )
        assert start_instance(expire).status == WorkflowInstance.Status.COMPLETED
        evidence.refresh_from_db()
        assert evidence.status == "expired"

    def test_risk_treatment_is_not_writable(self):
        assert "treatment" not in UPDATABLE_MODELS["risk_scenario"].fields
        assert not {"inherent_level", "current_level", "residual_level"} & set(
            UPDATABLE_MODELS["risk_scenario"].fields
        )

    def test_no_entry_may_write_name(self):
        assert not [key for key, e in UPDATABLE_MODELS.items() if "name" in e.fields]

    @pytest.mark.parametrize(
        "model,field",
        [
            # Cut from the first draft: a valuation, a narrative, a label, a
            # standing judgment. Widening the registry later is cheap;
            # narrowing it breaks published graphs, so re-adding needs a case.
            ("asset", "business_value"),
            ("entity", "is_active"),
            ("incident", "resolution"),
            ("compliance_assessment", "version"),
            ("risk_assessment", "version"),
            ("entity_assessment", "version"),
            ("risk_scenario", "existing_controls"),
        ],
    )
    def test_deliberately_unwritable_fields_stay_out(self, model, field):
        assert field not in UPDATABLE_MODELS[model].fields


@pytest.mark.django_db
class TestRelationWrites:
    def test_add_then_remove_links(self):
        domain = make_domain("Links")
        assessment = make_requirement_assessment(domain)
        first = AppliedControl.objects.create(name="C1", folder=domain)
        second = AppliedControl.objects.create(name="C2", folder=domain)
        add = update_flow(
            domain,
            {
                "model": "requirement_assessment",
                "id": str(assessment.id),
                "m2m": {
                    "applied_controls": {
                        "op": "add",
                        "values": f"{first.id},{second.id}",
                    }
                },
            },
        )
        instance = start_instance(add)
        assert output(instance)["relations"]["applied_controls"] == {
            "op": "add",
            "count": 2,
        }
        assert assessment.applied_controls.count() == 2

        remove = update_flow(
            domain,
            {
                "model": "requirement_assessment",
                "id": str(assessment.id),
                "m2m": {"applied_controls": {"op": "remove", "values": str(first.id)}},
            },
        )
        start_instance(remove)
        assert [c.name for c in assessment.applied_controls.all()] == ["C2"]

    def test_set_replaces_the_whole_relation(self):
        domain = make_domain("Replace")
        assessment = make_requirement_assessment(domain)
        old = Evidence.objects.create(name="Old", folder=domain)
        new = Evidence.objects.create(name="New", folder=domain)
        assessment.evidences.add(old)
        version = update_flow(
            domain,
            {
                "model": "requirement_assessment",
                "id": str(assessment.id),
                "m2m": {"evidences": {"op": "set", "values": [str(new.id)]}},
            },
        )
        start_instance(version)
        assert [e.name for e in assessment.evidences.all()] == ["New"]

    def test_values_may_come_from_an_upstream_node(self):
        domain = make_domain("Chained")
        assessment = make_requirement_assessment(domain)
        workflow = Workflow.objects.create(name="Create and link", folder=domain)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        create = node(
            "action",
            label="Make control",
            action_config={
                "type": "create_object",
                "model": "applied_control",
                "fields": {"name": "Remediation"},
            },
        )
        link = node(
            "action",
            label="Link it",
            action_config={
                "type": "update_object",
                "model": "requirement_assessment",
                "id": str(assessment.id),
                "m2m": {
                    "applied_controls": {
                        "op": "add",
                        "values": "{{nodes.make_control.created_object_id}}",
                    }
                },
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, create, link, end],
                "edges": [
                    edge(start, create),
                    edge(create, link),
                    edge(link, end),
                ],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        # The whole point: no more orphaned controls.
        assert [c.name for c in assessment.applied_controls.all()] == ["Remediation"]

    def test_unknown_relation_id_fails_the_node(self):
        domain = make_domain("Missing link")
        assessment = make_requirement_assessment(domain)
        version = update_flow(
            domain,
            {
                "model": "requirement_assessment",
                "id": str(assessment.id),
                "m2m": {"applied_controls": {"op": "add", "values": str(uuid.uuid4())}},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED

    def test_set_may_not_detach_an_out_of_scope_link(self):
        domain = make_domain("Displacing")
        elsewhere = make_domain("Elsewhere links")
        assessment = make_requirement_assessment(domain)
        foreign = AppliedControl.objects.create(name="Foreign", folder=elsewhere)
        mine = AppliedControl.objects.create(name="Mine", folder=domain)
        assessment.applied_controls.add(foreign)
        version = update_flow(
            domain,
            {
                "model": "requirement_assessment",
                "id": str(assessment.id),
                "m2m": {"applied_controls": {"op": "set", "values": str(mine.id)}},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert [c.name for c in assessment.applied_controls.all()] == ["Foreign"]

    def test_relation_target_outside_scope_is_refused(self):
        domain = make_domain("Here")
        elsewhere = make_domain("Elsewhere")
        assessment = make_requirement_assessment(domain)
        foreign = AppliedControl.objects.create(name="Foreign", folder=elsewhere)
        version = update_flow(
            domain,
            {
                "model": "requirement_assessment",
                "id": str(assessment.id),
                "m2m": {"applied_controls": {"op": "add", "values": str(foreign.id)}},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert assessment.applied_controls.count() == 0


@pytest.mark.django_db
class TestScopeAndPermissions:
    def test_row_outside_the_subtree_is_invisible(self):
        domain = make_domain("Scoped")
        elsewhere = make_domain("Other domain")
        foreign = AppliedControl.objects.create(name="Foreign", folder=elsewhere)
        version = update_flow(
            domain,
            {
                "model": "applied_control",
                "id": str(foreign.id),
                "fields": {"status": "active"},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        foreign.refresh_from_db()
        assert foreign.status != "active"

    def test_subtree_rows_are_reachable(self):
        parent = make_domain("Parent")
        child = make_domain("Child", parent=parent)
        control = AppliedControl.objects.create(name="Below", folder=child)
        version = update_flow(
            parent,
            {
                "model": "applied_control",
                "id": str(control.id),
                "fields": {"status": "active"},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.COMPLETED

    def test_update_requires_the_change_permission(self):
        assert required_permissions(
            {"type": "update_object", "model": "applied_control"}
        ) == ["change_appliedcontrol"]
        assert required_permissions({"type": "update_object", "model": "nope"}) == []


class TestUpdateValidation:
    def _node(self, config):
        return WorkflowNode(action_config=config)

    def test_unknown_model(self):
        codes = {
            c
            for c, _ in validate_update_config(
                self._node({"type": "update_object", "model": "nope"})
            )
        }
        assert codes == {"action_update_unknown_model"}

    def test_missing_id_and_unwritable_field(self):
        codes = {
            c
            for c, _ in validate_update_config(
                self._node(
                    {
                        "type": "update_object",
                        "model": "requirement_assessment",
                        "fields": {"result": "compliant"},
                    }
                )
            )
        }
        assert codes == {"action_update_missing_id", "action_update_field_not_writable"}

    def test_fenced_value_is_refused_at_publish(self):
        codes = {
            c
            for c, _ in validate_update_config(
                self._node(
                    {
                        "type": "update_object",
                        "model": "security_exception",
                        "id": "{{payload.object_id}}",
                        "fields": {"status": "approved"},
                    }
                )
            )
        }
        assert codes == {"action_update_value_not_allowed"}

    def test_relation_problems_are_caught_at_publish(self):
        codes = {
            c
            for c, _ in validate_update_config(
                self._node(
                    {
                        "type": "update_object",
                        "model": "applied_control",
                        "id": "x",
                        "m2m": {
                            "owner": {"op": "add", "values": ""},
                            "treatment": {"op": "add", "values": "x"},
                            "assets": {"op": "burn", "values": "x"},
                        },
                    }
                )
            )
        }
        assert codes == {
            "action_update_relation_no_values",
            "action_update_relation_not_writable",
            "action_update_bad_relation_op",
        }

    def test_a_value_outside_the_column_choices_is_refused_at_publish(self):
        codes = {
            c
            for c, _ in validate_update_config(
                self._node(
                    {
                        "type": "update_object",
                        "model": "applied_control",
                        "id": "{{payload.object_id}}",
                        "fields": {"status": "banana"},
                    }
                )
            )
        }
        assert codes == {"action_update_value_not_allowed"}

    def test_blank_inputs_are_ignored_like_they_are_at_runtime(self):
        """The builder renders an input per writable field and keeps keys
        across an action-type switch, so blanks and stale keys are normal."""
        assert (
            validate_update_config(
                self._node(
                    {
                        "type": "update_object",
                        "model": "applied_control",
                        "id": "{{payload.object_id}}",
                        "fields": {"name": "", "eta": "", "status": "active"},
                    }
                )
            )
            == []
        )

    def test_a_step_that_writes_nothing_is_refused(self):
        codes = {
            c
            for c, _ in validate_update_config(
                self._node(
                    {
                        "type": "update_object",
                        "model": "applied_control",
                        "id": "{{payload.object_id}}",
                        "fields": {"status": ""},
                    }
                )
            )
        }
        assert codes == {"action_update_nothing_to_write"}

    def test_templated_values_pass(self):
        assert (
            validate_update_config(
                self._node(
                    {
                        "type": "update_object",
                        "model": "applied_control",
                        "id": "{{payload.object_id}}",
                        "fields": {"status": "{{next_status}}"},
                        "m2m": {"owner": {"op": "set", "values": "{{owner_ids}}"}},
                    }
                )
            )
            == []
        )


@pytest.mark.django_db
class TestPublishIntegration:
    def test_a_guardrail_breach_blocks_publish(self):
        domain = make_domain("Publish")
        version = update_flow(
            domain,
            {
                "model": "requirement_assessment",
                "id": "{{payload.object_id}}",
                "fields": {"score": 5},
            },
        )
        codes = {error["code"] for error in validate_graph(version)}
        assert "action_update_field_not_writable" in codes

    def test_a_sound_update_graph_publishes(self):
        domain = make_domain("Publish ok")
        version = update_flow(
            domain,
            {
                "model": "applied_control",
                "id": "{{payload.object_id}}",
                "fields": {"status": "in_progress"},
            },
        )
        assert validate_graph(version) == []
