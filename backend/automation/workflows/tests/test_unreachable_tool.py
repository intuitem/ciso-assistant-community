"""A tool being unreachable is an outcome a graph can route on, if it opts in.

`allow_error_status` covers a server that answered badly. It cannot cover one
that never answered: requests raises before there is a status, so the node fails
and the run stops — which is right by default (a silent partial run is worse),
but leaves no way to notice the collector has been down for a week.

`allow_connection_error` turns that into status 0, which no real answer can
collide with, so the same condition that routes a 503 routes a refused
connection.
"""

import uuid

import pytest
import requests

from iam.models import Folder
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowInstance, WorkflowVersion
from automation.workflows.tests.helpers import publisher_user


def node(type_, ref, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "ref": ref,
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target, branch=None):
    payload = {"id": str(uuid.uuid4()), "source": source["id"], "target": target["id"]}
    if branch:
        payload["source_branch"] = branch["id"]
    return payload


def make_domain(name):
    return Folder.objects.create(
        name=f"{name} {uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def fetch_flow(folder, **extra):
    """trigger -> http_request -> end, with whatever config the test wants."""
    workflow = Workflow.objects.create(name=f"Fetch {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", "start", trigger_config={"type": "manual"})
    pull = node(
        "action",
        "pull",
        label="Pull",
        action_config={
            "type": "http_request",
            "method": "GET",
            # Nothing listens here; the guard is bypassed so the refusal is what
            # the action sees.
            "url": "https://tool.invalid/coverage.json",
            **extra,
        },
    )
    done = node("end", "done")
    save_graph(
        version,
        {"nodes": [start, pull, done], "edges": [edge(start, pull), edge(pull, done)]},
    )
    return version


@pytest.fixture
def unreachable(monkeypatch):
    """The SSRF guard would refuse first; this test is about what happens after."""
    monkeypatch.setattr(
        "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
    )

    def refuse(*args, **kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr("requests.request", refuse)


@pytest.mark.django_db
class TestUnreachableTool:
    def test_by_default_an_unreachable_tool_fails_the_run(self, unreachable):
        """The safe default: a collection that could not run must not look like
        one that ran and found nothing."""
        instance = start_instance(fetch_flow(make_domain("Default")))
        assert instance.status == WorkflowInstance.Status.FAILED

    def test_opting_in_reports_status_0_instead(self, unreachable):
        instance = start_instance(
            fetch_flow(make_domain("Opted in"), allow_connection_error=True)
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        output = instance.node_outputs["pull"]
        assert output["status"] == 0
        assert output["unreachable"] is True
        assert output["body"] is None
        assert output["reason"] == "ConnectionError"

    def test_the_reason_never_carries_the_url(self, unreachable):
        """A URL can hold a secret in its query string, so the run log gets the
        host and the exception class, never the address."""
        instance = start_instance(
            fetch_flow(
                make_domain("No leak"),
                allow_connection_error=True,
                url="https://tool.invalid/coverage.json?api_key=supersecret",
            )
        )
        output = instance.node_outputs["pull"]
        assert "supersecret" not in str(output)
        assert output["host"] == "tool.invalid"

    def test_a_condition_can_route_on_it(self, unreachable):
        """The point of the flag: one condition handles both a bad answer and no
        answer, because neither is 200."""
        folder = make_domain("Routed")
        workflow = Workflow.objects.create(name="Routed", folder=folder)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        status_var = {"id": str(uuid.uuid4()), "key": "http_status", "type": "number"}
        start = node("trigger", "start", trigger_config={"type": "manual"})
        pull = node(
            "action",
            "pull",
            label="Pull",
            action_config={
                "type": "http_request",
                "method": "GET",
                "url": "https://tool.invalid/coverage.json",
                "allow_connection_error": True,
            },
            output_mapping={"http_status": "status"},
        )
        ok_branch = {
            "id": str(uuid.uuid4()),
            "name": "Answered",
            "order": 0,
            "is_default": False,
            "condition_groups": [
                {
                    "operator": "and",
                    "order": 0,
                    "conditions": [
                        {
                            "variable": status_var["id"],
                            "op": "eq",
                            "value": 200,
                            "order": 0,
                        }
                    ],
                }
            ],
        }
        bad_branch = {
            "id": str(uuid.uuid4()),
            "name": "Down",
            "order": 1,
            "is_default": True,
        }
        check = node(
            "condition", "check", label="Answered?", branches=[ok_branch, bad_branch]
        )
        collected = node(
            "action",
            "collected",
            label="Collected",
            action_config={"type": "log", "message": "collected"},
        )
        warned = node(
            "action",
            "warned",
            label="Warned",
            action_config={
                "type": "log",
                "message": "tool unreachable: {{http_status}}",
            },
        )
        done = node("end", "done")
        save_graph(
            version,
            {
                "variables": [status_var],
                "nodes": [start, pull, check, collected, warned, done],
                "edges": [
                    edge(start, pull),
                    edge(pull, check),
                    edge(check, collected, ok_branch),
                    edge(collected, done),
                    edge(check, warned, bad_branch),
                    edge(warned, done),
                ],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        assert "warned" in instance.node_outputs
        assert "collected" not in instance.node_outputs
        assert instance.node_outputs["warned"]["message"] == "tool unreachable: 0"
