"""The shipped `Assignment actors become respondents` library, run end to end
from the audit log entry an actor change writes."""

from pathlib import Path

import pytest
import yaml
from auditlog.models import LogEntry

from core.models import (
    Actor,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssignment,
    Team,
)
from iam.models import Folder, User, UserGroup
from automation.workflows.engine import run_instance
from automation.workflows.events import payload_from_log_entry
from automation.workflows.import_export import import_workflow
from automation.workflows.models import WorkflowInstance
from automation.workflows.tasks import dispatch_internal_event_task
from automation.workflows.tests.helpers import publisher_user

LIBRARY = (
    Path(__file__).resolve().parents[3]
    / "library"
    / "libraries"
    / "workflow-compliance-assignment-respondents.yaml"
)
TARGETED = "urn:test:risk:framework:targeted"


@pytest.fixture
def run_now(monkeypatch):
    monkeypatch.setattr(
        "automation.workflows.tasks.run_instance_task",
        lambda instance_id: run_instance(WorkflowInstance.objects.get(id=instance_id)),
    )


def make_domain(name):
    domain = Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(domain)
    return domain


def install(domain):
    entry = yaml.safe_load(LIBRARY.read_text())["objects"]["workflows"][0]
    for variable in entry["graph"]["variables"]:
        if variable["key"] == "framework_urns":
            variable["default_value"] = TARGETED
    workflow, _warnings = import_workflow(entry, domain, user=publisher_user())
    workflow.draft_version.publish(publisher_user())
    workflow.triggers.update(enabled=True)
    return workflow


def make_audit(domain, urn=TARGETED):
    framework = Framework.objects.create(name=urn, urn=urn, folder=domain)
    perimeter = Perimeter.objects.create(name="Perimeter", folder=domain)
    return ComplianceAssessment.objects.create(
        name="Audit", framework=framework, perimeter=perimeter, folder=domain
    )


def last_update(assignment):
    return (
        LogEntry.objects.filter(
            object_pk=str(assignment.pk), action=LogEntry.Action.UPDATE
        )
        .order_by("-timestamp", "-pk")
        .first()
    )


def respondents(domain):
    group = UserGroup.objects.get(folder=domain, name="BI-UG-ADE")
    return set(group.user_set.values_list("email", flat=True))


@pytest.mark.django_db
class TestAssignmentRespondents:
    def test_an_actor_change_reads_as_its_operation(self):
        domain = make_domain("Domain")
        user = User.objects.create_user(email="direct@example.com")
        assignment = RequirementAssignment.objects.create(
            compliance_assessment=make_audit(domain), folder=domain
        )
        assignment.actor.add(Actor.objects.get(user=user))
        assert payload_from_log_entry(last_update(assignment))["new_values"] == {
            "actor": "add"
        }

    def test_added_actors_become_respondents(self, run_now):
        domain = make_domain("Domain")
        sibling = make_domain("Sibling")
        workflow = install(domain)
        direct = User.objects.create_user(email="direct@example.com")
        leader = User.objects.create_user(email="leader@example.com")
        outsider = User.objects.create_user(email="outsider@example.com")
        vendor = User.objects.create_user(
            email="vendor@example.com", is_third_party=True
        )
        team = Team.objects.create(name="In scope", folder=domain, leader=leader)
        far_team = Team.objects.create(name="Far", folder=sibling, leader=outsider)
        assignment = RequirementAssignment.objects.create(
            compliance_assessment=make_audit(domain), folder=domain
        )
        assignment.actor.set(
            [
                Actor.objects.get(user=direct),
                Actor.objects.get(user=vendor),
                Actor.objects.get(team=team),
                Actor.objects.get(team=far_team),
            ]
        )

        dispatch_internal_event_task.call_local(last_update(assignment).pk, 0)

        instance = WorkflowInstance.objects.get(workflow=workflow)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        assert respondents(domain) == {"direct@example.com", "leader@example.com"}

    def test_a_status_change_starts_no_run(self, run_now):
        domain = make_domain("Domain")
        install(domain)
        user = User.objects.create_user(email="direct@example.com")
        assignment = RequirementAssignment.objects.create(
            compliance_assessment=make_audit(domain), folder=domain
        )
        assignment.actor.add(Actor.objects.get(user=user))
        UserGroup.objects.get(folder=domain, name="BI-UG-ADE").user_set.clear()

        assignment.status = RequirementAssignment.Status.IN_PROGRESS
        assignment.save()
        dispatch_internal_event_task.call_local(last_update(assignment).pk, 0)

        assert not WorkflowInstance.objects.exists()

    def test_other_frameworks_are_left_alone(self, run_now):
        domain = make_domain("Domain")
        install(domain)
        user = User.objects.create_user(email="direct@example.com")
        assignment = RequirementAssignment.objects.create(
            compliance_assessment=make_audit(domain, "urn:test:risk:framework:other"),
            folder=domain,
        )
        assignment.actor.add(Actor.objects.get(user=user))

        dispatch_internal_event_task.call_local(last_update(assignment).pk, 0)

        assert respondents(domain) == set()

    def test_a_failed_grant_fails_the_run(self, run_now):
        domain = Folder.objects.create(
            name="No groups",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        workflow = install(domain)
        user = User.objects.create_user(email="direct@example.com")
        assignment = RequirementAssignment.objects.create(
            compliance_assessment=make_audit(domain), folder=domain
        )
        assignment.actor.add(Actor.objects.get(user=user))

        dispatch_internal_event_task.call_local(last_update(assignment).pk, 0)

        instance = WorkflowInstance.objects.get(workflow=workflow)
        assert instance.status == WorkflowInstance.Status.FAILED
