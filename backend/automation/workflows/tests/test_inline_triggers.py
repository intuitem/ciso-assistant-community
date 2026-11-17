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


@pytest.mark.django_db
def test_a_held_run_survives_the_view_saving_its_stale_instance(
    domain, django_capture_on_commit_callbacks
):
    from automation.workflows.events import hold_inline_runs

    install("evidence-default-status", domain)
    with hold_inline_runs():
        with django_capture_on_commit_callbacks(execute=True):
            evidence = Evidence.objects.create(name="Report", folder=domain)
        assert Evidence.objects.get(id=evidence.id).status == "draft"
        # A view saving the instance it holds, as RiskAssessmentViewSet's
        # perform_create does after serializer.save().
        evidence.description = "Annual report"
        evidence.save()
    evidence.refresh_from_db()
    assert evidence.status == "in_review"
    assert evidence.description == "Annual report"


def _run_request(view, user):
    from django.test import RequestFactory

    from core.custom_middleware import AuditlogMiddleware
    from automation.workflows.middleware import InlineWorkflowRunsMiddleware

    request = RequestFactory().post("/api/evidences/")
    request.user = user
    return InlineWorkflowRunsMiddleware(AuditlogMiddleware(view))(request)


@pytest.mark.django_db
def test_runs_start_after_the_view_and_are_not_logged_as_the_user(
    domain, django_capture_on_commit_callbacks
):
    from auditlog.models import LogEntry
    from django.http import HttpResponse

    from iam.models import User

    install("evidence-default-status", domain)
    requester = User.objects.create_user(email="requester@tests.local")
    created = {}

    def view(request):
        with django_capture_on_commit_callbacks(execute=True):
            created["evidence"] = Evidence.objects.create(name="Report", folder=domain)
        assert Evidence.objects.get(id=created["evidence"].id).status == "draft"
        return HttpResponse()

    _run_request(view, requester)

    evidence = Evidence.objects.get(id=created["evidence"].id)
    assert evidence.status == "in_review"
    entries = LogEntry.objects.get_for_object(evidence).order_by("pk")
    assert entries.first().actor == requester
    run_entry = entries.last()
    assert run_entry.changes_dict["status"][1] == "in_review"
    assert run_entry.actor is None


def test_the_hold_wraps_the_audit_context():
    from django.conf import settings

    order = list(settings.MIDDLEWARE)
    assert order.index(
        "automation.workflows.middleware.InlineWorkflowRunsMiddleware"
    ) < order.index("core.custom_middleware.AuditlogMiddleware")


@pytest.mark.django_db
def test_quick_form_events_hold_their_inline_dispatch_like_saves(
    monkeypatch, django_capture_on_commit_callbacks
):
    import uuid
    from types import SimpleNamespace

    from core.views import emit_quick_form_event
    from automation.workflows import events

    calls = []
    monkeypatch.setattr(
        events,
        "dispatch_internal_event",
        lambda event_key, payload, folder_id, inline: calls.append(inline),
    )
    response = SimpleNamespace(
        id=uuid.uuid4(),
        ref_id="R-1",
        name="Request",
        quick_form_id=uuid.uuid4(),
        quick_form=SimpleNamespace(ref_id="form", urn="urn:test:form"),
        publication_id=None,
        status="submitted",
        resolution=None,
        outcome_refs=[],
        computed_values={},
        score=None,
        submitted_by_id=None,
        decided_by_id=None,
        folder_id=None,
    )
    with events.hold_inline_runs():
        with django_capture_on_commit_callbacks(execute=True):
            emit_quick_form_event(response, "submitted")
        # Queued triggers at commit; the inline ones wait for the view (submit
        # closes the response after emitting) and run outside the user's audit
        # context, as InlineWorkflowRunsMiddleware does for a request.
        assert calls == [False]
    assert calls == [False, True]
