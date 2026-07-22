import uuid

import pytest

from core.models import AppliedControl, FilteringLabel
from iam.models import Folder
from workflows.events import (
    MAX_TRIGGER_DEPTH,
    dispatch_internal_event,
    event_key_catalog,
)
from workflows.graph import save_graph
from workflows.models import Workflow, WorkflowTrigger, WorkflowVersion
from workflows.tasks import dispatch_internal_event_task
from workflows.validation import validate_graph


@pytest.fixture
def capture_runs(monkeypatch):
    launched = []
    monkeypatch.setattr(
        "workflows.tasks.run_instance_task",
        lambda instance_id: launched.append(instance_id),
    )
    return launched


def make_workflow(
    name="Event flow",
    folder=None,
    published=True,
    event_key="appliedcontrol.updated",
    filters=None,
    enabled=True,
):
    """A workflow entered by an internal-event trigger node (ref 'on_event').
    Publishing creates the registration row (disabled by default); dispatch
    tests arm it explicitly."""
    workflow = Workflow.objects.create(
        name=name, folder=folder or Folder.get_root_folder()
    )
    version = WorkflowVersion.objects.create(workflow=workflow)
    trigger_config = {"type": "internal_event", "event_key": event_key}
    if filters:
        trigger_config["filters"] = filters
    trigger = {
        "id": str(uuid.uuid4()),
        "type": "trigger",
        "ref": "on_event",
        "trigger_config": trigger_config,
        "position": {"x": 0, "y": 0},
    }
    log = {
        "id": str(uuid.uuid4()),
        "type": "action",
        "label": "Log",
        "action_config": {"type": "log", "message": "fired"},
        "position": {"x": 0, "y": 0},
    }
    end = {"id": str(uuid.uuid4()), "type": "end", "position": {"x": 0, "y": 0}}
    save_graph(
        version,
        {
            "nodes": [trigger, log, end],
            "edges": [
                {
                    "id": str(uuid.uuid4()),
                    "source": trigger["id"],
                    "target": log["id"],
                },
                {"id": str(uuid.uuid4()), "source": log["id"], "target": end["id"]},
            ],
            "variables": [],
        },
    )
    if published:
        version.publish()
        if enabled:
            workflow.triggers.filter(node_ref="on_event").update(enabled=True)
    return workflow


def get_registration(workflow):
    return workflow.triggers.get(node_ref="on_event")


def payload(
    operation="updated",
    changes=None,
    folder=None,
    model="appliedcontrol",
    object_id=None,
):
    changes = changes or {}
    return {
        "event_key": f"{model}.{operation}",
        "model": model,
        "operation": operation,
        "object_id": str(object_id or uuid.uuid4()),
        "object_repr": "Test object",
        "changes": changes,
        "new_values": {field: diff[1] for field, diff in changes.items()},
        "folder_id": str(folder.id) if folder else None,
        "actor_email": None,
        "timestamp": None,
    }


@pytest.mark.django_db
class TestRegistrationLifecycle:
    def test_publish_creates_disarmed_registration(self):
        workflow = make_workflow(enabled=False)
        row = get_registration(workflow)
        assert row.type == WorkflowTrigger.Type.INTERNAL_EVENT
        assert row.enabled is False
        assert row.event_key == "appliedcontrol.updated"
        assert row.config["type"] == "internal_event"

    def test_republish_preserves_enabled_and_snapshots_config(self):
        workflow = make_workflow()
        version = workflow.published_version
        draft = version.clone_as_draft()
        node = draft.nodes.get(ref="on_event")
        node.trigger_config = {
            "type": "internal_event",
            "event_key": "incident.created",
        }
        node.save(update_fields=["trigger_config", "updated_at"])
        draft.publish()
        row = get_registration(workflow)
        assert row.enabled is True
        assert row.event_key == "incident.created"


