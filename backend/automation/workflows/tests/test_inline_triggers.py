from pathlib import Path

import pytest
import yaml

from core.models import Evidence
from automation.workflows.import_export import import_workflow
from automation.workflows.models import WorkflowInstance
from automation.workflows.tests.helpers import publisher_user
from automation.workflows.tests.test_update_actions import make_domain

LIBRARIES = Path(__file__).resolve().parents[3] / "library" / "libraries"


def install(stem, domain, inline=True):
    path = LIBRARIES / f"workflow-operations-{stem}.yaml"
    entry = yaml.safe_load(path.read_text())["objects"]["workflows"][0]
    config = entry["graph"]["nodes"][0]["trigger_config"]
    if inline is None:
        del config["inline"]
    else:
        config["inline"] = inline
    workflow, _warnings = import_workflow(entry, domain, user=publisher_user())
    workflow.draft_version.publish(publisher_user())
    workflow.triggers.update(enabled=True)


@pytest.fixture
def domain(monkeypatch):
    monkeypatch.setattr("global_settings.utils.ff_is_enabled", lambda flag: True)
    return make_domain("Defaults")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "created_with,expected",
    [(None, "in_review"), ("approved", "approved")],
)
def test_evidence_template_replaces_only_the_builtin_default(
    domain, created_with, expected, django_capture_on_commit_callbacks
):
    install("evidence-default-status", domain)
    extra = {"status": created_with} if created_with else {}
    with django_capture_on_commit_callbacks(execute=True):
        evidence = Evidence.objects.create(name="Report", folder=domain, **extra)
    evidence.refresh_from_db()
    assert evidence.status == expected


@pytest.mark.django_db
def test_without_inline_the_run_is_queued(domain, django_capture_on_commit_callbacks):
    install("evidence-default-status", domain, inline=False)
    with django_capture_on_commit_callbacks(execute=True):
        evidence = Evidence.objects.create(name="Report", folder=domain)
    evidence.refresh_from_db()
    assert evidence.status == "draft"


@pytest.mark.django_db
def test_failed_inline_run_does_not_break_the_save(
    domain, monkeypatch, django_capture_on_commit_callbacks
):
    install("evidence-default-status", domain)

    def boom(instance):
        raise RuntimeError("engine down")

    monkeypatch.setattr("automation.workflows.engine.run_instance", boom)
    with django_capture_on_commit_callbacks(execute=True):
        evidence = Evidence.objects.create(name="Report", folder=domain)
    evidence.refresh_from_db()
    assert evidence.status == "draft"
    assert WorkflowInstance.objects.get().status == WorkflowInstance.Status.FAILED


def inline_errors(domain, mutate):
    from automation.workflows.validation import validate_graph

    path = LIBRARIES / "workflow-operations-evidence-default-status.yaml"
    entry = yaml.safe_load(path.read_text())["objects"]["workflows"][0]
    mutate(entry["graph"]["nodes"])
    workflow, _warnings = import_workflow(entry, domain, user=publisher_user())
    return {e["code"] for e in validate_graph(workflow.draft_version)}


@pytest.mark.django_db
def test_shipped_template_is_valid_inline(domain):
    assert not {"trigger_inline_slow_step", "trigger_inline_invalid"} & inline_errors(
        domain, lambda nodes: None
    )


@pytest.mark.django_db
def test_inline_refuses_slow_steps(domain):
    def add_http(nodes):
        nodes[2]["action_config"] = {
            "type": "http_request",
            "method": "GET",
            "url": "https://example.com",
        }

    assert "trigger_inline_slow_step" in inline_errors(domain, add_http)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "config",
    [
        {"type": "manual", "inline": True},
        {"type": "internal_event", "event_key": "evidence.created", "inline": "yes"},
    ],
)
def test_inline_needs_an_event_trigger_and_a_boolean(domain, config):
    def set_trigger(nodes):
        nodes[0]["trigger_config"] = config

    assert "trigger_inline_invalid" in inline_errors(domain, set_trigger)


@pytest.mark.django_db
@pytest.mark.parametrize("queued_inline", [False, None])
def test_only_inline_triggers_run_in_the_request(
    domain, monkeypatch, django_capture_on_commit_callbacks, queued_inline
):
    from automation.workflows import tasks

    real = tasks.dispatch_internal_event_task
    queued = []

    class Recorder:
        def __call__(self, *args):
            queued.append(args)
            return real.call_local(*args)

        def call_local(self, *args):
            return real.call_local(*args)

    monkeypatch.setattr(tasks, "dispatch_internal_event_task", Recorder())
    install("evidence-default-status", domain)
    install("evidence-default-status", domain, inline=queued_inline)
    with django_capture_on_commit_callbacks(execute=True):
        evidence = Evidence.objects.create(name="Report", folder=domain)
    evidence.refresh_from_db()
    assert evidence.status == "in_review"
    assert [args[2] for args in queued] == [False]
    assert WorkflowInstance.objects.count() == 2
