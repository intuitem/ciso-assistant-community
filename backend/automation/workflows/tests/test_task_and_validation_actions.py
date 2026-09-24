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
