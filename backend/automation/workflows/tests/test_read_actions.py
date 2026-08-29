"""read_objects action: catalog reads scoped to the instance
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
    WorkflowToken,
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


@pytest.mark.django_db
class TestRegistryIntegrity:
    def test_every_field_is_a_concrete_scoped_column(self):
        """The field list doubles as the filter/order whitelist, so a
        non-column entry would explode at query time; the scope filter
        assumes a concrete folder FK."""
        from automation.workflows.actions import READABLE_MODELS

        for key, entry in READABLE_MODELS.items():
            columns = {f.name for f in entry.model._meta.concrete_fields}
            assert "folder" in columns, key
            for field in entry.readable_fields():
                assert field in columns, f"{key}.{field}"


@pytest.mark.django_db
class TestNamelessModels:
    def test_validation_flow_reads_without_name_column(self):
        from core.models import ValidationFlow

        domain = make_domain("Domain validations")
        ValidationFlow.objects.create(folder=domain)
        version = read_flow(domain, {"model": "validation_flow", "mode": "list"})
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = read_output(instance)
        assert output["count"] == 1
        row = output["results"][0]
        assert "name" not in row
        assert row["status"] == "submitted"
        assert row["ref_id"]
        # API parity: the display key for this nameless model is "str".
        assert row["str"] == row["ref_id"]

    def test_null_ref_id_rows_read_with_empty_str(self):
        """ref_id is only auto-assigned in save(); bulk-created rows can hold
        NULL, and str() must not blow up the whole read on them."""
        from core.models import ValidationFlow

        domain = make_domain("Domain null ref")
        flow = ValidationFlow.objects.create(folder=domain)
        ValidationFlow.objects.filter(id=flow.id).update(ref_id=None)
        version = read_flow(domain, {"model": "validation_flow", "mode": "list"})
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        row = read_output(instance)["results"][0]
        assert row["str"] == ""
        assert row["ref_id"] is None

    def test_name_is_not_filterable_on_nameless_models(self):
        domain = make_domain("Domain nameless filter")
        version = read_flow(
            domain,
            {
                "model": "validation_flow",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "name", "op": "eq", "value": "x"}],
                },
            },
        )
        read_node = version.nodes.get(type=WorkflowNode.Type.ACTION)
        codes = [code for code, _message in validate_read_config(read_node)]
        assert codes == ["action_read_invalid_filters"]


@pytest.mark.django_db
class TestDeadlineSweepModels:
    def test_risk_acceptance_expiry_filter(self):
        from core.models import RiskAcceptance

        domain = make_domain("Domain acceptances")
        RiskAcceptance.objects.create(
            name="Expiring", folder=domain, expiry_date=date(2026, 1, 1)
        )
        RiskAcceptance.objects.create(
            name="Far out", folder=domain, expiry_date=date(2030, 1, 1)
        )
        version = read_flow(
            domain,
            {
                "model": "risk_acceptance",
                "mode": "list",
                "filters": {
                    "operator": "and",
                    "conditions": [
                        {"field": "expiry_date", "op": "lt", "value": "2027-01-01"}
                    ],
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = read_output(instance)
        assert output["count"] == 1
        assert output["results"][0]["name"] == "Expiring"

    def test_requirement_assessment_sweep_carries_identifiers(self):
        from core.models import (
            ComplianceAssessment,
            Framework,
            Perimeter,
            RequirementAssessment,
            RequirementNode,
        )

        domain = make_domain("Domain requirements")
        framework = Framework.objects.create(
            name="FW", urn="urn:test:fw:ra", folder=Folder.get_root_folder()
        )
        # R1 is ref_id-only (no name), like most shipped framework nodes.
        requirements = [
            RequirementNode.objects.create(
                name="Req 0" if i == 0 else None,
                ref_id=f"R{i}",
                urn=f"urn:test:fw:ra:req{i}",
                framework=framework,
                assessable=True,
                folder=Folder.get_root_folder(),
            )
            for i in range(2)
        ]
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        assessment = ComplianceAssessment.objects.create(
            name="Audit", framework=framework, perimeter=perimeter, folder=domain
        )
        for requirement, result in zip(requirements, ["compliant", "non_compliant"]):
            RequirementAssessment.objects.create(
                compliance_assessment=assessment,
                requirement=requirement,
                folder=domain,
                result=result,
            )

        version = read_flow(
            domain,
            {
                "model": "requirement_assessment",
                "mode": "list",
                "filters": {
                    "operator": "and",
                    "conditions": [
                        {"field": "result", "op": "eq", "value": "non_compliant"}
                    ],
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = read_output(instance)
        assert output["count"] == 1
        row = output["results"][0]
        assert row["result"] == "non_compliant"
        # API-shaped identifiers: name is __str__, falling back to the
        # requirement's ref_id when the node has no name.
        assert row["name"] == "R1"
        assert row["requirement"]["ref_id"] == "R1"
        assert row["requirement"]["name"] is None
        assert row["compliance_assessment"]["name"] == "Audit"


def make_scenarios(domain):
    """One rated (current_level=1) and one unrated (-1 sentinel) scenario."""
    from core.models import Perimeter, RiskAssessment, RiskMatrix, RiskScenario

    perimeter = Perimeter.objects.create(name="P", folder=domain)
    matrix = RiskMatrix.objects.create(
        name="M",
        folder=Folder.get_root_folder(),
        json_definition={"risk": [{"name": "Low"}, {"name": "Medium"}]},
    )
    assessment = RiskAssessment.objects.create(
        name="RA", perimeter=perimeter, risk_matrix=matrix, folder=domain
    )
    rated = RiskScenario.objects.create(
        name="Rated", risk_assessment=assessment, folder=domain
    )
    RiskScenario.objects.create(
        name="Unrated", risk_assessment=assessment, folder=domain
    )
    # save() resets levels to -1 while proba/impact are unset; rate one row
    # at the column level.
    RiskScenario.objects.filter(id=rated.id).update(current_level=1)
    return assessment


@pytest.mark.django_db
class TestRiskScenarioLevels:
    def test_threshold_filters_skip_unrated_scenarios(self):
        domain = make_domain("Domain scenario levels")
        make_scenarios(domain)
        version = read_flow(
            domain,
            {
                "model": "risk_scenario",
                "mode": "list",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "current_level", "op": "lte", "value": 2}],
                },
            },
        )
        output = read_output(start_instance(version))
        assert [row["name"] for row in output["results"]] == ["Rated"]

    def test_eq_minus_one_still_targets_unrated_rows(self):
        domain = make_domain("Domain unrated eq")
        make_scenarios(domain)
        version = read_flow(
            domain,
            {
                "model": "risk_scenario",
                "mode": "list",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "current_level", "op": "eq", "value": -1}],
                },
            },
        )
        output = read_output(start_instance(version))
        assert [row["name"] for row in output["results"]] == ["Unrated"]

    def test_levels_serialize_as_matrix_cells(self):
        domain = make_domain("Domain level labels")
        make_scenarios(domain)
        version = read_flow(
            domain, {"model": "risk_scenario", "mode": "list", "order_by": "name"}
        )
        rated, unrated = read_output(start_instance(version))["results"]
        assert rated["current_level"] == {"name": "Medium", "value": 1}
        assert unrated["current_level"]["value"] == -1
        assert unrated["current_level"]["name"] == "--"
        assert rated["inherent_level"]["value"] == -1

    def test_negations_still_exclude_unrated_scenarios(self):
        """The >= 0 guard must survive negation: 'not', neq and not_in would
        otherwise flip it into 'OR level < 0' and sweep unrated rows in."""
        domain = make_domain("Domain unrated negation")
        make_scenarios(domain)
        cases = [
            {
                "operator": "not",
                "conditions": [{"field": "current_level", "op": "lte", "value": 0}],
            },
            {
                "operator": "and",
                "conditions": [{"field": "current_level", "op": "neq", "value": 0}],
            },
            {
                "operator": "and",
                "conditions": [
                    {"field": "current_level", "op": "not_in", "value": [0]}
                ],
            },
        ]
        for filters in cases:
            version = read_flow(
                domain, {"model": "risk_scenario", "mode": "list", "filters": filters}
            )
            output = read_output(start_instance(version))
            assert [row["name"] for row in output["results"]] == ["Rated"], filters

    def test_stale_matrix_level_fails_with_clean_error(self):
        """A library update can shrink the matrix while scenarios keep their
        old level indices; the read must fail as ActionError, not IndexError."""
        from core.models import RiskScenario

        domain = make_domain("Domain stale matrix")
        make_scenarios(domain)
        RiskScenario.objects.filter(name="Rated").update(current_level=5)
        version = read_flow(domain, {"model": "risk_scenario", "mode": "list"})
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        token = instance.tokens.get(status=WorkflowToken.Status.ERROR)
        assert "no longer exists in the risk matrix" in token.error_message


@pytest.mark.django_db
class TestApiShapeParity:
    def test_enum_fields_render_display_labels_but_filter_on_raw_values(self):
        domain = make_domain("Domain enum labels")
        Incident.objects.create(name="Breach", folder=domain, status="new", severity=1)
        Incident.objects.create(name="Old", folder=domain, status="closed", severity=5)
        version = read_flow(
            domain,
            {
                "model": "incident",
                "mode": "first",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "status", "op": "eq", "value": "new"}],
                },
            },
        )
        obj = read_output(start_instance(version))["object"]
        # Same shape as IncidentReadSerializer: display labels out, raw in.
        assert obj["name"] == "Breach"
        assert obj["status"] == "New"
        assert obj["severity"] == "Critical"


@pytest.mark.django_db
class TestAssessableFilter:
    def test_non_assessable_rows_are_excluded(self):
        from core.models import (
            ComplianceAssessment,
            Framework,
            Perimeter,
            RequirementAssessment,
            RequirementNode,
        )

        domain = make_domain("Domain assessable")
        framework = Framework.objects.create(
            name="FW", urn="urn:test:fw:hdr", folder=Folder.get_root_folder()
        )
        header = RequirementNode.objects.create(
            name=None,
            ref_id="1",
            urn="urn:test:fw:hdr:1",
            framework=framework,
            assessable=False,
            folder=Folder.get_root_folder(),
        )
        leaf = RequirementNode.objects.create(
            name=None,
            ref_id="1.1",
            urn="urn:test:fw:hdr:1.1",
            framework=framework,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        audit = ComplianceAssessment.objects.create(
            name="Audit", framework=framework, perimeter=perimeter, folder=domain
        )
        for requirement in (header, leaf):
            RequirementAssessment.objects.create(
                compliance_assessment=audit, requirement=requirement, folder=domain
            )

        version = read_flow(domain, {"model": "requirement_assessment", "mode": "list"})
        output = read_output(start_instance(version))
        assert output["count"] == 1
        assert output["results"][0]["requirement"]["ref_id"] == "1.1"


@pytest.mark.django_db
class TestAssessmentScoping:
    def test_requirement_assessment_filterable_by_audit(self):
        from core.models import (
            ComplianceAssessment,
            Framework,
            Perimeter,
            RequirementAssessment,
            RequirementNode,
        )

        domain = make_domain("Domain audit scoping")
        framework = Framework.objects.create(
            name="FW", urn="urn:test:fw:scope", folder=Folder.get_root_folder()
        )
        requirement = RequirementNode.objects.create(
            ref_id="R1",
            urn="urn:test:fw:scope:req1",
            framework=framework,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        audits = [
            ComplianceAssessment.objects.create(
                name=f"Audit {i}",
                framework=framework,
                perimeter=perimeter,
                folder=domain,
            )
            for i in range(2)
        ]
        for audit in audits:
            RequirementAssessment.objects.create(
                compliance_assessment=audit,
                requirement=requirement,
                folder=domain,
                result="non_compliant",
            )

        version = read_flow(
            domain,
            {
                "model": "requirement_assessment",
                "mode": "list",
                "filters": {
                    "operator": "and",
                    "conditions": [
                        {
                            "field": "compliance_assessment",
                            "op": "eq",
                            "value": str(audits[0].id),
                        }
                    ],
                },
            },
        )
        output = read_output(start_instance(version))
        assert output["count"] == 1
        row = output["results"][0]
        # Same nested shape as the API's FieldsRelatedField.
        assert row["compliance_assessment"] == {
            "str": str(audits[0]),
            "id": str(audits[0].id),
            "name": "Audit 0",
        }

    def test_risk_scenario_filterable_by_risk_assessment(self):
        from core.models import Perimeter, RiskAssessment, RiskMatrix, RiskScenario

        domain = make_domain("Domain scenario scoping")
        assessment = make_scenarios(domain)
        perimeter = Perimeter.objects.create(name="P2", folder=domain)
        matrix = RiskMatrix.objects.create(name="M2", folder=Folder.get_root_folder())
        other = RiskAssessment.objects.create(
            name="Other", perimeter=perimeter, risk_matrix=matrix, folder=domain
        )
        RiskScenario.objects.create(
            name="Elsewhere", risk_assessment=other, folder=domain
        )

        version = read_flow(
            domain,
            {
                "model": "risk_scenario",
                "mode": "list",
                "filters": {
                    "operator": "and",
                    "conditions": [
                        {
                            "field": "risk_assessment",
                            "op": "eq",
                            "value": str(assessment.id),
                        }
                    ],
                },
            },
        )
        output = read_output(start_instance(version))
        assert {row["name"] for row in output["results"]} == {"Rated", "Unrated"}


@pytest.mark.django_db
class TestOperatorTypeGating:
    def _flow(self, op, value):
        domain = make_domain(f"Domain op gate {op}")
        return read_flow(
            domain,
            {
                "model": "requirement_assessment",
                "filters": {
                    "operator": "and",
                    "conditions": [{"field": "is_scored", "op": op, "value": value}],
                },
            },
        )

    def test_boolean_contains_is_rejected_at_publish_time(self):
        version = self._flow("contains", "tru")
        read_node = version.nodes.get(type=WorkflowNode.Type.ACTION)
        codes = [code for code, _message in validate_read_config(read_node)]
        assert codes == ["action_read_invalid_filters"]

    def test_boolean_eq_still_validates(self):
        version = self._flow("eq", True)
        read_node = version.nodes.get(type=WorkflowNode.Type.ACTION)
        assert validate_read_config(read_node) == []

    def test_boolean_contains_is_rejected_at_run_time(self):
        # Published configs predate the publish gate: the same check must
        # fail loud at execution instead of diverging across databases.
        from automation.workflows.actions import (
            READABLE_MODELS,
            ActionError,
            _read_condition_to_q,
        )

        entry = READABLE_MODELS["requirement_assessment"]
        with pytest.raises(ActionError, match="not valid for field"):
            _read_condition_to_q(
                {"field": "is_scored", "op": "contains", "value": "tru"},
                entry,
                {"is_scored"},
                {},
            )