@pytest.mark.django_db
class TestMatching:
    def test_key_match_and_mismatch(self, capture_runs):
        make_workflow()
        started = dispatch_internal_event("appliedcontrol.updated", payload(), None)
        assert len(started) == 1
        assert not dispatch_internal_event("incident.created", payload(), None)

    def test_folder_subtree_containment(self, capture_runs):
        root = Folder.get_root_folder()
        domain = Folder.objects.create(
            name="EvtDomain", parent_folder=root, content_type=Folder.ContentType.DOMAIN
        )
        sibling = Folder.objects.create(
            name="EvtSibling",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        make_workflow(folder=domain)

        inside = dispatch_internal_event(
            "appliedcontrol.updated", payload(folder=domain), str(domain.id)
        )
        assert len(inside) == 1
        outside = dispatch_internal_event(
            "appliedcontrol.updated", payload(folder=sibling), str(sibling.id)
        )
        assert not outside

    def test_transition_filter_matches_only_on_change(self, capture_runs):
        make_workflow(
            filters={
                "operator": "and",
                "conditions": [
                    {"field": "status", "op": "eq", "value": "active", "changed": True}
                ],
            },
        )
        hit = dispatch_internal_event(
            "appliedcontrol.updated",
            payload(changes={"status": ["--", "active"]}),
            None,
        )
        assert len(hit) == 1
        # Field changed to a different value: no match.
        assert not dispatch_internal_event(
            "appliedcontrol.updated",
            payload(changes={"status": ["--", "deprecated"]}),
            None,
        )
        # Field not part of the diff at all: no match.
        assert not dispatch_internal_event(
            "appliedcontrol.updated",
            payload(changes={"description": ["a", "b"]}),
            None,
        )

    def test_state_filter_reads_live_object(self, capture_runs):
        control = AppliedControl.objects.create(
            name="Live control", folder=Folder.get_root_folder()
        )
        label = FilteringLabel.objects.create(
            label="bar", folder=Folder.get_root_folder()
        )
        control.filtering_labels.add(label)
        make_workflow(
            filters={
                "operator": "and",
                "conditions": [
                    {"field": "filtering_labels", "op": "contains", "value": "bar"}
                ],
            },
        )
        hit = dispatch_internal_event(
            "appliedcontrol.updated",
            payload(changes={"description": ["a", "b"]}, object_id=control.id),
            None,
        )
        assert len(hit) == 1

    def test_boolean_composition_canonical_example(self, capture_runs):
        """(folder = foo AND status != active) OR filtering_label = bar."""
        root = Folder.get_root_folder()
        foo = Folder.objects.create(
            name="foo", parent_folder=root, content_type=Folder.ContentType.DOMAIN
        )
        label = FilteringLabel.objects.create(label="bar", folder=root)

        in_foo_inactive = AppliedControl.objects.create(name="A", folder=foo)
        in_foo_active = AppliedControl.objects.create(
            name="B", folder=foo, status="active"
        )
        labeled_elsewhere = AppliedControl.objects.create(name="C", folder=root)
        labeled_elsewhere.filtering_labels.add(label)
        plain = AppliedControl.objects.create(name="D", folder=root)

        make_workflow(
            filters={
                "operator": "or",
                "conditions": [
                    {"field": "filtering_labels", "op": "contains", "value": "bar"}
                ],
                "children": [
                    {
                        "operator": "and",
                        "conditions": [
                            {"field": "folder", "op": "eq", "value": str(foo.id)},
                            {"field": "status", "op": "neq", "value": "active"},
                        ],
                    }
                ],
            },
        )

        def fire(control):
            return dispatch_internal_event(
                "appliedcontrol.updated",
                payload(
                    changes={"description": ["x", "y"]},
                    object_id=control.id,
                    folder=control.folder,
                ),
                str(control.folder_id),
            )

        assert len(fire(in_foo_inactive)) == 1  # left branch
        assert not fire(in_foo_active)  # folder matches, status excludes
        assert len(fire(labeled_elsewhere)) == 1  # right branch
        assert not fire(plain)  # neither


@pytest.mark.django_db
class TestDispatch:
    def test_instance_created_with_trigger_metadata(self, capture_runs):
        workflow = make_workflow()
        registration = get_registration(workflow)
        started = dispatch_internal_event(
            "appliedcontrol.updated",
            payload(changes={"status": ["--", "active"]}),
            None,
        )
        instance = started[0]
        assert instance.trigger == "internal_event"
        assert instance.trigger_registration_id == registration.id
        assert instance.trigger_depth == 1
        assert instance.payload["new_values"] == {"status": "active"}
        assert capture_runs == [str(instance.id)]
        entry_log = instance.logs.filter(event_type="instance_started").get()
        assert entry_log.node.ref == "on_event"
        registration.refresh_from_db()
        assert registration.last_result == WorkflowTrigger.Result.TRIGGERED
        assert registration.trigger_count == 1
        assert registration.last_triggered_at is not None

    def test_unpublished_and_disabled_skips(self, capture_runs):
        # Archiving the published version strands the registration row: the
        # dispatcher must record SKIPPED_UNPUBLISHED, not crash or fire.
        workflow = make_workflow()
        registration = get_registration(workflow)
        WorkflowVersion.objects.filter(id=workflow.published_version.id).update(
            status=WorkflowVersion.Status.ARCHIVED
        )
        assert not dispatch_internal_event("appliedcontrol.updated", payload(), None)
        registration.refresh_from_db()
        assert registration.last_result == WorkflowTrigger.Result.SKIPPED_UNPUBLISHED

        make_workflow(name="Disabled flow", enabled=False)
        assert not dispatch_internal_event("appliedcontrol.updated", payload(), None)

    def test_depth_cap(self, capture_runs):
        workflow = make_workflow()
        registration = get_registration(workflow)
        started = dispatch_internal_event(
            "appliedcontrol.updated", payload(), None, origin_depth=MAX_TRIGGER_DEPTH
        )
        assert not started
        registration.refresh_from_db()
        assert registration.last_result == WorkflowTrigger.Result.SKIPPED_DEPTH

    def test_chain_depth_increments(self, capture_runs):
        make_workflow()
        started = dispatch_internal_event(
            "appliedcontrol.updated", payload(), None, origin_depth=2
        )
        assert started[0].trigger_depth == 3


@pytest.mark.django_db
class TestCudProducer:
    def test_end_to_end_from_auditlog(self, capture_runs):
        from auditlog.models import LogEntry

        make_workflow(
            event_key="appliedcontrol.updated",
            filters={
                "operator": "and",
                "conditions": [
                    {"field": "status", "op": "eq", "value": "active", "changed": True}
                ],
            },
        )
        control = AppliedControl.objects.create(
            name="E2E control", folder=Folder.get_root_folder()
        )
        control.status = "active"
        control.save()

        log_entry = (
            LogEntry.objects.filter(
                object_pk=str(control.pk), action=LogEntry.Action.UPDATE
            )
            .order_by("-timestamp")
            .first()
        )
        assert log_entry is not None, "auditlog did not record the update"
        # Execute the task body directly (huey is not immediate in tests).
        dispatch_internal_event_task.call_local(log_entry.pk, 0)
        assert len(capture_runs) == 1

        # A no-op save produces no diff → no second run (transition semantics).
        control.save()
        later = (
            LogEntry.objects.filter(
                object_pk=str(control.pk), action=LogEntry.Action.UPDATE
            )
            .order_by("-timestamp")
            .first()
        )
        if later and later.pk != log_entry.pk:
            dispatch_internal_event_task.call_local(later.pk, 0)
        assert len(capture_runs) == 1

    def test_event_key_catalog_covers_registered_models(self):
        keys = {entry["key"] for entry in event_key_catalog()}
        assert "appliedcontrol.created" in keys
        assert "incident.updated" in keys
        assert "asset.deleted" in keys
        # Workflows' own models are excluded (no circular triggering).
        assert not any(key.startswith("workflowinstance.") for key in keys)


@pytest.mark.django_db
class TestConfigValidation:
    """Event key / filter validation moved from the trigger serializer to
    publish validation of the trigger node's config."""

    def _codes(self, trigger_config, folder=None):
        workflow = Workflow.objects.create(
            name=f"cfg {uuid.uuid4().hex[:6]}",
            folder=folder or Folder.get_root_folder(),
        )
        version = WorkflowVersion.objects.create(workflow=workflow)
        trigger = {
            "id": str(uuid.uuid4()),
            "type": "trigger",
            "trigger_config": trigger_config,
            "position": {},
        }
        end = {"id": str(uuid.uuid4()), "type": "end", "position": {}}
        save_graph(
            version,
            {
                "nodes": [trigger, end],
                "edges": [
                    {
                        "id": str(uuid.uuid4()),
                        "source": trigger["id"],
                        "target": end["id"],
                    }
                ],
                "variables": [],
            },
        )
        return [e["code"] for e in validate_graph(version)]

    def test_valid_config(self):
        codes = self._codes(
            {"type": "internal_event", "event_key": "appliedcontrol.updated"}
        )
        assert codes == []

    def test_unknown_event_key_rejected(self):
        codes = self._codes(
            {"type": "internal_event", "event_key": "nonexistent.exploded"}
        )
        assert "trigger_invalid_event_key" in codes

    def test_malformed_filters_rejected(self):
        codes = self._codes(
            {
                "type": "internal_event",
                "event_key": "appliedcontrol.updated",
                "filters": {"operator": "xor", "conditions": []},
            }
        )
        assert "trigger_invalid_filters" in codes
        codes = self._codes(
            {
                "type": "internal_event",
                "event_key": "appliedcontrol.updated",
                "filters": {"conditions": [{"field": "", "op": "eq", "value": "x"}]},
            }
        )
        assert "trigger_invalid_filters" in codes

    def test_folder_condition_outside_scope_rejected(self):
        root = Folder.get_root_folder()
        domain = Folder.objects.create(
            name="ScopeDomain",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        sibling = Folder.objects.create(
            name="ScopeSibling",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        codes = self._codes(
            {
                "type": "internal_event",
                "event_key": "appliedcontrol.updated",
                "filters": {
                    "operator": "and",
                    "conditions": [
                        {"field": "folder", "op": "eq", "value": str(sibling.id)}
                    ],
                },
            },
            folder=domain,
        )
        assert "trigger_filters_out_of_scope" in codes
