"""One run per user action and object, and the bulk writes that used to reach
neither the audit trail nor the events."""

import uuid

import pytest
from auditlog.cid import correlation_id

from core.models import AppliedControl, ComplianceAssessment, Framework, Perimeter
from core.models import RequirementAssessment, RequirementNode
from core.utils import bulk_update_with_log
from iam.models import Folder
from automation.workflows.events import dispatch_internal_event, payload_from_log_entry
from automation.workflows.models import WorkflowInstance, WorkflowTrigger
from automation.workflows.tests.test_event_triggers import (  # noqa: F401
    capture_runs,
    get_registration,
    make_workflow,
    payload,
)


SAME_OBJECT = str(uuid.uuid4())


def event(cid=None, object_id=SAME_OBJECT, **kwargs):
    body = payload(object_id=object_id, **kwargs)
    body["cid"] = cid or ""
    return body


@pytest.mark.django_db
class TestCorrelationCoalescing:
    def test_one_object_in_one_user_action_starts_one_run(self, capture_runs):
        workflow = make_workflow()
        cid = str(uuid.uuid4())
        first = dispatch_internal_event("appliedcontrol.updated", event(cid), None)
        rest = [
            dispatch_internal_event("appliedcontrol.updated", event(cid), None)
            for _ in range(5)
        ]
        assert len(first) == 1
        assert all(started == [] for started in rest)
        assert WorkflowInstance.objects.count() == 1
        assert (
            get_registration(workflow).last_result
            == WorkflowTrigger.Result.SKIPPED_COALESCED
        )

    def test_a_bulk_over_several_objects_still_runs_per_object(self, capture_runs):
        """The key is the object too: a bulk edit that touches 3 rows in one
        request is 3 runs, not 1. Only repeats of the same row collapse."""
        make_workflow()
        cid = str(uuid.uuid4())
        for _ in range(3):
            dispatch_internal_event(
                "appliedcontrol.updated", event(cid, object_id=str(uuid.uuid4())), None
            )
        assert WorkflowInstance.objects.count() == 3

    def test_separate_user_actions_each_get_a_run(self, capture_runs):
        make_workflow()
        dispatch_internal_event(
            "appliedcontrol.updated", event(str(uuid.uuid4())), None
        )
        dispatch_internal_event(
            "appliedcontrol.updated", event(str(uuid.uuid4())), None
        )
        assert WorkflowInstance.objects.count() == 2

    def test_events_without_a_correlation_id_are_not_coalesced(self, capture_runs):
        """Nothing to group by, so nothing may be dropped."""
        make_workflow()
        dispatch_internal_event("appliedcontrol.updated", event(""), None)
        dispatch_internal_event("appliedcontrol.updated", event(""), None)
        assert WorkflowInstance.objects.count() == 2

    def test_the_run_records_which_action_it_reacted_to(self, capture_runs):
        make_workflow()
        cid = str(uuid.uuid4())
        [instance] = dispatch_internal_event("appliedcontrol.updated", event(cid), None)
        assert instance.trigger_cid == cid
        assert instance.payload["cid"] == cid

    def test_coalescing_expires_so_a_reused_id_cannot_silence_a_trigger(
        self, capture_runs
    ):
        """The cid can come from an inbound header, so a client reusing one
        must not suppress a trigger for good."""
        from datetime import timedelta

        from django.utils import timezone

        from automation.workflows.events import COALESCE_WINDOW

        make_workflow()
        cid = "constant-header-value"
        dispatch_internal_event("appliedcontrol.updated", event(cid), None)
        WorkflowInstance.objects.update(
            created_at=timezone.now() - COALESCE_WINDOW - timedelta(minutes=1)
        )
        dispatch_internal_event("appliedcontrol.updated", event(cid), None)
        assert WorkflowInstance.objects.count() == 2

    def test_coalescing_is_per_trigger_not_global(self, capture_runs):
        make_workflow(name="First")
        make_workflow(name="Second")
        cid = str(uuid.uuid4())
        started = dispatch_internal_event("appliedcontrol.updated", event(cid), None)
        # Two workflows listening to the same event both run: they are
        # different subscribers, not a repeat of the same one.
        assert len(started) == 2


@pytest.mark.django_db
class TestBulkUpdateEmitsEvents:
    """bulk_update skips post_save, so these writes were invisible."""

    def make_audit(self, folder):
        framework = Framework.objects.create(
            name="FW", urn=f"urn:test:{uuid.uuid4()}", folder=Folder.get_root_folder()
        )
        requirements = [
            RequirementNode.objects.create(
                name=f"Req {index}",
                urn=f"urn:test:{uuid.uuid4()}:r{index}",
                framework=framework,
                assessable=True,
                folder=Folder.get_root_folder(),
            )
            for index in range(3)
        ]
        perimeter = Perimeter.objects.create(name="P", folder=folder)
        audit = ComplianceAssessment.objects.create(
            name="Audit", framework=framework, perimeter=perimeter, folder=folder
        )
        return [
            RequirementAssessment.objects.create(
                compliance_assessment=audit,
                requirement=requirement,
                folder=folder,
                result="not_assessed",
            )
            for requirement in requirements
        ]

    def test_bulk_update_with_log_writes_one_entry_per_changed_row(self):
        from auditlog.models import LogEntry

        folder = Folder.objects.create(
            name=f"Bulk {uuid.uuid4()}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        rows = self.make_audit(folder)
        for row in rows[:2]:
            row.result = "non_compliant"
        logged = bulk_update_with_log(RequirementAssessment, rows, ["result"])
        # The untouched third row diffs to nothing and is not logged.
        assert logged == 2
        entries = LogEntry.objects.filter(
            object_pk__in=[str(row.pk) for row in rows[:2]],
            action=LogEntry.Action.UPDATE,
        )
        assert entries.count() == 2
        entry = entries.first()
        assert entry.changes_dict["result"][1] == "non_compliant"
        assert entry.additional_data.get("folder_id") == str(folder.id)
        assert RequirementAssessment.objects.filter(result="non_compliant").count() == 2

    def test_the_entries_are_shaped_for_the_event_producer(self):
        from auditlog.models import LogEntry

        folder = Folder.objects.create(
            name=f"Shape {uuid.uuid4()}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        rows = self.make_audit(folder)
        rows[0].result = "compliant"
        token = correlation_id.set("one-merge")
        try:
            bulk_update_with_log(RequirementAssessment, rows, ["result"])
        finally:
            correlation_id.reset(token)
        entry = LogEntry.objects.filter(
            object_pk=str(rows[0].pk), action=LogEntry.Action.UPDATE
        ).first()
        body = payload_from_log_entry(entry)
        assert body["event_key"] == "requirementassessment.updated"
        assert body["new_values"]["result"] == "compliant"
        assert body["folder_id"] == str(folder.id)
        # The bulk write carries the request's correlation id, which is the
        # only field the coalescing path reads.
        assert body["cid"] == "one-merge"

    def test_a_bare_bulk_update_still_says_nothing(self):
        """The contrast, and the creation-time paths that keep the bare call."""
        from auditlog.models import LogEntry

        folder = Folder.objects.create(
            name=f"Silent {uuid.uuid4()}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        rows = self.make_audit(folder)
        before = LogEntry.objects.filter(action=LogEntry.Action.UPDATE).count()
        for row in rows:
            row.result = "compliant"
        RequirementAssessment.objects.bulk_update(rows, ["result"])
        assert LogEntry.objects.filter(action=LogEntry.Action.UPDATE).count() == before

    def test_nothing_to_do_is_cheap(self):
        assert bulk_update_with_log(AppliedControl, [], ["status"]) == 0
