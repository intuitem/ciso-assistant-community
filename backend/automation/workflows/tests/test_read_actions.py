"""read_objects action (spec D26): catalog reads scoped to the instance
folder's subtree, filter-tree compilation, modes, and publish validation."""

import uuid
from datetime import date

import pytest

from core.models import AppliedControl, Incident
from iam.models import Folder
from automation.workflows.actions import required_permissions, validate_read_config
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


def read_flow(folder, config, variables=None, input_mapping=None):
    workflow = Workflow.objects.create(name=f"Read flow {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node(
        "trigger", trigger_config={"type": "manual"}, input_mapping=input_mapping or {}
    )
    read = node(
        "action",
        label="Fetch rows",
        action_config={"type": "read_objects", **config},
    )
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [start, read, end],
            "edges": [edge(start, read), edge(read, end)],
            "variables": variables or [],
        },
    )
    return version


def read_output(instance):
    return instance.node_outputs["fetch_rows"]


@pytest.mark.django_db
class TestReadObjectsAction:
    def test_list_mode_returns_scoped_rows_with_count(self):
        domain = make_domain("Domain A")
        for index in range(3):
            AppliedControl.objects.create(name=f"AC {index}", folder=domain)
        version = read_flow(domain, {"model": "applied_control", "mode": "list"})
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = read_output(instance)
        assert output["count"] == 3
        assert {row["name"] for row in output["results"]} == {"AC 0", "AC 1", "AC 2"}
        assert set(output["results"][0]) >= {"id", "name", "status", "eta"}

    def test_count_is_unpaged_while_results_respect_limit(self):
        domain = make_domain("Domain limit")
        for index in range(5):
            AppliedControl.objects.create(name=f"AC {index}", folder=domain)
        version = read_flow(
            domain, {"model": "applied_control", "mode": "list", "limit": 2}
        )
        output = read_output(start_instance(version))
        assert output["count"] == 5
        assert len(output["results"]) == 2

    def test_ordering(self):
        domain = make_domain("Domain order")
        AppliedControl.objects.create(name="B", folder=domain, eta=date(2026, 9, 1))
        AppliedControl.objects.create(name="A", folder=domain, eta=date(2026, 8, 1))
        version = read_flow(
            domain, {"model": "applied_control", "mode": "list", "order_by": "eta"}
        )
        output = read_output(start_instance(version))
        assert [row["name"] for row in output["results"]] == ["A", "B"]
        assert output["results"][0]["eta"] == "2026-08-01"

    def test_scope_excludes_sibling_and_parent_but_includes_subfolder(self):
        parent = make_domain("Parent")
        domain = make_domain("Mine", parent=parent)
        sub = make_domain("Sub", parent=domain)
        sibling = make_domain("Sibling", parent=parent)
        AppliedControl.objects.create(name="parent row", folder=parent)
        AppliedControl.objects.create(name="my row", folder=domain)
        AppliedControl.objects.create(name="sub row", folder=sub)
        AppliedControl.objects.create(name="sibling row", folder=sibling)
        version = read_flow(domain, {"model": "applied_control", "mode": "list"})
        output = read_output(start_instance(version))
        assert {row["name"] for row in output["results"]} == {"my row", "sub row"}

    def test_filters_eq_contains_in_and_not_group(self):
        domain = make_domain("Domain filters")
        Incident.objects.create(name="Phishing wave", folder=domain, status="new")
        Incident.objects.create(name="Ransomware", folder=domain, status="closed")
        Incident.objects.create(name="Phishing retro", folder=domain, status="closed")
        version = read_flow(
            domain,
            {
                "model": "incident",
                "mode": "list",
                "filters": {
                    "operator": "and",
                    "conditions": [
                        {"field": "name", "op": "contains", "value": "phishing"},
                        {"field": "status", "op": "in", "value": ["new", "closed"]},
                    ],
                    "children": [
                        {
                            "operator": "not",
                            "conditions": [
                                {"field": "status", "op": "eq", "value": "closed"}
                            ],
                        }
                    ],
                },
            },
        )
        output = read_output(start_instance(version))
        assert [row["name"] for row in output["results"]] == ["Phishing wave"]

    def test_filter_value_templating_from_payload(self):
        domain = make_domain("Domain template")
        AppliedControl.objects.create(name="MFA rollout", folder=domain)
        AppliedControl.objects.create(name="Backups", folder=domain)
        version = read_flow(
            domain,
            {
                "model": "applied_control",
                "mode": "first",
                "filters": {
                    "operator": "and",
                    "conditions": [
                        {"field": "name", "op": "eq", "value": "{{wanted}}"}
                    ],
                },
            },
            variables=[{"id": str(uuid.uuid4()), "key": "wanted", "type": "string"}],
            input_mapping={"wanted": "wanted"},
        )
        instance = start_instance(version, payload={"wanted": "MFA rollout"})
        output = read_output(instance)
        assert output["found"] is True
        assert output["object"]["name"] == "MFA rollout"

    def test_first_mode_miss_is_not_an_error(self):
        domain = make_domain("Domain miss")
        version = read_flow(
            domain,
            {
                "model": "applied_control",
                "mode": "first",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "name", "op": "eq", "value": "nope"}],
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = read_output(instance)
        assert output == {"found": False, "object": None}

    def test_unknown_model_parks_the_token(self):
        domain = make_domain("Domain bad model")
        version = read_flow(domain, {"model": "user", "mode": "list"})
        instance = start_instance(version)
        assert instance.status != WorkflowInstance.Status.COMPLETED
        assert any(
            "unknown model" in (log.message or "")
            for log in instance.logs.filter(event_type="error")
        )

    def test_incompatible_filter_value_parks_the_token(self):
        domain = make_domain("Domain bad value")
        AppliedControl.objects.create(name="AC", folder=domain, eta=date(2026, 8, 1))
        version = read_flow(
            domain,
            {
                "model": "applied_control",
                "mode": "list",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "eta", "op": "gt", "value": "not-a-date"}],
                },
            },
        )
        instance = start_instance(version)
        assert instance.status != WorkflowInstance.Status.COMPLETED


