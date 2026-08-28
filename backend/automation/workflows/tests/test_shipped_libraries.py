"""Every workflow library shipped in library/libraries must survive the trip a
customer takes: stored, loaded, instantiated into a domain, and published.

Publishing is the real check — it runs the graph validator, so a sample with an
unwired branch, a bad action config or a fenced value fails here rather than in
someone's instance."""

from pathlib import Path

import pytest
import yaml

from core.models import LoadedLibrary, StoredLibrary
from iam.models import Folder
from automation.workflows.import_export import import_workflow
from automation.workflows.models import Workflow
from automation.workflows.validation import validate_graph
from automation.workflows.tests.helpers import publisher_user

LIBRARY_DIR = Path(__file__).resolve().parents[3] / "library" / "libraries"


def workflow_libraries():
    found = []
    for path in sorted(LIBRARY_DIR.glob("*.yaml")):
        if "workflows:" not in path.read_text():
            continue
        document = yaml.safe_load(path.read_text())
        if isinstance(document, dict) and (document.get("objects") or {}).get(
            "workflows"
        ):
            found.append(path)
    return found


LIBRARIES = workflow_libraries()


@pytest.mark.skipif(not LIBRARIES, reason="no workflow libraries shipped yet")
@pytest.mark.django_db
@pytest.mark.parametrize("path", LIBRARIES, ids=lambda p: p.stem)
class TestShippedWorkflowLibraries:
    def test_loads_through_the_library_pipeline(self, path):
        """Shipped files are registered on startup, so the customer-facing
        path is loading that stored row, not storing the file again."""
        urn = yaml.safe_load(path.read_text())["urn"]
        stored = StoredLibrary.objects.filter(urn=urn).order_by("-version").first()
        assert stored is not None, f"{urn} was not registered from library/libraries"
        assert stored.load() is None
        loaded = LoadedLibrary.objects.get(urn=urn)
        assert loaded.objects_meta.get("workflows")

    def test_every_workflow_imports_and_publishes(self, path):
        document = yaml.safe_load(path.read_text())
        domain = Folder.objects.create(
            name=f"Domain {path.stem}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        for entry in document["objects"]["workflows"]:
            # The install dialog collects declared secrets; mirror it, so a
            # sample that calls an external system can still be published here.
            secrets = {
                name: "placeholder"
                for name in (entry.get("requires") or {}).get("secrets") or []
            }
            workflow, warnings = import_workflow(
                entry, domain, user=publisher_user(), secrets=secrets
            )
            assert not [w for w in warnings if "ids from the source instance" in w], (
                f"{entry['ref_id']}: config carries ids that will not exist elsewhere"
            )
            version = workflow.draft_version
            version.run_as = publisher_user()
            version.save()
            errors = validate_graph(version)
            assert errors == [], f"{entry['ref_id']}: {errors}"

    def test_documents_declare_their_identity(self, path):
        document = yaml.safe_load(path.read_text())
        for entry in document["objects"]["workflows"]:
            assert entry.get("urn", "").startswith(document["urn"] + ":workflow:")
            assert entry.get("ref_id")
            assert entry.get("description")

    def test_nothing_can_act_on_install(self, path):
        """Samples must land inert: schedules and event triggers arrive
        disabled, and imports are drafts until someone publishes them."""
        document = yaml.safe_load(path.read_text())
        domain = Folder.objects.create(
            name=f"Inert {path.stem}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        for entry in document["objects"]["workflows"]:
            workflow, _ = import_workflow(entry, domain, user=publisher_user())
            assert workflow.published_version is None
            assert not workflow.triggers.filter(enabled=True).exists()

    def test_recipients_are_variables_not_hardcoded_addresses(self, path):
        """A shipped sample must not mail a stranger: every send_email
        recipient is templated, so installing one cannot reach an address the
        installer did not choose."""
        document = yaml.safe_load(path.read_text())
        for entry in document["objects"]["workflows"]:
            for node in entry["graph"]["nodes"]:
                config = node.get("action_config") or {}
                if config.get("type") != "send_email":
                    continue
                assert "{{" in config.get("recipients", ""), (
                    f"{entry['ref_id']}.{node['ref']}: hardcoded recipient"
                )


def test_workflow_names_are_unique_across_shipped_libraries():
    names = []
    for path in LIBRARIES:
        document = yaml.safe_load(path.read_text())
        names += [entry["name"] for entry in document["objects"]["workflows"]]
    assert len(names) == len(set(names)), "two shipped workflows share a name"


@pytest.mark.django_db
def test_a_shipped_workflow_survives_a_round_trip():
    """Import one, export it again: the document a customer re-shares must be
    loadable by the same pipeline."""
    if not LIBRARIES:
        pytest.skip("no workflow libraries shipped yet")
    from automation.workflows.import_export import export_workflow_library

    document = yaml.safe_load(LIBRARIES[0].read_text())
    domain = Folder.objects.create(
        name="Round trip",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    workflow, _ = import_workflow(
        document["objects"]["workflows"][0], domain, user=publisher_user()
    )
    again = export_workflow_library(Workflow.objects.get(pk=workflow.pk))
    stored, error = StoredLibrary.store_library_content(yaml.safe_dump(again).encode())
    assert error is None, error
    assert stored.load() is None


@pytest.mark.django_db
def test_the_read_only_explorer_actually_runs():
    """Publishing checks the shape; this checks a shipped sample executes.
    The explorer only reads and logs, so it is the one safe to run here."""
    from automation.workflows.engine import start_instance
    from automation.workflows.models import WorkflowInstance

    document = yaml.safe_load((LIBRARY_DIR / "workflows-operations.yaml").read_text())
    entry = next(
        w for w in document["objects"]["workflows"] if w["ref_id"] == "sandbox-explorer"
    )
    domain = Folder.objects.create(
        name="Explorer domain",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    workflow, _ = import_workflow(entry, domain, user=publisher_user())
    version = workflow.draft_version
    version.run_as = publisher_user()
    version.save()
    version.publish(publisher_user())

    instance = start_instance(workflow.published_version)
    assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
    assert instance.node_outputs["report"]["message"]
