"""D28 schema freeze: every export validates against the versioned JSON
Schema, canonical exports are minimal, capabilities gate forward-compat,
branches travel by name, provenance is stamped at import."""

import json
import uuid
from pathlib import Path

import jsonschema
import pytest

from iam.models import Folder
from workflows.graph import save_graph
from workflows.import_export import (
    WorkflowImportError,
    export_workflow,
    import_workflow,
)
from workflows.models import Workflow, WorkflowVersion

SCHEMA = json.loads(
    (Path(__file__).parent.parent / "schema" / "workflow-v1.schema.json").read_text()
)


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


def rich_workflow():
    """One workflow exercising branches, for_each, read actions, secrets and
    variables — the shapes the freeze must keep stable."""
    workflow = Workflow.objects.create(
        name=f"Freeze probe {uuid.uuid4()}", folder=Folder.get_root_folder()
    )
    version = WorkflowVersion.objects.create(workflow=workflow)
    var_id = str(uuid.uuid4())
    trigger = node("trigger", trigger_config={"type": "manual"})
    read = node(
        "action",
        label="List controls",
        action_config={
            "type": "read_objects",
            "model": "applied_control",
            "mode": "list",
            "filters": {
                "operator": "and",
                "conditions": [{"field": "status", "op": "eq", "value": "active"}],
                "children": [],
            },
        },
        output_mapping={"n": "count"},
    )
    loop = node(
        "loop",
        label="Each control",
        loop_config={
            "collection": "{{nodes.list_controls.results}}",
            "on_item_error": "continue",
        },
    )
    notify = node(
        "action",
        label="Notify",
        action_config={
            "type": "http_request",
            "method": "POST",
            "url": "https://example.test/hook",
            "headers": {"Authorization": "Bearer {{secrets.api_token}}"},
            "body": "{{item.name}}",
        },
    )
    cond = node(
        "condition",
        label="Any?",
        branches=[
            {
                "id": str(uuid.uuid4()),
                "name": "some",
                "order": 0,
                "is_default": False,
                "condition_groups": [
                    {
                        "operator": "and",
                        "order": 0,
                        "conditions": [
                            {"variable": var_id, "op": "gt", "value": "0", "order": 0}
                        ],
                        "children": [],
                    }
                ],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "",
                "order": 1,
                "is_default": True,
                "condition_groups": [],
            },
        ],
    )
    log_a = node("action", label="Some", action_config={"type": "log", "message": "a"})
    log_b = node(
        "action",
        label="None",
        action_config={"type": "log", "message": "b", "extra": ""},
    )
    end = node("end")
    branches = cond["branches"]
    save_graph(
        version,
        {
            "nodes": [trigger, read, loop, notify, cond, log_a, log_b, end],
            "edges": [
                edge(trigger, read),
                edge(read, loop),
                edge(loop, notify, source_port="each"),
                edge(notify, loop),
                edge(loop, cond, source_port="done"),
                edge(cond, log_a, source_branch=branches[0]["id"]),
                edge(cond, log_b, source_branch=branches[1]["id"]),
                edge(log_a, end),
                edge(log_b, end),
            ],
            "variables": [{"id": var_id, "key": "n", "type": "number"}],
        },
    )
    return workflow


def walk_values(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk_values(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_values(item, f"{path}[{index}]")
    else:
        yield path, value


@pytest.mark.django_db
class TestSchemaFreeze:
    def test_export_validates_against_schema(self):
        document = export_workflow(rich_workflow())
        jsonschema.validate(document, SCHEMA)

    def test_export_is_minimal(self):
        document = export_workflow(rich_workflow())
        for path, value in walk_values(document):
            assert value not in ("", None), f"empty value exported at {path}"
        blob = json.dumps(document)
        assert '"extra": ""' not in blob
        assert '"children": []' not in blob

    def test_capabilities_manifest(self):
        document = export_workflow(rich_workflow())
        assert document["requires"]["capabilities"] == ["loop", "read_objects"]
        assert document["requires"]["secrets"] == ["api_token"]

    def test_unknown_capability_is_rejected(self):
        document = export_workflow(rich_workflow())
        document["requires"]["capabilities"].append("quantum_actions")
        with pytest.raises(WorkflowImportError, match="quantum_actions"):
            import_workflow(document, Folder.get_root_folder())

    def test_branches_travel_by_name(self):
        document = export_workflow(rich_workflow())
        cond = next(n for n in document["graph"]["nodes"] if n["type"] == "condition")
        assert [b["name"] for b in cond["branches"]] == ["some", "otherwise"]
        named = [
            e["source_branch"]
            for e in document["graph"]["edges"]
            if "source_branch" in e
        ]
        assert sorted(named) == ["otherwise", "some"]

    def test_roundtrip_with_named_branches(self):
        document = export_workflow(rich_workflow())
        imported, _warnings = import_workflow(document, Folder.get_root_folder())
        again = export_workflow(imported)
        assert again["graph"] == document["graph"]

    def test_positional_source_branch_still_accepted(self):
        document = export_workflow(rich_workflow())
        for edge_entry in document["graph"]["edges"]:
            if "source_branch" in edge_entry:
                cond = next(
                    n
                    for n in document["graph"]["nodes"]
                    if n["type"] == "condition"
                )
                names = [b["name"] for b in cond["branches"]]
                edge_entry["source_branch"] = names.index(edge_entry["source_branch"])
        imported, _ = import_workflow(document, Folder.get_root_folder())
        again = export_workflow(imported)
        cond = next(n for n in again["graph"]["nodes"] if n["type"] == "condition")
        assert [b["name"] for b in cond["branches"]] == ["some", "otherwise"]

    def test_duplicate_branch_names_rejected(self):
        document = export_workflow(rich_workflow())
        cond = next(n for n in document["graph"]["nodes"] if n["type"] == "condition")
        cond["branches"][1]["name"] = cond["branches"][0]["name"]
        for edge_entry in document["graph"]["edges"]:
            edge_entry.pop("source_branch", None)
        with pytest.raises(WorkflowImportError, match="duplicate branch names"):
            import_workflow(document, Folder.get_root_folder())

    def test_provenance_stamped_from_envelope(self):
        document = export_workflow(rich_workflow())
        document["urn"] = "urn:intuitem:workflow:overdue-digest"
        document["version"] = 3
        jsonschema.validate(document, SCHEMA)
        imported, _ = import_workflow(document, Folder.get_root_folder())
        assert imported.source_urn == "urn:intuitem:workflow:overdue-digest"
        assert imported.source_version == "3"

    def test_node_reference_missing_validation(self):
        from workflows.validation import validate_graph

        workflow = rich_workflow()
        version = workflow.versions.first()
        broken = version.nodes.get(label="Notify")
        broken.action_config["body"] = "{{nodes.gone.results}}"
        broken.save(update_fields=["action_config"])
        codes = [e["code"] for e in validate_graph(version)]
        assert "node_reference_missing" in codes