@pytest.mark.django_db
class TestComputedReadFields:
    def test_compliance_assessment_scores_and_breakdown(self):
        from core.models import (
            ComplianceAssessment,
            Framework,
            Perimeter,
            RequirementAssessment,
            RequirementNode,
        )

        domain = make_domain("Computed domain")
        framework = Framework.objects.create(
            name="FW", urn="urn:test:fw", folder=Folder.get_root_folder()
        )
        nodes = [
            RequirementNode.objects.create(
                name=f"Req {i}",
                urn=f"urn:test:fw:req{i}",
                framework=framework,
                assessable=True,
                folder=Folder.get_root_folder(),
            )
            for i in range(3)
        ]
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        assessment = ComplianceAssessment.objects.create(
            name="Audit", framework=framework, perimeter=perimeter, folder=domain
        )
        results = ["compliant", "compliant", "non_compliant"]
        for node_row, result in zip(nodes, results):
            RequirementAssessment.objects.create(
                compliance_assessment=assessment,
                requirement=node_row,
                folder=domain,
                result=result,
                is_scored=True,
                score=3,
            )

        version = read_flow(domain, {"model": "compliance_assessment", "mode": "first"})
        output = read_output(start_instance(version))
        assert output["found"] is True
        row = output["object"]
        assert row["requirements"]["total"] == 3
        assert row["requirements"]["compliant"] == 2
        assert row["requirements"]["non_compliant"] == 1
        assert row["requirements"]["not_assessed"] == 0
        assert set(row["scores"]) == {
            "implementation_score",
            "documentation_score",
            "maturity_score",
        }
        assert "computed_outcome" in row

    def test_computed_fields_are_not_filterable(self):
        from automation.workflows.actions import validate_read_config

        domain = make_domain("Computed filter domain")
        version = read_flow(
            domain,
            {
                "model": "compliance_assessment",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "scores", "op": "eq", "value": "x"}],
                },
            },
        )
        read_node = version.nodes.get(type=WorkflowNode.Type.ACTION)
        codes = [code for code, _m in validate_read_config(read_node)]
        assert codes == ["action_read_invalid_filters"]


@pytest.mark.django_db
class TestReadValidation:
    def _version_with_config(self, config):
        domain = make_domain(f"Domain val {uuid.uuid4()}")
        return read_flow(domain, config)

    def _codes(self, config):
        version = self._version_with_config(config)
        read_node = version.nodes.get(type=WorkflowNode.Type.ACTION)
        return [code for code, _message in validate_read_config(read_node)]

    def test_valid_config_passes_publish_validation(self):
        version = self._version_with_config(
            {
                "model": "applied_control",
                "mode": "list",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "status", "op": "eq", "value": "active"}],
                },
                "order_by": "-eta",
                "limit": 10,
            }
        )
        codes = [e["code"] for e in validate_graph(version)]
        assert not any(code.startswith("action_read") for code in codes)

    def test_unknown_model(self):
        assert self._codes({"model": "user"}) == ["action_read_unknown_model"]

    def test_unknown_filter_field(self):
        codes = self._codes(
            {
                "model": "applied_control",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "folder__name", "op": "eq", "value": "x"}],
                },
            }
        )
        assert codes == ["action_read_invalid_filters"]

    def test_changed_flag_rejected(self):
        codes = self._codes(
            {
                "model": "applied_control",
                "filters": {
                    "operator": "and",
                    "conditions": [
                        {"field": "status", "op": "eq", "value": "x", "changed": True}
                    ],
                },
            }
        )
        assert codes == ["action_read_invalid_filters"]

    def test_bad_mode_order_and_limit(self):
        codes = self._codes(
            {
                "model": "applied_control",
                "mode": "all",
                "order_by": "secret",
                "limit": 5000,
            }
        )
        assert set(codes) == {
            "action_read_invalid_mode",
            "action_read_invalid_order",
            "action_read_invalid_limit",
        }

    def test_errors_surface_in_validate_graph(self):
        version = self._version_with_config({"model": "user"})
        codes = [e["code"] for e in validate_graph(version)]
        assert "action_read_unknown_model" in codes

    def test_required_permissions_returns_view_codename(self):
        assert required_permissions(
            {"type": "read_objects", "model": "applied_control"}
        ) == ["view_appliedcontrol"]
        assert required_permissions({"type": "read_objects", "model": "nope"}) == []
