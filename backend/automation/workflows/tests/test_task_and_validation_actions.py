"""Tasks and validation flows as things a workflow may create.

Both are how a run hands work back to a person, so both can name that person —
`assigned_to` and `approver` are optional here exactly as they are on the
models, which is not this registry's call to overrule. The task carries its
occurrence, because the board and the reminders read TaskNode and a template on
its own shows nothing.
"""

import uuid
from datetime import date, timedelta

import pytest

from core.models import (
    AppliedControl,
    Actor,
    ComplianceAssessment,
    Evidence,
    Framework,
    Perimeter,
    TaskNode,
    TaskTemplate,
    ValidationFlow,
)
from iam.models import Folder, User
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowInstance, WorkflowVersion
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


def action_flow(folder, config):
    workflow = Workflow.objects.create(name=f"WF {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    act = node("action", label="Do it", action_config=config)
    end = node("end")
    save_graph(
        version,
        {"nodes": [start, act, end], "edges": [edge(start, act), edge(act, end)]},
    )
    return version


@pytest.fixture
def domain():
    return Folder.objects.create(
        name=f"tasks {uuid.uuid4()}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.fixture
def assignee(domain):
    user = User.objects.create(email=f"owner-{uuid.uuid4()}@test.example")
    return Actor.objects.get(user=user)


@pytest.mark.django_db
class TestCreatingATask:
    def test_the_template_arrives_with_its_occurrence(self, domain, assignee):
        due = date.today() + timedelta(days=14)
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "task_template",
                    "fields": {
                        "name": "Refresh the access review evidence",
                        "assigned_to": str(assignee.id),
                        "task_date": due.isoformat(),
                    },
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables

        template = TaskTemplate.objects.get(folder=domain)
        assert template.name == "Refresh the access review evidence"
        assert list(template.assigned_to.all()) == [assignee]
        assert template.is_recurrent is False

        # The board reads this, not the template.
        occurrence = TaskNode.objects.get(task_template=template)
        assert occurrence.due_date == due
        assert occurrence.scheduled_date == due
        assert occurrence.folder == domain

    def test_it_can_point_at_what_it_is_about(self, domain, assignee):
        control = AppliedControl.objects.create(name="Access review", folder=domain)
        evidence = Evidence.objects.create(name="Q3 export", folder=domain)
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "task_template",
                    "fields": {
                        "name": "Chase the export",
                        "assigned_to": str(assignee.id),
                        "applied_controls": str(control.id),
                        "evidences": str(evidence.id),
                    },
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        template = TaskTemplate.objects.get(folder=domain)
        assert list(template.applied_controls.all()) == [control]
        assert list(template.evidences.all()) == [evidence]

    def test_an_unassigned_task_is_allowed_and_still_gets_its_occurrence(self, domain):
        """The model leaves `assigned_to` blank-able, so a workflow may too. The
        occurrence is not optional in the same way — without it the task exists
        and is invisible."""
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "task_template",
                    "fields": {"name": "Unowned but visible"},
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        template = TaskTemplate.objects.get(folder=domain)
        assert list(template.assigned_to.all()) == []
        assert TaskNode.objects.filter(task_template=template).count() == 1

    def test_an_unknown_assignee_is_refused(self, domain):
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "task_template",
                    "fields": {"name": "Ghost", "assigned_to": str(uuid.uuid4())},
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        # Nothing half-made: the template is not created before the assignees
        # are resolved.
        assert not TaskTemplate.objects.filter(folder=domain).exists()


@pytest.mark.django_db
class TestCreatingAValidationFlow:
    @pytest.fixture
    def audit(self, domain):
        framework = Framework.objects.create(
            name="FW",
            urn=f"urn:test:vf:{uuid.uuid4()}",
            folder=Folder.get_root_folder(),
        )
        perimeter = Perimeter.objects.create(name="P", folder=domain)
        return ComplianceAssessment.objects.create(
            name="ISO 27001", framework=framework, perimeter=perimeter, folder=domain
        )

    def test_it_names_an_approver_and_a_subject(self, domain, audit):
        approver = User.objects.create(email=f"boss-{uuid.uuid4()}@test.example")
        deadline = date.today() + timedelta(days=7)
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "validation_flow",
                    "fields": {
                        "approver": str(approver.id),
                        "compliance_assessments": str(audit.id),
                        "validation_deadline": deadline.isoformat(),
                        "request_notes": "Evidence review complete; please sign off.",
                    },
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables

        flow = ValidationFlow.objects.get(folder=domain)
        assert flow.approver == approver
        # The run's identity asked, the same one its reads and writes use.
        assert flow.requester == publisher_user()
        assert list(flow.compliance_assessments.all()) == [audit]
        assert flow.validation_deadline == deadline
        assert flow.status == ValidationFlow.Status.SUBMITTED
        assert flow.ref_id.startswith("VAL.")

    def test_two_approvers_are_refused_rather_than_silently_halved(self, domain, audit):
        """`approver` is one FK column. Two ids would put one of them on the
        flow and drop the other without a word, leaving someone waiting on a
        request nobody sent them."""
        one = User.objects.create(email=f"a-{uuid.uuid4()}@test.example")
        two = User.objects.create(email=f"b-{uuid.uuid4()}@test.example")
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "validation_flow",
                    "fields": {
                        "approver": f"{one.id},{two.id}",
                        "compliance_assessments": str(audit.id),
                    },
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert not ValidationFlow.objects.filter(folder=domain).exists()


@pytest.mark.django_db
class TestTheSideEffectsTheEditorHas:
    """The registry writes through the ORM rather than the write serializers, so
    everything a serializer does besides the row has to be done here too. These
    pin the ones that were missed once already."""

    def test_assigning_a_task_tells_the_assignee(self, domain, assignee, monkeypatch):
        sent = []
        monkeypatch.setattr(
            "core.tasks.send_task_template_assignment_notification",
            lambda task_id, emails: sent.append((str(task_id), emails)),
        )
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "task_template",
                    "fields": {"name": "Tell them", "assigned_to": str(assignee.id)},
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        task = TaskTemplate.objects.get(folder=domain)
        assert sent and sent[0][0] == str(task.id)
        assert sent[0][1] == assignee.get_emails()

    def test_an_unassigned_task_tells_nobody(self, domain, monkeypatch):
        sent = []
        monkeypatch.setattr(
            "core.tasks.send_task_template_assignment_notification",
            lambda task_id, emails: sent.append(emails),
        )
        start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "task_template",
                    "fields": {"name": "Nobody"},
                },
            )
        )
        assert sent == []

    def test_a_periodic_run_updates_its_task_instead_of_piling_them_up(
        self, domain, assignee
    ):
        """`upsert` worked here before the task grew its occurrence, and a
        quarterly flow that duplicated its task every run would be useless."""
        first = date.today() + timedelta(days=7)
        later = date.today() + timedelta(days=97)

        def run(task_date):
            return start_instance(
                action_flow(
                    domain,
                    {
                        "type": "create_object",
                        "model": "task_template",
                        "upsert": True,
                        "fields": {
                            "name": "Quarterly access review",
                            "assigned_to": str(assignee.id),
                            "task_date": task_date.isoformat(),
                        },
                    },
                )
            )

        assert run(first).status == WorkflowInstance.Status.COMPLETED
        second = run(later)
        assert second.status == WorkflowInstance.Status.COMPLETED, second.variables

        template = TaskTemplate.objects.get(name="Quarterly access review")
        assert TaskTemplate.objects.filter(folder=domain).count() == 1
        assert template.task_date == later
        # The occurrence is re-dated, not doubled: the board shows one task.
        occurrence = TaskNode.objects.get(task_template=template)
        assert occurrence.due_date == later
        assert list(template.assigned_to.all()) == [assignee]

    def test_a_recurring_task_of_the_same_name_is_left_alone(self, domain):
        """A recurring template's occurrences come from its schedule. Matching
        one here would re-date every occurrence it has ever had, completed
        history included."""
        recurring = TaskTemplate.objects.create(
            name="Quarterly access review",
            folder=domain,
            is_recurrent=True,
            schedule={"interval": 1, "frequency": "MONTHLY"},
        )
        occurrence = TaskNode.objects.create(
            task_template=recurring,
            due_date=date.today() - timedelta(days=30),
            scheduled_date=date.today() - timedelta(days=30),
            folder=domain,
            status="completed",
        )
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "task_template",
                    "upsert": True,
                    "fields": {
                        "name": "Quarterly access review",
                        "task_date": (date.today() + timedelta(days=7)).isoformat(),
                    },
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        occurrence.refresh_from_db()
        assert occurrence.due_date == date.today() - timedelta(days=30)
        assert occurrence.status == "completed"
        # The one-off task is created beside it, not merged into it.
        assert TaskTemplate.objects.filter(name="Quarterly access review").count() == 2

    def test_an_update_that_names_no_date_keeps_the_one_there(self, domain):
        """Not setting `task_date` is not saying "no date"."""
        due = date.today() + timedelta(days=21)

        def run(fields):
            return start_instance(
                action_flow(
                    domain,
                    {
                        "type": "create_object",
                        "model": "task_template",
                        "upsert": True,
                        "fields": {"name": "Keep my date", **fields},
                    },
                )
            )

        run({"task_date": due.isoformat()})
        instance = run({"description": "Just a note"})
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables

        template = TaskTemplate.objects.get(name="Keep my date")
        assert template.task_date == due
        assert template.description == "Just a note"
        assert TaskNode.objects.get(task_template=template).due_date == due

    def test_the_second_run_says_it_did_not_create(self, domain):
        def run():
            return start_instance(
                action_flow(
                    domain,
                    {
                        "type": "create_object",
                        "model": "task_template",
                        "upsert": True,
                        "fields": {"name": "Same task"},
                    },
                )
            )

        run()
        instance = run()
        log = instance.logs.get(event_type="action_executed")
        assert log.data["created"] is False

    def test_an_assignee_is_named_the_way_a_person_names_them(self, domain, assignee):
        """An Actor has no name of its own, so it answers to the email of the
        user it wraps — what someone types in the builder."""
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "task_template",
                    "fields": {
                        "name": "By email",
                        "assigned_to": assignee.user.email,
                    },
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        assert list(TaskTemplate.objects.get(name="By email").assigned_to.all()) == [
            assignee
        ]

    def test_a_validation_flow_opens_with_its_submission_event(self, domain):
        from core.models import FlowEvent

        approver = User.objects.create(email=f"boss-{uuid.uuid4()}@test.example")
        framework = Framework.objects.create(
            name="FW",
            urn=f"urn:test:vf2:{uuid.uuid4()}",
            folder=Folder.get_root_folder(),
        )
        perimeter = Perimeter.objects.create(name="P2", folder=domain)
        audit = ComplianceAssessment.objects.create(
            name="ISO", framework=framework, perimeter=perimeter, folder=domain
        )
        instance = start_instance(
            action_flow(
                domain,
                {
                    "type": "create_object",
                    "model": "validation_flow",
                    "fields": {
                        "approver": approver.email,
                        "compliance_assessments": str(audit.id),
                        "request_notes": "Please sign off.",
                    },
                },
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        flow = ValidationFlow.objects.get(folder=domain)
        event = FlowEvent.objects.get(validation_flow=flow)
        assert event.event_type == ValidationFlow.Status.SUBMITTED
        assert event.event_notes == "Please sign off."
        assert event.folder == flow.folder
