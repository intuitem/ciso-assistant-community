"""send_email action: delivery failures must fail the node.

The action sends synchronously (not through the fire-and-forget huey task),
so an SMTP error, an unconfigured mailer or a disabled mailing toggle all
surface as ActionError and feed the node retry policy instead of logging a
clean ACTION_EXECUTED row while nothing was sent.
"""

import uuid

import pytest
from django.core import mail

from global_settings.models import GlobalSettings
from iam.models import Folder
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


def enable_mailing(settings):
    general, _ = GlobalSettings.objects.get_or_create(name="general")
    general.value = {**(general.value or {}), "notifications_enable_mailing": True}
    general.save()
    settings.EMAIL_HOST = "smtp.tests.local"
    settings.EMAIL_PORT = "25"
    settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"


def error_messages(instance):
    return [log.message or "" for log in instance.logs.filter(event_type="error")]


@pytest.mark.django_db
class TestSendEmail:
    def test_sends_to_each_recipient(self, settings):
        enable_mailing(settings)
        version = email_flow(
            {
                "recipients": "a@tests.local, b@tests.local",
                "subject": "Reminder",
                "body": "Control is overdue",
            }
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert sorted(message.to[0] for message in mail.outbox) == [
            "a@tests.local",
            "b@tests.local",
        ]
        log = instance.logs.get(event_type="action_executed")
        assert log.data["recipients"] == ["a@tests.local", "b@tests.local"]
        assert log.data["subject"] == "Reminder"

    def test_mailing_disabled_fails_the_node(self, settings):
        settings.EMAIL_HOST = "smtp.tests.local"
        settings.DEFAULT_FROM_EMAIL = "ciso@tests.local"
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("mailing is disabled" in m for m in error_messages(instance))
        assert not mail.outbox

    def test_missing_email_settings_fail_the_node(self, settings):
        general, _ = GlobalSettings.objects.get_or_create(name="general")
        general.value = {**(general.value or {}), "notifications_enable_mailing": True}
        general.save()
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

    def test_invalid_recipient_fails_before_any_send(self, settings):
        enable_mailing(settings)
        version = email_flow(
            {"recipients": "a@tests.local, not-an-email", "subject": "S"}
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "invalid recipient 'not-an-email'" in m for m in error_messages(instance)
        )
        assert not mail.outbox

    def test_transport_failure_fails_the_node(self, settings, monkeypatch):
        enable_mailing(settings)

        def broken_send(subject, message, recipient, html_message=None):
            raise ConnectionRefusedError("connection refused")

        monkeypatch.setattr("core.tasks.send_email_now", broken_send)
        version = email_flow({"recipients": "a@tests.local", "subject": "S"})
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "sending to 'a@tests.local' failed" in m for m in error_messages(instance)
        )

    def test_no_recipients_fails_the_node(self, settings):
        enable_mailing(settings)
        version = email_flow({"recipients": "", "subject": "S"})
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("no recipients configured" in m for m in error_messages(instance))
