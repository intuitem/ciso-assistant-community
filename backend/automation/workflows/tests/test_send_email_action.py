"""send_email action: delivery failures must fail the node.

Delivery is dispatched to a huey task (DeferredSendEmailTask): the engine parks
the token WAITING and the task sends outside the engine transaction, so SMTP
I/O never runs while the instance-tree locks are held. The task hands the
token back — success advances the run, any delivery failure fails the node
and feeds the per-node retry policy instead of logging a clean
ACTION_EXECUTED row while nothing was sent.

Huey is not immediate in tests: the `dispatch` fixture captures the enqueue
and `dispatch.run()` executes the task body synchronously.
"""

import uuid

import pytest
from django.core import mail

from global_settings.models import GlobalSettings
from iam.models import Folder
from automation.workflows import actions as workflow_actions
from automation.workflows import tasks as workflow_tasks
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowNode,
    WorkflowToken,
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


def email_flow(config):
    workflow = Workflow.objects.create(
        name="Email flow", folder=Folder.get_root_folder()
    )
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    action = node("action", action_config={"type": "send_email", **config})
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [start, action, end],
            "edges": [edge(start, action), edge(action, end)],
            "variables": [],
        },
    )
    return version


def configure_smtp(settings):
    settings.EMAIL_HOST = "smtp.tests.local"
    settings.EMAIL_PORT = "25"
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"


def error_messages(instance):
    return [log.message or "" for log in instance.logs.filter(event_type="error")]


@pytest.fixture
def dispatch(monkeypatch):
    """Capture send_email_task enqueues instead of hitting the huey queue;
    run(i) executes the captured task body synchronously."""
    captured = []
    deliver = workflow_tasks.send_email_task.call_local
    # DeferredSendEmailTask binds send_email_task from the actions module,
    # so that binding is the one to patch.
    monkeypatch.setattr(
        workflow_actions, "send_email_task", lambda **kwargs: captured.append(kwargs)
    )

    class Dispatch:
        calls = captured

        @staticmethod
        def run(index=0):
            deliver(**captured[index])

    return Dispatch


