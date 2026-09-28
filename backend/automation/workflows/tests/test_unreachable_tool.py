"""Opting into status 0 so an unreachable tool is a branch, not a dead run.

`allow_error_status` covers a server that answered badly; it cannot cover one
that never answered, because requests raises before there is a status. Status 0
collides with no real answer, so one condition routes both.
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
    """The SSRF guard would refuse first; this is about what happens after."""
    monkeypatch.setattr(
        "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
    )

    def refuse(*args, **kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr("requests.request", refuse)


@pytest.mark.django_db
class TestUnreachableTool:
    def test_by_default_an_unreachable_tool_fails_the_run(self, unreachable):
        """A collection that could not run must not look like an empty one."""
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
        """A URL can hold a secret in its query string."""
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

    def test_both_branches_report_the_same_keys(self, monkeypatch):
        """A key on one branch only resolves to nothing on the other."""
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
        )

        class Answer:
            status_code = 200
            text = "{}"

            def json(self):
                return {"ok": True}

        monkeypatch.setattr("requests.request", lambda *a, **k: Answer())
        answered = start_instance(
            fetch_flow(make_domain("Answered"), allow_connection_error=True)
        )

        def refuse(*args, **kwargs):
            raise requests.ConnectionError("connection refused")

        monkeypatch.setattr("requests.request", refuse)
        silent = start_instance(
            fetch_flow(make_domain("Silent"), allow_connection_error=True)
        )

        assert set(answered.node_outputs["pull"]) == set(silent.node_outputs["pull"])
        assert answered.node_outputs["pull"]["unreachable"] is False
        assert answered.node_outputs["pull"]["host"] == "tool.invalid"

    def test_a_string_false_does_not_opt_in(self, monkeypatch):
        """Read raw, the same key meant the opposite of attach_evidence's."""
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
        )

        class Answer:
            status_code = 503
            text = "down"

            def json(self):
                raise ValueError

        monkeypatch.setattr("requests.request", lambda *a, **k: Answer())
        instance = start_instance(
            fetch_flow(make_domain("Stringly"), allow_error_status="false")
        )
        assert instance.status == WorkflowInstance.Status.FAILED

    def test_a_condition_can_route_on_it(self, unreachable):
        """One condition handles both a bad answer and no answer."""
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


def attach_flow(folder, evidence, **extra):
    """trigger -> attach_evidence(source: url) -> end."""
    workflow = Workflow.objects.create(name=f"Attach {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", "start", trigger_config={"type": "manual"})
    attach = node(
        "action",
        "attach",
        label="Attach",
        action_config={
            "type": "attach_evidence",
            "evidence": str(evidence.id),
            "source": "url",
            "url": "https://tool.invalid/export.csv",
            "filename": "export.csv",
            "new_revision": True,
            **extra,
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


@pytest.fixture
def evidence():
    from core.models import Evidence

    folder = make_domain("Attach")
    return Evidence.objects.create(name="Weekly export", folder=folder), folder


@pytest.mark.django_db
class TestUnreachableAttachSource:
    """attach_evidence downloads the file itself, so a collection graph has no
    http_request to branch on. Same opt-ins; `attached` is the discriminator."""

    def test_by_default_an_unreachable_source_fails_the_run(
        self, unreachable, evidence
    ):
        obj, folder = evidence
        instance = start_instance(attach_flow(folder, obj))
        assert instance.status == WorkflowInstance.Status.FAILED
        assert obj.revisions.count() == 0

    def test_opting_in_reports_the_miss_and_files_nothing(self, unreachable, evidence):
        obj, folder = evidence
        instance = start_instance(attach_flow(folder, obj, allow_connection_error=True))
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        output = instance.node_outputs["attach"]
        assert output["attached"] is False
        assert output["unreachable"] is True
        assert output["status"] == 0
        assert output["reason"] == "ConnectionError"
        assert output["host"] == "tool.invalid"
        assert obj.revisions.count() == 0

    def test_the_miss_never_carries_the_url(self, unreachable, evidence):
        obj, folder = evidence
        instance = start_instance(
            attach_flow(
                folder,
                obj,
                allow_connection_error=True,
                url="https://tool.invalid/export.csv?api_key=supersecret",
            )
        )
        assert "supersecret" not in str(instance.node_outputs["attach"])

    def test_a_bad_answer_is_a_separate_opt_in(self, monkeypatch, evidence):
        """Opting into one must not enable the other."""
        obj, folder = evidence
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
        )

        class Answer:
            status_code = 503

            def iter_content(self, _):
                return iter([])

        monkeypatch.setattr("requests.get", lambda *a, **k: Answer())

        failed = start_instance(attach_flow(folder, obj, allow_connection_error=True))
        assert failed.status == WorkflowInstance.Status.FAILED

        allowed = start_instance(attach_flow(folder, obj, allow_error_status=True))
        assert allowed.status == WorkflowInstance.Status.COMPLETED, allowed.variables
        output = allowed.node_outputs["attach"]
        assert output["attached"] is False
        assert output["status"] == 503
        assert output["unreachable"] is False
        assert output["reason"] == "http_error"

    def test_both_branches_report_the_same_keys(self, monkeypatch, evidence):
        """A key on one branch only breaks a mapping on the other."""
        obj, folder = evidence
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
        )

        class Answer:
            status_code = 200

            def iter_content(self, _):
                return iter([b"host,agent\nlaptop-01,ok\n"])

        monkeypatch.setattr("requests.get", lambda *a, **k: Answer())
        filed = start_instance(attach_flow(folder, obj, allow_connection_error=True))

        def refuse(*args, **kwargs):
            raise requests.ConnectionError("connection refused")

        monkeypatch.setattr("requests.get", refuse)
        missed = start_instance(attach_flow(folder, obj, allow_connection_error=True))

        assert set(filed.node_outputs["attach"]) == set(missed.node_outputs["attach"])

    def test_a_filed_revision_reports_attached(self, monkeypatch, evidence):
        """Absent on success, a branch on it reads None and always fails."""
        obj, folder = evidence
        monkeypatch.setattr(
            "core.net_safety.assert_public_url_unless_dev", lambda *a, **k: None
        )

        class Answer:
            status_code = 200

            def iter_content(self, _):
                return iter([b"host,agent\nlaptop-01,ok\n"])

        monkeypatch.setattr("requests.get", lambda *a, **k: Answer())

        instance = start_instance(attach_flow(folder, obj, allow_connection_error=True))
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        output = instance.node_outputs["attach"]
        assert output["attached"] is True
        assert output["version"] == 1
        assert output["status"] == 200
        assert obj.revisions.count() == 1
