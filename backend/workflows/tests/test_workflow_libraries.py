"""Workflow libraries (spec D31): exports are library documents, loadable
through the library pipeline; loaded workflows are divorced user documents."""

import uuid

import pytest
import yaml

from core.models import StoredLibrary, LoadedLibrary
from iam.models import Folder
from workflows.graph import save_graph
from workflows.import_export import export_workflow_library, import_workflow_library
from workflows.models import Workflow, WorkflowVersion


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


def simple_workflow(name="Escalation runbook"):
    workflow = Workflow.objects.create(name=name, folder=Folder.get_root_folder())
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger = node("trigger", trigger_config={"type": "manual"})
    act = node(
        "action",
        label="Log it",
        action_config={"type": "log", "message": "hello {{secrets.token}}"},
    )
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [trigger, act, end],
            "edges": [edge(trigger, act), edge(act, end)],
            "variables": [],
        },
    )
    return workflow


@pytest.mark.django_db
class TestWorkflowLibraryExport:
    def test_envelope_satisfies_library_requirements(self):
        document = export_workflow_library(simple_workflow())
        assert StoredLibrary.REQUIRED_FIELDS <= set(document.keys())
        assert document["urn"] == "urn:custom:risk:library:workflow-escalation-runbook"
        assert document["version"] == 1
        assert document["locale"] == "en"
        entry = document["objects"]["workflows"][0]
        assert entry["urn"].startswith(document["urn"] + ":workflow:")
        assert entry["schema_version"] == 1
        assert entry["requires"] == {"secrets": ["token"]}

    def test_store_and_load_creates_divorced_workflow(self):
        document = export_workflow_library(simple_workflow("Runbook"))
        content = yaml.safe_dump(document).encode()
        stored, error = StoredLibrary.store_library_content(content)
        assert error is None, error
        assert stored.objects_meta == {"workflows": 1}

        error = stored.load()
        assert error is None, error

        loaded = LoadedLibrary.objects.get(urn=document["urn"])
        imported = Workflow.objects.get(name="Runbook (2)")  # source still exists
        assert imported.source_urn == document["objects"]["workflows"][0]["urn"]
        assert imported.source_version == "1"
        assert imported.draft_version is not None

        # Divorce: unloading the library leaves the workflow untouched.
        loaded.delete()
        assert Workflow.objects.filter(id=imported.id).exists()

    def test_dialog_import_targets_folder(self):
        document = export_workflow_library(simple_workflow("Dialog flow"))
        domain = Folder.objects.create(
            name="Import target",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        workflows, _warnings = import_workflow_library(document, domain)
        assert [w.folder for w in workflows] == [domain]
        assert workflows[0].source_version == "1"

    def test_non_library_document_is_rejected(self):
        from workflows.import_export import WorkflowImportError

        with pytest.raises(WorkflowImportError, match="workflow library"):
            import_workflow_library(
                {"schema_version": 1, "name": "old style", "graph": {}},
                Folder.get_root_folder(),
            )

    def test_broken_workflow_entry_fails_the_whole_store(self):
        document = export_workflow_library(simple_workflow("Broken lib"))
        document["objects"]["workflows"][0]["graph"]["nodes"][0]["ref"] = "BAD REF"
        content = yaml.safe_dump(document).encode()
        stored, error = StoredLibrary.store_library_content(content)
        assert error is None  # storing succeeds; loading validates
        error = stored.load()
        assert error is not None and "objects.workflows[0]" in error
        assert not Workflow.objects.filter(name="Broken lib (2)").exists()
