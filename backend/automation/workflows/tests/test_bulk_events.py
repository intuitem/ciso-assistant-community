"""Bulk-write event seam: QuerySet.update()/bulk_update() bypass auditlog,
so the CUD producer never sees them. snapshot_for_bulk_events/emit_bulk_events
is the explicit replacement at the call sites that matter to workflows."""

import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import AppliedControl, Severity, Vulnerability
from iam.models import Folder
from automation.workflows.engine import current_trigger_depth
from automation.workflows.events import (
    dispatch_internal_event,
    emit_bulk_events,
    snapshot_for_bulk_events,
)
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowVersion
from automation.workflows.tests.helpers import publisher_user


@pytest.fixture
def capture_bulk(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "automation.workflows.tasks.dispatch_bulk_event_task",
        lambda payload, origin_depth=0: calls.append((payload, origin_depth)),
    )
    return calls


@pytest.fixture
def dispatch_bulk_inline(monkeypatch):
    """Run the bulk dispatch synchronously (huey is not immediate in tests).
    Returns the (payload, started instances) record for diagnostics."""
    record = []

    def _run(payload, origin_depth=0):
        started = dispatch_internal_event(
            payload["event_key"],
            payload,
            payload.get("folder_id"),
            origin_depth=origin_depth,
        )
        record.append((payload, started))

    monkeypatch.setattr(
        "automation.workflows.tasks.dispatch_bulk_event_task",
        _run,
    )
    return record


@pytest.fixture
def capture_runs(monkeypatch):
    launched = []
    monkeypatch.setattr(
        "automation.workflows.tasks.run_instance_task",
        lambda instance_id: launched.append(instance_id),
    )
    return launched


def make_workflow(event_key, filters=None, folder=None):
    """Published workflow with an armed internal-event trigger (ref
    'on_event'), same shape as in test_event_triggers."""
    workflow = Workflow.objects.create(
        name=f"Bulk flow {uuid.uuid4().hex[:6]}",
        folder=folder or Folder.get_root_folder(),
    )
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
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
                {"id": str(uuid.uuid4()), "source": trigger["id"], "target": log["id"]},
                {"id": str(uuid.uuid4()), "source": log["id"], "target": end["id"]},
            ],
            "variables": [],
        },
    )
    version.publish(publisher_user())
    workflow.triggers.filter(node_ref="on_event").update(enabled=True)
    return workflow


def make_domain(name):
    return Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.mark.django_db
class TestBulkEventSeam:
    def test_gate_short_circuits_with_one_query(self, django_assert_num_queries):
        AppliedControl.objects.create(name="C", folder=Folder.get_root_folder())
        queryset = AppliedControl.objects.all()
        with django_assert_num_queries(1):
            snapshot = snapshot_for_bulk_events(queryset, ["status"])
        assert snapshot is None
        with django_assert_num_queries(0):
            emit_bulk_events(snapshot)

    def test_payload_matches_auditlog_shape(
        self, capture_bulk, django_capture_on_commit_callbacks
    ):
        make_workflow("appliedcontrol.updated")
        folder = Folder.get_root_folder()
        control = AppliedControl.objects.create(name="C", folder=folder, status="to_do")
        queryset = AppliedControl.objects.filter(pk=control.pk)
        with django_capture_on_commit_callbacks(execute=True):
            snapshot = snapshot_for_bulk_events(queryset, ["status"])
            assert snapshot is not None
            queryset.update(status="active")
            emit_bulk_events(snapshot)
        assert len(capture_bulk) == 1
        payload, depth = capture_bulk[0]
        assert depth == 0
        assert payload["event_key"] == "appliedcontrol.updated"
        assert payload["model"] == "appliedcontrol"
        assert payload["app_label"] == "core"
        assert payload["operation"] == "updated"
        assert payload["object_id"] == str(control.pk)
        assert payload["object_repr"] == "C"
        assert payload["changes"] == {"status": ["to_do", "active"]}
        assert payload["new_values"] == {"status": "active"}
        assert payload["folder_id"] == str(folder.id)
        assert payload["actor_email"] is None
        assert payload["timestamp"]

    def test_unchanged_objects_are_dropped(
        self, capture_bulk, django_capture_on_commit_callbacks
    ):
        make_workflow("appliedcontrol.updated")
        folder = Folder.get_root_folder()
        changed = AppliedControl.objects.create(
            name="Changed", folder=folder, status="to_do"
        )
        AppliedControl.objects.create(name="Same", folder=folder, status="active")
        queryset = AppliedControl.objects.all()
        with django_capture_on_commit_callbacks(execute=True):
            snapshot = snapshot_for_bulk_events(queryset, ["status"])
            queryset.update(status="active")
            emit_bulk_events(snapshot)
        assert [p["object_id"] for p, _ in capture_bulk] == [str(changed.pk)]

    def test_folder_id_is_per_object(
        self, capture_bulk, django_capture_on_commit_callbacks
    ):
        make_workflow("appliedcontrol.updated")
        domain_a = make_domain("Bulk domain A")
        domain_b = make_domain("Bulk domain B")
        AppliedControl.objects.create(name="A", folder=domain_a, status="to_do")
        AppliedControl.objects.create(name="B", folder=domain_b, status="to_do")
        queryset = AppliedControl.objects.all()
        with django_capture_on_commit_callbacks(execute=True):
            snapshot = snapshot_for_bulk_events(queryset, ["status"])
            queryset.update(status="active")
            emit_bulk_events(snapshot)
        folder_ids = {p["object_repr"]: p["folder_id"] for p, _ in capture_bulk}
        assert folder_ids == {"A": str(domain_a.id), "B": str(domain_b.id)}

    def test_trigger_depth_is_propagated(
        self, capture_bulk, django_capture_on_commit_callbacks
    ):
        make_workflow("appliedcontrol.updated")
        control = AppliedControl.objects.create(
            name="C", folder=Folder.get_root_folder(), status="to_do"
        )
        queryset = AppliedControl.objects.filter(pk=control.pk)
        token = current_trigger_depth.set(2)
        try:
            with django_capture_on_commit_callbacks(execute=True):
                snapshot = snapshot_for_bulk_events(queryset, ["status"])
                queryset.update(status="active")
                emit_bulk_events(snapshot)
        finally:
            current_trigger_depth.reset(token)
        assert [depth for _, depth in capture_bulk] == [2]

    def test_none_snapshot_is_a_noop(self):
        emit_bulk_events(None)


