"""Built objects: create_object dispatches to a constructor when the registry
entry declares one, so an audit arrives with its requirements and a third-party
assessment can arrive with its questionnaire."""

import uuid

import pytest

from core.models import ComplianceAssessment, Framework, RequirementNode
from iam.models import Folder
from tprm.models import Entity, EntityAssessment
from automation.workflows.actions import (
    required_permissions,
    validate_create_config,
)
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowNode,
    WorkflowVersion,
)
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


def make_domain(name):
    return Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def make_framework(groups=True):
    slug = uuid.uuid4().hex[:8]
    framework = Framework.objects.create(
        name=f"FW {slug}",
        urn=f"urn:test:risk:library:fw-{slug}:framework:fw",
        folder=Folder.get_root_folder(),
        implementation_groups_definition=[{"ref_id": "core"}, {"ref_id": "advanced"}]
        if groups
        else None,
    )
    for index in range(3):
        RequirementNode.objects.create(
            name=f"Req {index}",
            urn=f"{framework.urn}:req{index}",
            framework=framework,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
    return framework


def action_flow(folder, config):
    workflow = Workflow.objects.create(name=f"Flow {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    act = node("action", label="Build it", action_config=config)
    end = node("end")
    save_graph(
        version,
        {"nodes": [start, act, end], "edges": [edge(start, act), edge(act, end)]},
    )
    return version


@pytest.mark.django_db
class TestCreateAudit:
    def test_builds_an_audit_with_its_requirements(self):
        domain = make_domain("Audit build")
        framework = make_framework()
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "compliance_assessment",
                "fields": {
                    "name": "Q4 audit",
                    "framework": framework.urn,
                    "implementation_groups": ["core"],
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        audit = ComplianceAssessment.objects.get(name="Q4 audit")
        assert audit.framework == framework
        assert audit.selected_implementation_groups == ["core"]
        # The point of the action: create_object left this at zero.
        assert audit.requirement_assessments.count() == 3
        assert instance.node_outputs["build_it"]["created_object_name"] == "Q4 audit"

    def test_the_framework_can_be_named_by_urn_or_id(self):
        domain = make_domain("By id")
        framework = make_framework()
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "compliance_assessment",
                "fields": {"name": "By id", "framework": str(framework.id)},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.COMPLETED

    def test_an_unknown_framework_fails_the_node(self):
        domain = make_domain("No framework")
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "compliance_assessment",
                "fields": {
                    "name": "Nope",
                    "framework": "urn:test:risk:library:missing:framework:nope",
                },
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED

    def test_an_undefined_implementation_group_fails_the_node(self):
        domain = make_domain("Bad group")
        framework = make_framework()
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "compliance_assessment",
                "fields": {
                    "name": "Bad group",
                    "framework": framework.urn,
                    "implementation_groups": ["nonexistent"],
                },
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not ComplianceAssessment.objects.filter(name="Bad group").exists()


@pytest.mark.django_db
class TestCreateEntityAssessment:
    def make_entity(self, domain):
        return Entity.objects.create(
            name=f"Vendor {uuid.uuid4().hex[:6]}", folder=domain
        )

    def test_creates_the_assessment_alone(self):
        domain = make_domain("TPRM plain")
        entity = self.make_entity(domain)
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "entity_assessment",
                "fields": {"name": "Due diligence", "entity": str(entity.id)},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        assessment = EntityAssessment.objects.get(name="Due diligence")
        assert assessment.entity == entity
        assert assessment.compliance_assessment is None

    def test_creates_the_questionnaire_with_implementation_groups(self):
        domain = make_domain("TPRM questionnaire")
        entity = self.make_entity(domain)
        framework = make_framework()
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "entity_assessment",
                "fields": {
                    "name": "Vendor questionnaire",
                    "entity": str(entity.id),
                    "framework": framework.urn,
                    "implementation_groups": ["core", "advanced"],
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        assessment = EntityAssessment.objects.get(name="Vendor questionnaire")
        audit = assessment.compliance_assessment
        assert audit is not None
        assert audit.selected_implementation_groups == ["core", "advanced"]
        assert audit.requirement_assessments.count() == 3
        # The questionnaire lives in its own enclave, like the API builds it.
        assert audit.folder.content_type == Folder.ContentType.ENCLAVE
        assert audit.folder.parent_folder == domain
        assert instance.node_outputs["build_it"]["created_object_id"] == str(
            assessment.id
        )

    def test_an_entity_outside_scope_is_refused(self):
        domain = make_domain("Scoped tprm")
        elsewhere = make_domain("Other tprm")
        entity = Entity.objects.create(name="Foreign vendor", folder=elsewhere)
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "entity_assessment",
                "fields": {"name": "Nope", "entity": str(entity.id)},
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED


class TestBuiltObjectValidation:
    def _node(self, config):
        return WorkflowNode(action_config=config)

    def test_a_required_construction_param_is_caught_at_publish(self):
        codes = {
            c
            for c, _ in validate_create_config(
                self._node(
                    {
                        "type": "create_object",
                        "model": "compliance_assessment",
                        "fields": {"name": "x"},
                    }
                )
            )
        }
        assert codes == {"action_create_missing_param"}

    def test_upsert_is_refused_on_a_built_model(self):
        codes = {
            c
            for c, _ in validate_create_config(
                self._node(
                    {
                        "type": "create_object",
                        "model": "compliance_assessment",
                        "upsert": True,
                        "fields": {"name": "x", "framework": "urn:test:fw"},
                    }
                )
            )
        }
        assert "action_create_upsert_unsupported" in codes

    def test_a_framework_that_is_neither_urn_nor_id_is_refused(self):
        codes = {
            c
            for c, _ in validate_create_config(
                self._node(
                    {
                        "type": "create_object",
                        "model": "compliance_assessment",
                        "fields": {"name": "x", "framework": "ISO 27001"},
                    }
                )
            )
        }
        assert codes == {"action_create_bad_reference"}

    def test_templated_values_pass(self):
        assert (
            validate_create_config(
                self._node(
                    {
                        "type": "create_object",
                        "model": "entity_assessment",
                        "fields": {
                            "name": "Due diligence: {{payload.object_repr}}",
                            "entity": "{{payload.object_id}}",
                            "framework": "{{framework_urn}}",
                            "implementation_groups": "{{groups}}",
                        },
                    }
                )
            )
            == []
        )

    def test_permissions_follow_what_gets_built(self):
        assert required_permissions(
            {"type": "create_object", "model": "entity_assessment", "fields": {}}
        ) == ["add_entityassessment"]
        assert required_permissions(
            {
                "type": "create_object",
                "model": "entity_assessment",
                "fields": {"framework": "urn:x"},
            }
        ) == ["add_entityassessment", "add_complianceassessment"]


@pytest.mark.django_db
class TestReferenceResolution:
    """Library-backed objects are named by urn, so a shipped workflow can
    point at one; the builder's pickers keep supplying ids."""

    def test_create_object_accepts_a_matrix_urn(self):
        from core.models import RiskAssessment, RiskMatrix
        from core.models import Perimeter

        domain = make_domain("Matrix by urn")
        matrix = RiskMatrix.objects.create(
            name="M",
            urn=f"urn:test:risk:library:m-{uuid.uuid4().hex[:6]}:risk_matrix:m",
            folder=Folder.get_root_folder(),
            json_definition={"risk": [{"name": "Low"}]},
        )
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "risk_assessment",
                "fields": {
                    "name": "Quarterly review",
                    "risk_matrix": matrix.urn,
                    "perimeter": str(perimeter.id),
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        assert RiskAssessment.objects.get(name="Quarterly review").risk_matrix == matrix

    def test_an_unknown_urn_fails_the_node(self):
        from core.models import Perimeter

        domain = make_domain("Bad urn")
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "risk_assessment",
                "fields": {
                    "name": "No matrix",
                    "risk_matrix": "urn:test:risk:library:nope:risk_matrix:nope",
                    "perimeter": str(perimeter.id),
                },
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED

    def test_a_literal_that_is_neither_urn_nor_id_is_refused_at_publish(self):
        from automation.workflows.actions import validate_create_config

        codes = {
            c
            for c, _ in validate_create_config(
                WorkflowNode(
                    action_config={
                        "type": "create_object",
                        "model": "risk_assessment",
                        "fields": {"name": "x", "risk_matrix": "ISO 5x5"},
                    }
                )
            )
        }
        assert "action_create_bad_reference" in codes
