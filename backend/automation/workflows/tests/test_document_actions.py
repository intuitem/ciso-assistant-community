"""Managed documents as a workflow citizen: read them, open one with its first
draft, open the next draft, and rewrite a draft's markdown.

The line this module defends is the same one the rest of the registry draws —
automation may write the text, never the verdict. A revision's `status` is
absent from the update registry because publish() deprecates the revision it
replaces and repoints the document, and a draft is the only revision whose
markdown a run may touch at all.
"""

import uuid

import pytest

from doc_management.models import (
    DocumentContainer,
    DocumentEdit,
    DocumentRevision,
    DocumentTemplate,
    ManagedDocument,
)
from iam.models import Folder
from automation.workflows.actions import UPDATABLE_MODELS, required_permissions
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
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


def edge(source, target):
    return {"id": str(uuid.uuid4()), "source": source["id"], "target": target["id"]}


def make_domain(name, parent=None):
    return Folder.objects.create(
        name=name,
        parent_folder=parent or Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def action_flow(folder, config, label="Do it"):
    workflow = Workflow.objects.create(name=f"Docs {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    act = node("action", label=label, action_config=config)
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [start, act, end],
            "edges": [edge(start, act), edge(act, end)],
        },
    )
    return version


def make_document(
    folder, content="# Access control\n\nOriginal.", locale="en", name="Access control"
):
    """A container, its locale variant and a published v1 — what the editor
    leaves behind once someone has published a document. `name` is a parameter
    because a container's name is unique within its folder."""
    container = DocumentContainer.objects.create(name=name, folder=folder)
    document = ManagedDocument.objects.create(container=container, locale=locale)
    revision = DocumentRevision.objects.create(
        document=document,
        version_number=1,
        content=content,
        status=DocumentRevision.Status.PUBLISHED,
    )
    document.current_revision = revision
    document.save()
    return container, document, revision