@pytest.mark.django_db
class TestBulkEventEndToEnd:
    def test_scoring_toggle_fires_is_scored_transition_trigger(
        self, dispatch_bulk_inline, capture_runs, django_capture_on_commit_callbacks
    ):
        from core.models import (
            ComplianceAssessment,
            Framework,
            Perimeter,
            RequirementAssessment,
            RequirementNode,
        )
        from core.serializers import ComplianceAssessmentWriteSerializer
        from core.utils import HIDDEN

        domain = make_domain("Bulk domain audit")
        framework = Framework.objects.create(
            name="FW", urn="urn:test:bulk:fw", folder=Folder.get_root_folder()
        )
        requirements = [
            RequirementNode.objects.create(
                name=f"Req {i}",
                urn=f"urn:test:bulk:fw:req{i}",
                framework=framework,
                assessable=True,
                folder=Folder.get_root_folder(),
            )
            for i in range(2)
        ]
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        assessment = ComplianceAssessment.objects.create(
            name="Audit",
            framework=framework,
            perimeter=perimeter,
            folder=domain,
            scoring_enabled=True,
        )
        for requirement in requirements:
            RequirementAssessment.objects.create(
                compliance_assessment=assessment,
                requirement=requirement,
                folder=domain,
                is_scored=True,
                score=2,
            )
        make_workflow(
            "requirementassessment.updated",
            filters={
                "operator": "and",
                "conditions": [
                    {
                        "field": "is_scored",
                        "op": "eq",
                        "value": "False",
                        "changed": True,
                    }
                ],
            },
            folder=domain,
        )

        # scoring_enabled is a derived property; the API toggles it by
        # PATCHing field_visibility (hide score/is_scored for every role).
        serializer = ComplianceAssessmentWriteSerializer(
            instance=assessment,
            data={"field_visibility": {"score": HIDDEN, "is_scored": HIDDEN}},
            partial=True,
            context={"request": None},
        )
        assert serializer.is_valid(), serializer.errors
        with django_capture_on_commit_callbacks(execute=True):
            serializer.save()

        # One run per requirement assessment whose is_scored flipped.
        assert len(capture_runs) == 2

    def test_refresh_due_dates_fires_vulnerability_trigger(
        self, dispatch_bulk_inline, capture_runs, django_capture_on_commit_callbacks
    ):
        from core.views import VulnerabilityViewSet
        from global_settings.models import GlobalSettings

        sla, _ = GlobalSettings.objects.get_or_create(name="vulnerability-sla")
        sla.value = {"sla_anchor": "detected_at", "low": 30}
        sla.save()
        domain = make_domain("Bulk domain vulns")
        vulnerability = Vulnerability.objects.create(
            name="V",
            folder=domain,
            severity=Severity.LOW,
            detected_at=timezone.now(),
        )
        # save() already applied the SLA on create; blank the due date the
        # bulk way (no signals) so the refresh has real drift to correct.
        Vulnerability.objects.filter(pk=vulnerability.pk).update(due_date=None)
        make_workflow(
            "vulnerability.updated",
            filters={
                "operator": "and",
                "conditions": [
                    {"field": "due_date", "op": "neq", "value": "", "changed": True}
                ],
            },
            folder=domain,
        )

        request = APIRequestFactory().post("/vulnerabilities/refresh-due-dates/")
        force_authenticate(request, user=publisher_user())
        with django_capture_on_commit_callbacks(execute=True):
            response = VulnerabilityViewSet.as_view({"post": "refresh_due_dates"})(
                request
            )
        assert response.status_code == 200
        assert response.data["updated"] == 1
        assert len(capture_runs) == 1, dispatch_bulk_inline
