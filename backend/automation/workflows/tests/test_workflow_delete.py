"""Deleting a workflow that branches.

Condition.variable is PROTECT and non-nullable, so every real condition puts a
PROTECT edge between two children of one version — which Django refuses to
collect. The regression pinned here: the delete preview reported those
conditions as blockers, so the UI refused a delete the API would have carried
out, for every branching workflow including two shipped libraries.
"""

import uuid

import pytest
from rest_framework.test import APIClient

from iam.models import Folder
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Condition,
    ConditionGroup,
    Workflow,
    WorkflowVersion,
)
from automation.workflows.tests.helpers import publisher_user


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "source": source["id"],
        "target": target["id"],
        **kwargs,
    }


def branching_workflow():
    """A trigger, a condition on a variable, two arms, an end."""
    workflow = Workflow.objects.create(
        name="Branching", folder=Folder.get_root_folder()
    )
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    variable_id = str(uuid.uuid4())
    start = node("trigger", trigger_config={"type": "manual"})
    route = node(
        "condition",
        branches=[
            {
                "id": str(uuid.uuid4()),
                "name": "hot",
                "order": 0,
                "is_default": False,
                "condition_groups": [
                    {
                        "id": str(uuid.uuid4()),
                        "operator": "and",
                        "conditions": [
                            {
                                "id": str(uuid.uuid4()),
                                "variable": variable_id,
                                "op": "eq",
                                "value": "yes",
                            }
                        ],
                    }
                ],
            },
            {
                "id": str(uuid.uuid4()),
                "name": "cold",
                "order": 1,
                "is_default": True,
                "condition_groups": [],
            },
        ],
    )
    hot = node("action", action_config={"type": "log", "message": "hot"})
    cold = node("action", action_config={"type": "log", "message": "cold"})
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [start, route, hot, cold, end],
            "edges": [
                edge(start, route),
                edge(route, hot, source_branch=route["branches"][0]["id"]),
                edge(route, cold, source_branch=route["branches"][1]["id"]),
                edge(hot, end),
                edge(cold, end),
            ],
            "variables": [{"id": variable_id, "key": "flag", "type": "string"}],
        },
    )
    return workflow


def admin_client():
    client = APIClient()
    client.force_authenticate(publisher_user())
    return client


@pytest.mark.django_db
class TestBranchingWorkflowDelete:
    def test_the_graph_really_has_a_protect_edge(self):
        """Without a variable-bound condition there is nothing to regress."""
        workflow = branching_workflow()
        assert Condition.objects.filter(
            group__branch__node__version__workflow=workflow
        ).exists()
        assert Condition._meta.get_field(
            "variable"
        ).remote_field.on_delete.__name__ == ("PROTECT")

    def test_preview_does_not_report_conditions_as_blockers(self):
        workflow = branching_workflow()
        resp = admin_client().get(
            f"/api/workflows/workflows/{workflow.id}/cascade-info/"
        )
        assert resp.status_code == 200
        blocked = resp.json()["blocked"]
        assert blocked["count"] == 0, blocked["grouped_objects"]

    def test_delete_succeeds(self):
        workflow = branching_workflow()
        workflow_id = workflow.id
        resp = admin_client().delete(f"/api/workflows/workflows/{workflow_id}/")
        assert resp.status_code == 204, resp.content
        assert not Workflow.objects.filter(id=workflow_id).exists()
        # The pre-cleared trees go too rather than stranding rows.
        assert not ConditionGroup.objects.filter(
            branch__node__version__workflow_id=workflow_id
        ).exists()

    def test_preview_and_delete_agree(self):
        """The bug was the two disagreeing."""
        workflow = branching_workflow()
        client = admin_client()
        blocked = client.get(
            f"/api/workflows/workflows/{workflow.id}/cascade-info/"
        ).json()["blocked"]["count"]
        deleted = (
            client.delete(f"/api/workflows/workflows/{workflow.id}/").status_code == 204
        )
        assert (blocked == 0) is deleted

    def test_a_genuine_blocker_is_still_reported(self):
        """A PROTECT reference from outside the cascade still blocks."""
        workflow = branching_workflow()
        user = publisher_user()
        other = Workflow.objects.create(name="Parent", folder=Folder.get_root_folder())
        other_version = WorkflowVersion.objects.create(workflow=other, run_as=user)
        # subprocess_workflow is the app's other PROTECT, pointing in from
        # outside this workflow's cascade.
        start = node("trigger", trigger_config={"type": "manual"})
        end = node("end")
        save_graph(
            other_version,
            {"nodes": [start, end], "edges": [edge(start, end)], "variables": []},
        )
        other_version.nodes.filter(type="end").update(subprocess_workflow=workflow)

        resp = admin_client().get(
            f"/api/workflows/workflows/{workflow.id}/cascade-info/"
        )
        assert resp.status_code == 200
        blocked = resp.json()["blocked"]
        assert blocked["count"] == 1, blocked["grouped_objects"]
        assert blocked["grouped_objects"][0]["model"] == "WorkflowNode"