@pytest.mark.django_db
class TestCreatingADocument:
    def _flow(self, folder, container, **fields):
        return action_flow(
            folder,
            {
                "type": "create_object",
                "model": "managed_document",
                "fields": {"container": str(container.id), **fields},
            },
        )

    def test_a_document_arrives_with_its_first_draft(self):
        domain = make_domain("Policies")
        container = DocumentContainer.objects.create(name="Backup", folder=domain)
        instance = start_instance(
            self._flow(domain, container, name="Backup policy", content="# Backup")
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        document = ManagedDocument.objects.get(container=container)
        assert document.folder == domain
        assert document.default_locale is True
        revision = document.current_revision
        assert (revision.version_number, revision.status) == (
            1,
            DocumentRevision.Status.DRAFT,
        )
        assert revision.content == "# Backup"
        assert revision.folder == domain

    def test_a_template_seeds_the_draft(self):
        domain = make_domain("Templated")
        DocumentTemplate.objects.create(
            ref_id="iso-27001-access",
            name="Access control policy",
            content="## Purpose\n\n{{scope}}",
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        container = DocumentContainer.objects.create(name="Access", folder=domain)
        instance = start_instance(
            self._flow(
                domain,
                container,
                name="Access policy",
                template_used="iso-27001-access",
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        document = ManagedDocument.objects.get(container=container)
        assert document.current_revision.content == "## Purpose\n\n{{scope}}"

    def test_an_unknown_template_stops_the_run(self):
        domain = make_domain("No template")
        container = DocumentContainer.objects.create(name="Nope", folder=domain)
        instance = start_instance(
            self._flow(domain, container, name="Nope", template_used="does-not-exist")
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert not ManagedDocument.objects.filter(container=container).exists()

    def test_one_document_per_locale(self):
        """(container, locale) is the document's identity: a second row would
        make `default_locale` and the catalog ambiguous."""
        domain = make_domain("Twice")
        container = DocumentContainer.objects.create(name="Once", folder=domain)
        start_instance(self._flow(domain, container, name="First"))
        second = start_instance(self._flow(domain, container, name="Second"))
        assert second.status == WorkflowInstance.Status.FAILED
        assert ManagedDocument.objects.filter(container=container).count() == 1

    def test_a_container_outside_the_scope_is_refused(self):
        domain = make_domain("Here")
        elsewhere = make_domain("Elsewhere")
        container = DocumentContainer.objects.create(name="Foreign", folder=elsewhere)
        instance = start_instance(self._flow(domain, container, name="Foreign"))
        assert instance.status == WorkflowInstance.Status.FAILED
        assert not ManagedDocument.objects.filter(container=container).exists()

    def test_a_missing_container_is_caught_at_publish(self):
        """The column is nullable, so only the registry says a run may not
        create a document without one."""
        from automation.workflows.actions import validate_create_config
        from automation.workflows.models import WorkflowNode

        codes = {
            code
            for code, _message in validate_create_config(
                WorkflowNode(
                    action_config={
                        "type": "create_object",
                        "model": "managed_document",
                        "fields": {"name": "Orphan"},
                    }
                )
            )
        }
        assert "action_create_missing_fk" in codes

    def test_the_folder_it_lands_in_needs_the_create_permission(self):
        """A built model lands where its parent is — here the container's
        domain — which authorize_action never saw: it cleared the action
        against the workflow's own folder."""
        from automation.workflows import authz

        domain = make_domain("Publishes here")
        child = make_domain("Read-only corner", parent=domain)
        container = DocumentContainer.objects.create(name="Locked", folder=child)
        version = self._flow(domain, container, name="Locked")
        real_can = authz.can
        authz.can = lambda user, codename, folder: (
            False if folder == child else real_can(user, codename, folder)
        )
        try:
            instance = start_instance(version)
        finally:
            authz.can = real_can

        assert instance.status == WorkflowInstance.Status.FAILED
        assert not ManagedDocument.objects.filter(container=container).exists()
        # The constructor writes the first revision in the same breath.
        assert not DocumentRevision.objects.filter(
            document__container=container
        ).exists()

    def test_it_declares_the_revision_permission_it_needs(self):
        """The constructor writes a revision on every run, not only when a
        field asks for one."""
        assert set(
            required_permissions(
                {"type": "create_object", "model": "managed_document", "fields": {}}
            )
        ) == {"add_manageddocument", "add_documentrevision"}


@pytest.mark.django_db
class TestOpeningTheNextDraft:
    def _flow(self, folder, document, **fields):
        return action_flow(
            folder,
            {
                "type": "create_object",
                "model": "document_revision",
                "fields": {"document": str(document.id), **fields},
            },
        )

    def test_a_new_draft_clones_what_is_current_and_takes_the_next_number(self):
        domain = make_domain("Next draft")
        _container, document, _revision = make_document(domain)
        instance = start_instance(self._flow(domain, document, change_summary="Review"))
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        draft = document.revisions.get(status=DocumentRevision.Status.DRAFT)
        assert draft.version_number == 2
        assert draft.content == "# Access control\n\nOriginal."
        assert draft.change_summary == "Review"
        # The published one still serves until someone publishes the draft.
        document.refresh_from_db()
        assert document.current_revision.version_number == 1

    def test_content_supplied_replaces_the_clone(self):
        domain = make_domain("Fresh text")
        _container, document, _revision = make_document(domain)
        instance = start_instance(self._flow(domain, document, content="# Rewritten"))
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        assert document.revisions.first().content == "# Rewritten"

    def test_only_one_draft_may_be_open(self):
        domain = make_domain("One draft")
        _container, document, _revision = make_document(domain)
        start_instance(self._flow(domain, document))
        second = start_instance(self._flow(domain, document))
        assert second.status == WorkflowInstance.Status.FAILED
        assert (
            document.revisions.filter(status=DocumentRevision.Status.DRAFT).count() == 1
        )

    def test_the_revision_is_named_by_its_version(self):
        """A built model need not have a `name` column."""
        domain = make_domain("Naming")
        _container, document, _revision = make_document(domain)
        instance = start_instance(self._flow(domain, document))
        assert instance.node_outputs["do_it"]["created_object_name"].endswith("v2")


@pytest.mark.django_db
class TestRewritingADraft:
    def _flow(self, folder, revision, **fields):
        return action_flow(
            folder,
            {
                "type": "update_object",
                "model": "document_revision",
                "id": str(revision.id),
                "fields": fields,
            },
        )

    def test_a_draft_takes_new_markdown(self):
        domain = make_domain("Rewrite")
        _container, document, _published = make_document(domain)
        draft = DocumentRevision.objects.create(
            document=document, version_number=2, content="old"
        )
        instance = start_instance(
            self._flow(domain, draft, content="# New", change_summary="Redrafted")
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        draft.refresh_from_db()
        assert (draft.content, draft.change_summary) == ("# New", "Redrafted")

    def test_a_published_revision_is_a_record_not_a_draft(self):
        domain = make_domain("Published")
        _container, _document, published = make_document(domain)
        instance = start_instance(self._flow(domain, published, content="# Tampered"))
        assert instance.status == WorkflowInstance.Status.FAILED
        published.refresh_from_db()
        assert published.content == "# Access control\n\nOriginal."

    def test_the_refusal_says_why(self):
        domain = make_domain("Why")
        _container, _document, published = make_document(domain)
        instance = start_instance(self._flow(domain, published, content="# Tampered"))
        said = " ".join(
            [token.error_message for token in instance.tokens.all()]
            + [f"{entry.message} {entry.data}" for entry in instance.logs.all()]
        )
        assert "only rewritable while it is being drafted" in said

    def test_a_revision_sent_back_for_changes_is_still_being_drafted(self):
        """The fence matches doc_management's own perform_update, which lets an
        author keep working on a revision a reviewer returned."""
        domain = make_domain("Change requested")
        _container, document, _published = make_document(domain)
        returned = DocumentRevision.objects.create(
            document=document,
            version_number=2,
            content="old",
            status=DocumentRevision.Status.CHANGE_REQUESTED,
        )
        instance = start_instance(self._flow(domain, returned, content="# Reworked"))
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        returned.refresh_from_db()
        assert returned.content == "# Reworked"

    def test_the_rewrite_lands_in_the_document_history(self):
        """The editor snapshots every content change; a run's rewrite has to
        appear in the same place or the only trace is the revision itself."""
        domain = make_domain("History")
        _container, document, _published = make_document(domain)
        draft = DocumentRevision.objects.create(
            document=document, version_number=2, content="old"
        )
        start_instance(self._flow(domain, draft, content="# Newer"))
        edit = DocumentEdit.objects.get(revision=draft)
        assert edit.content_snapshot == "# Newer"
        assert edit.editor == publisher_user()

    def test_a_returned_revision_is_rewritten_without_a_snapshot(self):
        """doc_management snapshots drafts only. A run following the same rule
        is the point of sharing record_document_edit with the editor."""
        domain = make_domain("Returned history")
        _container, document, _published = make_document(domain)
        returned = DocumentRevision.objects.create(
            document=document,
            version_number=2,
            content="old",
            status=DocumentRevision.Status.CHANGE_REQUESTED,
        )
        start_instance(self._flow(domain, returned, content="# Reworked"))
        assert not DocumentEdit.objects.filter(revision=returned).exists()

    def test_the_history_keeps_the_same_number_of_entries_as_the_editor(self):
        from doc_management.models import MAX_EDITS_PER_REVISION

        domain = make_domain("Capped history")
        _container, document, _published = make_document(domain)
        draft = DocumentRevision.objects.create(
            document=document, version_number=2, content="old"
        )
        for pass_ in range(MAX_EDITS_PER_REVISION + 3):
            start_instance(self._flow(domain, draft, content=f"# Pass {pass_}"))
        assert (
            DocumentEdit.objects.filter(revision=draft).count()
            == MAX_EDITS_PER_REVISION
        )

    def test_rewriting_with_the_same_markdown_adds_nothing(self):
        domain = make_domain("Same markdown")
        _container, document, _published = make_document(domain)
        draft = DocumentRevision.objects.create(
            document=document, version_number=2, content="# Same"
        )
        start_instance(self._flow(domain, draft, content="# Same"))
        assert not DocumentEdit.objects.filter(revision=draft).exists()

    def test_a_metadata_only_write_leaves_no_snapshot(self):
        domain = make_domain("No snapshot")
        _container, document, _published = make_document(domain)
        draft = DocumentRevision.objects.create(
            document=document, version_number=2, content="old"
        )
        start_instance(self._flow(domain, draft, change_summary="Just a note"))
        assert not DocumentEdit.objects.filter(revision=draft).exists()

    def test_a_run_cannot_move_a_revision_through_its_lifecycle(self):
        """publish() deprecates the revision it replaces and repoints the
        document; a column write would do neither."""
        entry = UPDATABLE_MODELS["document_revision"]
        assert "status" not in entry.fields
        assert "published_at" not in entry.fields
        assert "reviewer" not in entry.fields

    def test_a_run_cannot_repoint_which_revision_is_served(self):
        assert "current_revision" not in UPDATABLE_MODELS["managed_document"].fields


@pytest.mark.django_db
class TestReadingDocuments:
    def read_flow(self, folder, config):
        workflow = Workflow.objects.create(name=f"Read {uuid.uuid4()}", folder=folder)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
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
            },
        )
        return version

    def test_a_document_reads_like_the_editor_shows_it(self):
        domain = make_domain("Catalog")
        _container, document, revision = make_document(domain)
        instance = start_instance(
            self.read_flow(domain, {"model": "managed_document", "mode": "list"})
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        row = instance.node_outputs["fetch_rows"]["results"][0]
        # The variant has no title of its own; the container names it.
        assert row["name"] == "Access control"
        assert row["document_type"] == DocumentContainer.DocumentType.POLICY
        assert row["current_revision"]["version_number"] == 1
        assert row["current_revision"]["id"] == str(revision.id)
        assert row["container"]["id"] == str(document.container_id)

    def test_the_markdown_itself_is_readable(self):
        domain = make_domain("Content")
        make_document(domain)
        instance = start_instance(
            self.read_flow(domain, {"model": "document_revision", "mode": "first"})
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED
        row = instance.node_outputs["fetch_rows"]["object"]
        assert row["content"] == "# Access control\n\nOriginal."
        assert row["version_number"] == 1

    def test_more_rows_do_not_cost_more_queries(self):
        """Both entries' computed values dereference relations per row — the
        document its container and current revision, the revision its document
        and that document's container. Measured as a delta between two sizes:
        a run is an engine, an authorization kernel and a log, none of which is
        what this is about."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def queries_for(model, rows):
            domain = make_domain(f"Scale {model} {rows}")
            for index in range(rows):
                make_document(domain, content=f"# Doc {index}", name=f"Doc {index}")
            version = self.read_flow(domain, {"model": model, "mode": "list"})
            with CaptureQueriesContext(connection) as captured:
                instance = start_instance(version)
            assert instance.node_outputs["fetch_rows"]["count"] == rows
            return len(captured)

        for model in ("managed_document", "document_revision"):
            small = queries_for(model, 2)
            large = queries_for(model, 6)
            assert large - small <= 2, f"{model}: {small} for 2 rows, {large} for 6"

    def test_another_domain_is_not_in_scope(self):
        domain = make_domain("Mine")
        make_document(make_domain("Theirs"))
        instance = start_instance(
            self.read_flow(domain, {"model": "managed_document", "mode": "list"})
        )
        assert instance.node_outputs["fetch_rows"]["count"] == 0


@pytest.mark.django_db
class TestTheAuditLogStaysProportionate:
    """Registering the document models puts a log row — and the event
    producer's trigger match — on every document write. The editor autosaves a
    draft constantly, so the hot path had better not reach either."""

    def entries_for(self, revision):
        from auditlog.models import LogEntry

        return LogEntry.objects.get_for_object(revision).count()

    def test_a_content_only_save_writes_no_log_row(self):
        domain = make_domain("Autosave")
        _container, document, _published = make_document(domain)
        draft = DocumentRevision.objects.create(
            document=document, version_number=2, content="draft"
        )
        before = self.entries_for(draft)
        for index in range(5):
            draft.content = f"draft {index}"
            draft.save()
        assert self.entries_for(draft) == before

    def test_a_lifecycle_move_does_write_one(self):
        """What the log is for: the revision going somewhere, not the prose
        changing under it."""
        domain = make_domain("Submitted")
        _container, document, _published = make_document(domain)
        draft = DocumentRevision.objects.create(
            document=document, version_number=2, content="draft"
        )
        before = self.entries_for(draft)
        draft.status = DocumentRevision.Status.IN_REVIEW
        draft.save()
        assert self.entries_for(draft) == before + 1


class TestDocumentsAreTriggerable:
    """Internal-event triggers derive from the auditlog registry, so registering
    the document models is what puts them on the trigger list."""

    def test_the_lifecycle_has_event_keys(self):
        from automation.workflows.events import event_key_catalog

        keys = {row["key"] for row in event_key_catalog()}
        assert {
            "documentcontainer.created",
            "manageddocument.created",
            "documentrevision.created",
            "documentrevision.updated",
        } <= keys

    @pytest.mark.django_db
    def test_a_document_run_knows_what_it_is_about(self):
        """The subject of a run is resolved from the event key, and it is where
        objects the run creates land — so the lookup has to know the app."""
        from types import SimpleNamespace

        from automation.workflows.actions import _triggering_object

        container = DocumentContainer.objects.create(
            name="Subject", folder=make_domain("Subject")
        )
        instance = SimpleNamespace(
            payload={"id": str(container.id)},
            variables={},
            trigger_registration=SimpleNamespace(event_key="documentcontainer.created"),
        )
        assert _triggering_object(instance) == container


@pytest.mark.django_db
class TestAiMayWriteTheDraft:
    """The point of the enabler: markdown is free text, so a drafted revision is
    the one place an AI answer belongs verbatim — and it lands in a draft, which
    a human still has to publish."""

    def published(self, update_fields):
        workflow = Workflow.objects.create(
            name="Draft it", folder=Folder.get_root_folder()
        )
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        draft = node(
            "action",
            ref="draft",
            action_config={
                "type": "ai_generate",
                "prompt": "Draft the access control policy",
            },
        )
        write = node(
            "action",
            ref="write",
            action_config={
                "type": "update_object",
                "model": "document_revision",
                "id": "{{revision_id}}",
                "fields": update_fields,
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, draft, write, end],
                "edges": [edge(start, draft), edge(draft, write), edge(write, end)],
                "variables": [
                    {"id": str(uuid.uuid4()), "key": "revision_id", "type": "string"}
                ],
            },
        )
        return version

    def codes(self, version):
        return {error["code"] for error in validate_graph(version)}

    def test_an_ai_draft_may_fill_the_content(self):
        version = self.published({"content": "{{nodes.draft.text}}"})
        assert "action_update_ai_value_on_fenced_field" not in self.codes(version)

    def test_it_may_fill_the_change_summary_too(self):
        version = self.published({"change_summary": "{{nodes.draft.text}}"})
        assert "action_update_ai_value_on_fenced_field" not in self.codes(version)


def test_renewing_the_editing_lock_raises_no_internal_event():
    """The editor renews its lock every few minutes. Tracking that would make
    each renewal a `documentrevision.updated` event, evaluated against every
    enabled trigger, for a field no workflow can act on."""
    from auditlog.registry import auditlog

    excluded = auditlog.get_model_fields(DocumentRevision)["exclude_fields"]
    assert {"editing_since", "editing_user"} <= set(excluded)
    # The lifecycle a trigger is actually after stays tracked.
    assert "status" not in excluded
