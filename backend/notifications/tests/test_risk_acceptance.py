"""
Risk acceptance wiring: submit asks the approver, a decision (accepted / rejected /
revoked) tells the owners of the covered risk scenarios.

Tasks are queued with `transaction.on_commit`, and HUEY runs with
`immediate: False`, so they are swapped for in-process `.call_local()` runs.
"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from test_fixtures import RISK_MATRIX_JSON_DEFINITION

from core.models import RiskAcceptance, RiskAssessment, RiskMatrix, RiskScenario
from core.views import RiskAcceptanceViewSet
from iam.models import Folder, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="RA test domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def approver(db):
    return User.objects.create(
        email="approver@test.local", first_name="Ada", last_name="Approver"
    )


@pytest.fixture
def owner(db):
    return User.objects.create(email="owner@test.local")


@pytest.fixture
def acceptance(folder, approver, owner):
    matrix = RiskMatrix.objects.create(
        name="m",
        folder=Folder.get_root_folder(),
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    assessment = RiskAssessment.objects.create(
        name="ra", folder=folder, risk_matrix=matrix
    )
    scenario = RiskScenario.objects.create(
        name="Ransomware", risk_assessment=assessment
    )
    scenario.owner.add(owner.actor)
    acceptance = RiskAcceptance.objects.create(
        name="Accept ransomware", folder=folder, approver=approver
    )
    acceptance.risk_scenarios.add(scenario)
    return acceptance


@contextmanager
def _producer(django_capture_on_commit_callbacks):
    from core import tasks

    submitted = tasks.send_risk_acceptance_submitted_notification
    decided = tasks.send_risk_acceptance_decided_notification
    with (
        patch(
            "core.tasks.send_risk_acceptance_submitted_notification",
            side_effect=lambda *a: submitted.call_local(*a),
        ),
        patch(
            "core.tasks.send_risk_acceptance_decided_notification",
            side_effect=lambda *a: decided.call_local(*a),
        ),
        patch("core.tasks.check_email_configuration", return_value=True),
        patch("core.tasks.notify") as notify,
        patch("core.tasks.send_notification_email") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        yield notify, send_email


def _transition(acceptance, state, user):
    acceptance.set_state(state)
    RiskAcceptanceViewSet._notify_state(SimpleNamespace(user=user), acceptance, state)


def test_submit_asks_the_approver(
    acceptance, approver, owner, django_capture_on_commit_callbacks
):
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        _transition(acceptance, "submitted", owner)

    notification_type, recipients, target, context = notify.call_args.args
    assert notification_type == "risk_acceptance_submitted"
    assert recipients == [approver.email]
    assert target == acceptance
    assert context["acceptance_name"] == "Accept ransomware"

    subject, body, recipient, _html = send_email.call_args.args
    assert recipient == approver.email
    assert "Accept ransomware" in subject
    assert "Ransomware" in body


def test_submit_cancelled_before_the_task_runs_sends_nothing(
    acceptance, owner, django_capture_on_commit_callbacks
):
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        acceptance.set_state("created")
        RiskAcceptanceViewSet._notify_state(
            SimpleNamespace(user=owner), acceptance, "submitted"
        )

    notify.assert_not_called()
    send_email.assert_not_called()


@pytest.mark.parametrize("state", ["accepted", "rejected", "revoked"])
def test_decision_tells_the_scenario_owners(
    acceptance, approver, owner, state, django_capture_on_commit_callbacks
):
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        _transition(acceptance, state, approver)

    notification_type, recipients, target, context = notify.call_args.args
    assert notification_type == "risk_acceptance_decided"
    assert recipients == [owner.email]
    assert target == acceptance
    assert context == {"acceptance_name": "Accept ransomware", "decision_key": state}

    subject, body, recipient, _html = send_email.call_args.args
    assert recipient == owner.email
    assert "Ada Approver" in body


def test_decision_email_is_in_the_owner_language(
    acceptance, approver, owner, django_capture_on_commit_callbacks
):
    with (
        patch("core.email_utils.get_email_preferences", return_value=("fr", "auto")),
        _producer(django_capture_on_commit_callbacks) as (_notify, send_email),
    ):
        _transition(acceptance, "rejected", approver)

    subject = send_email.call_args.args[0]
    assert subject.endswith(": Rejeté"), subject
