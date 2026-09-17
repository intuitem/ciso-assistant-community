"""`attach_evidence` finding the occurrence a collected file answers for.

The owed occurrence's id changes every period, so it cannot be a setting — it
used to need a Read objects step in front of every collection graph. What it
must never do is decide the task is done.
"""

import uuid
from datetime import date, timedelta

import pytest

from core.models import Evidence, TaskNode, TaskTemplate
from iam.models import Folder
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowInstance, WorkflowVersion
from automation.workflows.tests.helpers import publisher_user

TODAY = date.today()


def node(type_, ref, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "ref": ref,
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target):
    return {"id": str(uuid.uuid4()), "source": source["id"], "target": target["id"]}


@pytest.fixture
def domain():
    return Folder.objects.create(
        name=f"Collection {uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.fixture
def evidence(domain):
    return Evidence.objects.create(name="Weekly export", folder=domain)


def a_task(domain, evidence, name="Collect the export"):
    task = TaskTemplate.objects.create(
        name=f"{name} {uuid.uuid4().hex[:4]}", folder=domain, task_date=TODAY
    )
    task.evidences.add(evidence)
    return task


def an_occurrence(task, domain, due, status="pending"):
    return TaskNode.objects.create(
        task_template=task, folder=domain, due_date=due, status=status
    )


def attach_flow(domain, evidence):
    """A collection told to find the occurrence itself."""
    workflow = Workflow.objects.create(name=f"Collect {uuid.uuid4()}", folder=domain)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node(
        "trigger",
        "start",
        trigger_config={"type": "manual"},
    )
    attach = node(
        "action",
        "attach",
        label="Collect",
        action_config={
            "type": "attach_evidence",
            "evidence": str(evidence.id),
            "source": "text",
            "text": "host,agent\nlaptop-01,ok\n",
            "filename": "export.csv",
            "new_revision": True,
            "find_occurrence": True,
        },
    )
    done = node("end", "done")
    save_graph(
        version,
        {
            "nodes": [start, attach, done],
            "edges": [edge(start, attach), edge(attach, done)],
        },
    )
    return version


def collected(domain, evidence):
    """Run one collection, hand back the attach output."""
    instance = start_instance(attach_flow(domain, evidence))
    assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
    return instance.node_outputs["attach"]


@pytest.mark.django_db
class TestOwedOccurrence:
    def test_it_answers_for_the_occurrence_that_is_due(self, domain, evidence):
        task = a_task(domain, evidence)
        owed = an_occurrence(task, domain, TODAY)
        assert collected(domain, evidence)["task_node_id"] == str(owed.id)

    def test_the_most_recent_due_period_wins_not_the_oldest(self, domain, evidence):
        """A period nobody closed must not swallow every later file."""
        task = a_task(domain, evidence)
        an_occurrence(task, domain, TODAY - timedelta(days=21))
        an_occurrence(task, domain, TODAY - timedelta(days=14))
        current = an_occurrence(task, domain, TODAY)
        assert collected(domain, evidence)["task_node_id"] == str(current.id)

    def test_in_progress_is_still_owed(self, domain, evidence):
        """Only completed and cancelled are settled."""
        task = a_task(domain, evidence)
        open_one = an_occurrence(task, domain, TODAY, status="in_progress")
        assert collected(domain, evidence)["task_node_id"] == str(open_one.id)

    def test_settled_occurrences_are_skipped(self, domain, evidence):
        task = a_task(domain, evidence)
        an_occurrence(task, domain, TODAY, status="completed")
        earlier = an_occurrence(task, domain, TODAY - timedelta(days=7))
        assert collected(domain, evidence)["task_node_id"] == str(earlier.id)

    def test_a_future_period_is_not_answered_for_early(self, domain, evidence):
        task = a_task(domain, evidence)
        an_occurrence(task, domain, TODAY + timedelta(days=7))
        output = collected(domain, evidence)
        # Still filed, it just answers for nothing.
        assert output["task_node_id"] is None
        assert output["attached"] is True

    def test_filing_never_settles_the_occurrence(self, domain, evidence):
        """Automation attaches the work; a person decides it is done."""
        task = a_task(domain, evidence)
        owed = an_occurrence(task, domain, TODAY)
        collected(domain, evidence)
        owed.refresh_from_db()
        assert owed.status == "pending"

    def test_two_tasks_expecting_it_is_refused_not_guessed(self, domain, evidence):
        """Due dates cannot say which task a file answers for."""
        first = a_task(domain, evidence, "Collect for audit")
        second = a_task(domain, evidence, "Collect for the board")
        an_occurrence(first, domain, TODAY)
        an_occurrence(second, domain, TODAY - timedelta(days=1))
        instance = start_instance(attach_flow(domain, evidence))
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "name the occurrence explicitly" in (log.message or "")
            for log in instance.logs.filter(event_type="error")
        )

    def test_another_domains_occurrence_is_not_borrowed(self, domain, evidence):
        elsewhere = Folder.objects.create(
            name=f"Elsewhere {uuid.uuid4().hex[:6]}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        task = TaskTemplate.objects.create(
            name="Collect", folder=elsewhere, task_date=TODAY
        )
        task.evidences.add(evidence)
        an_occurrence(task, elsewhere, TODAY)
        assert collected(domain, evidence)["task_node_id"] is None

    def test_overwriting_keeps_the_occurrence_already_answered_for(
        self, domain, evidence
    ):
        """Clearing it would un-link whoever had answered, and the output has
        to report the row rather than what this run resolved."""
        from core.models import EvidenceRevision

        task = a_task(domain, evidence)
        answered = an_occurrence(task, domain, TODAY, status="completed")
        existing = EvidenceRevision.objects.create(
            evidence=evidence, folder=domain, task_node=answered
        )
        version = attach_flow(domain, evidence)
        attach = version.nodes.get(ref="attach")
        attach.action_config.pop("new_revision", None)
        attach.save()

        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        existing.refresh_from_db()
        assert existing.task_node_id == answered.id
        assert instance.node_outputs["attach"]["task_node_id"] == str(answered.id)

    def test_off_by_default(self, domain, evidence):
        task = a_task(domain, evidence)
        an_occurrence(task, domain, TODAY)
        version = attach_flow(domain, evidence)
        attach = version.nodes.get(ref="attach")
        attach.action_config.pop("find_occurrence")
        attach.save()
        instance = start_instance(version)
        assert instance.node_outputs["attach"]["task_node_id"] is None