@pytest.mark.django_db
class TestSendEmail:
    def test_delivery_runs_outside_the_engine_transaction(
        self, settings, dispatch, django_capture_on_commit_callbacks
    ):
        configure_smtp(settings)
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        # Parked, nothing sent: the send happens in the task, after commit.
        assert instance.status == WorkflowInstance.Status.ACTIVE
        token = instance.tokens.get(current_node__type=WorkflowNode.Type.ACTION)
        assert token.status == WorkflowToken.Status.WAITING
        assert not mail.outbox
        assert dispatch.calls[0]["token_id"] == str(token.id)

    def test_sends_to_each_recipient(
        self, settings, dispatch, django_capture_on_commit_callbacks
    ):
        configure_smtp(settings)
        version = email_flow(
            {
                "recipients": "a@tests.local, b@tests.local",
                "subject": "Reminder",
                "body": "Control is overdue",
            }
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert sorted(message.to[0] for message in mail.outbox) == [
            "a@tests.local",
            "b@tests.local",
        ]
        log = instance.logs.get(event_type="action_executed")
        assert log.data["recipients"] == ["a@tests.local", "b@tests.local"]
        assert log.data["subject"] == "Reminder"

    def test_duplicate_task_delivery_is_ignored(
        self, settings, dispatch, django_capture_on_commit_callbacks
    ):
        configure_smtp(settings)
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        dispatch.run()  # huey may deliver twice; the WAITING pre-check drops it
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert len(mail.outbox) == 1

    def test_notifications_toggle_does_not_gate_workflow_email(
        self, settings, dispatch, django_capture_on_commit_callbacks
    ):
        # notifications_enable_mailing governs the digest notifications only;
        # send_email nodes delivered with it off before the sync rework and
        # must keep doing so.
        configure_smtp(settings)
        general, _ = GlobalSettings.objects.get_or_create(name="general")
        general.value = {**(general.value or {}), "notifications_enable_mailing": False}
        general.save()
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert len(mail.outbox) == 1

    def test_console_backend_needs_no_smtp_settings(
        self, settings, dispatch, django_capture_on_commit_callbacks
    ):
        # MAIL_DEBUG deployments swap in the console backend with no
        # EMAIL_HOST/EMAIL_PORT; the settings precheck must not fail the node
        # in exactly the environments meant for testing workflows.
        settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
        settings.EMAIL_HOST = None
        settings.EMAIL_PORT = None
        settings.DEFAULT_FROM_EMAIL = "noreply@ciso.assistant"
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED

    def test_missing_email_settings_fail_the_node(self, settings):
        settings.EMAIL_HOST = None
        settings.EMAIL_PORT = None
        settings.DEFAULT_FROM_EMAIL = None
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "not configured" in m and "EMAIL_HOST" in m
            for m in error_messages(instance)
        )
        assert not mail.outbox

    def test_display_name_recipient_is_accepted(
        self, settings, dispatch, django_capture_on_commit_callbacks
    ):
        configure_smtp(settings)
        version = email_flow(
            {"recipients": "Jane Doe <jane@tests.local>", "subject": "S"}
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert mail.outbox[0].to == ["Jane Doe <jane@tests.local>"]

    def test_invalid_recipient_fails_before_any_send(self, settings):
        configure_smtp(settings)
        version = email_flow(
            {"recipients": "a@tests.local, not-an-email", "subject": "S"}
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "invalid recipient 'not-an-email'" in m for m in error_messages(instance)
        )
        assert not mail.outbox

    def test_transport_failure_fails_the_node(
        self, settings, dispatch, monkeypatch, django_capture_on_commit_callbacks
    ):
        configure_smtp(settings)

        def broken_send(
            subject, message, recipient, html_message=None, connection=None
        ):
            raise ConnectionRefusedError("connection refused")

        monkeypatch.setattr("automation.workflows.tasks.send_email_now", broken_send)
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "delivery failed for a@tests.local" in m and "(0 of 1 sent)" in m
            for m in error_messages(instance)
        )

    def test_one_dead_recipient_does_not_starve_the_rest(
        self, settings, dispatch, monkeypatch, django_capture_on_commit_callbacks
    ):
        configure_smtp(settings)
        import core.tasks as core_tasks

        real_send = core_tasks.send_email_now

        def flaky(subject, message, recipient, html_message=None, connection=None):
            if recipient == "gone@tests.local":
                raise ConnectionRefusedError("mailbox gone")
            return real_send(subject, message, recipient, html_message, connection)

        monkeypatch.setattr("automation.workflows.tasks.send_email_now", flaky)
        version = email_flow(
            {
                "recipients": "a@tests.local, gone@tests.local, c@tests.local",
                "subject": "S",
            }
        )
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.FAILED
        # The dead address fails the node but the others still got their mail.
        assert sorted(message.to[0] for message in mail.outbox) == [
            "a@tests.local",
            "c@tests.local",
        ]
        assert any(
            "gone@tests.local" in m and "(2 of 3 sent)" in m
            for m in error_messages(instance)
        )

    def test_failed_delivery_feeds_the_retry_policy(
        self, settings, dispatch, monkeypatch, django_capture_on_commit_callbacks
    ):
        configure_smtp(settings)
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        version.nodes.filter(type=WorkflowNode.Type.ACTION).update(
            retry_max_attempts=1, retry_delay_seconds=5
        )
        scheduled = {}
        monkeypatch.setattr(
            "automation.workflows.tasks.retry_token_task.schedule",
            lambda args, delay: scheduled.update(token_id=args[0], delay=delay),
        )
        import core.tasks as core_tasks

        real_send = core_tasks.send_email_now
        state = {"broken": True}

        def flaky(subject, message, recipient, html_message=None, connection=None):
            if state["broken"]:
                raise ConnectionRefusedError("connection refused")
            return real_send(subject, message, recipient, html_message, connection)

        monkeypatch.setattr("automation.workflows.tasks.send_email_now", flaky)

        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        with django_capture_on_commit_callbacks(execute=True):
            dispatch.run()  # first delivery fails -> RETRYING, retry scheduled
        token = instance.tokens.get(status=WorkflowToken.Status.RETRYING)
        assert scheduled == {"token_id": str(token.id), "delay": 5}

        state["broken"] = False
        with django_capture_on_commit_callbacks(execute=True):
            # The consumer re-runs the node, which re-renders and re-dispatches.
            workflow_tasks.retry_token_task.call_local(scheduled["token_id"])
        dispatch.run(1)
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert [message.to for message in mail.outbox] == [["a@tests.local"]]

    def test_config_errors_do_not_burn_the_retry_schedule(self, settings):
        # Permanent problems (invalid recipient here) are non-retryable: the
        # node must fail immediately even with retries configured, not
        # re-execute a doomed send on the retry schedule.
        configure_smtp(settings)
        version = email_flow({"recipients": "not-an-email", "subject": "S"})
        version.nodes.filter(type=WorkflowNode.Type.ACTION).update(retry_max_attempts=3)
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert not instance.tokens.filter(status=WorkflowToken.Status.RETRYING).exists()

    def test_zero_messages_sent_fails_the_node(
        self, settings, dispatch, monkeypatch, django_capture_on_commit_callbacks
    ):
        configure_smtp(settings)
        monkeypatch.setattr(
            "core.tasks.EmailMessage.send", lambda self, fail_silently=False: 0
        )
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        with django_capture_on_commit_callbacks(execute=True):
            instance = start_instance(version)
        dispatch.run()
        instance.refresh_from_db()
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "delivery failed for a@tests.local" in m for m in error_messages(instance)
        )

    def test_no_recipients_fails_the_node(self, settings):
        configure_smtp(settings)
        version = email_flow({"recipients": "", "subject": "S"})
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("no recipients configured" in m for m in error_messages(instance))
