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
from workflows.models import Workflow, WorkflowEventTrigger, WorkflowVersion
from workflows.serializers import WorkflowEventTriggerWriteSerializer
from workflows.tasks import dispatch_internal_event_task


@pytest.fixture
def capture_runs(monkeypatch):
    launched = []
    monkeypatch.setattr(
        "workflows.tasks.run_instance_task",
        lambda instance_id: launched.append(instance_id),
    )
    return launched


def make_workflow(name="Event flow", folder=None, published=True):
    workflow = Workflow.objects.create(
        name=name, folder=folder or Folder.get_root_folder()
    )
    version = WorkflowVersion.objects.create(workflow=workflow)
    start = {"id": str(uuid.uuid4()), "type": "start", "position": {"x": 0, "y": 0}}
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
            "nodes": [start, log, end],
            "edges": [
                {"id": str(uuid.uuid4()), "source": start["id"], "target": log["id"]},
                {"id": str(uuid.uuid4()), "source": log["id"], "target": end["id"]},
            ],
            "variables": [],
        },
    )
    if published:
        version.publish()
    return workflow


def make_trigger(workflow, event_key="appliedcontrol.updated", **kwargs):
    return WorkflowEventTrigger.objects.create(
        name=f"trigger-{uuid.uuid4().hex[:6]}",
        workflow=workflow,
        event_key=event_key,
        **kwargs,
    )


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
class TestMatching:
    def test_key_match_and_mismatch(self, capture_runs):
        workflow = make_workflow()
        make_trigger(workflow, event_key="appliedcontrol.updated")
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
        workflow = make_workflow(folder=domain)
        make_trigger(workflow)

        inside = dispatch_internal_event(
            "appliedcontrol.updated", payload(folder=domain), str(domain.id)
        )
        assert len(inside) == 1
        outside = dispatch_internal_event(
            "appliedcontrol.updated", payload(folder=sibling), str(sibling.id)
        )
        assert not outside

    def test_transition_filter_matches_only_on_change(self, capture_runs):
        workflow = make_workflow()
        make_trigger(
            workflow,
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
        workflow = make_workflow()
        make_trigger(
            workflow,
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

        workflow = make_workflow()
        make_trigger(
            workflow,
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
        trigger = make_trigger(workflow)
        started = dispatch_internal_event(
            "appliedcontrol.updated",
            payload(changes={"status": ["--", "active"]}),
            None,
        )
        instance = started[0]
        assert instance.trigger == "internal_event"
        assert instance.event_trigger_id == trigger.id
        assert instance.trigger_depth == 1
        assert instance.payload["new_values"] == {"status": "active"}
        assert capture_runs == [str(instance.id)]
        trigger.refresh_from_db()
        assert trigger.last_result == WorkflowEventTrigger.Result.TRIGGERED
        assert trigger.trigger_count == 1
        assert trigger.last_triggered_at is not None

    def test_unpublished_and_disabled_skips(self, capture_runs):
        unpublished = make_workflow(published=False)
        trigger = make_trigger(unpublished)
        assert not dispatch_internal_event("appliedcontrol.updated", payload(), None)
        trigger.refresh_from_db()
        assert trigger.last_result == WorkflowEventTrigger.Result.SKIPPED_UNPUBLISHED

        published = make_workflow(name="Disabled flow")
        make_trigger(published, enabled=False)
        assert not dispatch_internal_event("appliedcontrol.updated", payload(), None)

    def test_depth_cap(self, capture_runs):
        workflow = make_workflow()
        trigger = make_trigger(workflow)
        started = dispatch_internal_event(
            "appliedcontrol.updated", payload(), None, origin_depth=MAX_TRIGGER_DEPTH
        )
        assert not started
        trigger.refresh_from_db()
        assert trigger.last_result == WorkflowEventTrigger.Result.SKIPPED_DEPTH

    def test_chain_depth_increments(self, capture_runs):
        workflow = make_workflow()
        make_trigger(workflow)
        started = dispatch_internal_event(
            "appliedcontrol.updated", payload(), None, origin_depth=2
        )
        assert started[0].trigger_depth == 3


@pytest.mark.django_db
class TestCudProducer:
    def test_end_to_end_from_auditlog(self, capture_runs):
        from auditlog.models import LogEntry

        workflow = make_workflow()
        make_trigger(
            workflow,
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
class TestSerializerValidation:
    def _validate(self, workflow, **overrides):
        data = {
            "name": "t",
            "workflow": str(workflow.id),
            "event_key": "appliedcontrol.updated",
            "filters": {},
            "enabled": True,
        }
        data.update(overrides)
        serializer = WorkflowEventTriggerWriteSerializer(data=data)
        return serializer.is_valid(), serializer.errors

    def test_valid_payload(self):
        workflow = make_workflow()
        ok, errors = self._validate(workflow)
        assert ok, errors

    def test_unknown_event_key_rejected(self):
        workflow = make_workflow()
        ok, errors = self._validate(workflow, event_key="nonexistent.exploded")
        assert not ok and "event_key" in errors

    def test_malformed_filters_rejected(self):
        workflow = make_workflow()
        ok, errors = self._validate(
            workflow,
            filters={"operator": "xor", "conditions": []},
        )
        assert not ok and "filters" in errors
        ok, errors = self._validate(
            workflow,
            filters={"conditions": [{"field": "", "op": "eq", "value": "x"}]},
        )
        assert not ok

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
        workflow = make_workflow(folder=domain)
        ok, errors = self._validate(
            workflow,
            filters={
                "operator": "and",
                "conditions": [
                    {"field": "folder", "op": "eq", "value": str(sibling.id)}
                ],
            },
        )
        assert not ok and "filters" in errors
