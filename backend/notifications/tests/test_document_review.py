"""
Document review: a container's reviewers are asked when a revision is submitted for
review, and once reviewers are set only they may approve or request changes. The
revision's author hears about the decision (validated, change requested, published).

Driven through the API so the view-level restriction is exercised. Tasks are queued
with `transaction.on_commit` and HUEY runs with `immediate: False`, so they are
swapped for in-process `.call_local()` runs.
"""

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from doc_management.models import DocumentContainer, DocumentRevision, ManagedDocument
from iam.models import Folder, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Docs test domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def author(db):
    return User.objects.create_superuser("author@test.local")


@pytest.fixture
def reviewer(db):
    return User.objects.create_superuser("reviewer@test.local")


@pytest.fixture
def container(folder):
    return DocumentContainer.objects.create(name="Access policy", folder=folder)


@pytest.fixture
def revision(container, folder, author):
    document = ManagedDocument.objects.create(container=container, folder=folder)
    return DocumentRevision.objects.create(
        document=document, folder=folder, author=author, content="v1"
    )


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _post(user, revision, action, **data):
    return _client(user).post(
        f"/api/document-revisions/{revision.id}/{action}/", data, format="json"
    )


@contextmanager
def _producer(django_capture_on_commit_callbacks):
    from core import tasks

    requested = tasks.send_document_review_requested_notification
    reviewed = tasks.send_document_revision_reviewed_notification
    with (
        patch(
            "core.tasks.send_document_review_requested_notification",
            side_effect=lambda *a: requested.call_local(*a),
        ),
        patch(
            "core.tasks.send_document_revision_reviewed_notification",
            side_effect=lambda *a: reviewed.call_local(*a),
        ),
        patch("core.tasks.send_object_assignment_notification"),
        patch("core.tasks.check_email_configuration", return_value=True),
        patch("core.tasks.notify") as notify,
        patch("core.tasks.send_notification_email") as send_email,
        django_capture_on_commit_callbacks(execute=True),
    ):
        yield notify, send_email


def _in_review(revision):
    DocumentRevision.objects.filter(pk=revision.pk).update(
        status=DocumentRevision.Status.IN_REVIEW
    )


def test_submit_asks_the_reviewers_but_not_the_submitter(
    container, revision, author, reviewer, django_capture_on_commit_callbacks
):
    container.reviewers.add(reviewer.actor, author.actor)
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        assert _post(author, revision, "submit-for-review").status_code == 200

    notification_type, recipients, target, context = notify.call_args.args
    assert notification_type == "document_review_requested"
    assert recipients == [reviewer.email]
    assert target == container
    assert context == {"document_name": "Access policy"}
    assert send_email.call_args.args[2] == reviewer.email


def test_submit_without_reviewers_sends_nothing(
    revision, author, django_capture_on_commit_callbacks
):
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        assert _post(author, revision, "submit-for-review").status_code == 200

    notify.assert_not_called()
    send_email.assert_not_called()


@pytest.mark.parametrize("action", ["approve", "request-changes"])
def test_only_reviewers_may_decide_once_set(
    container, revision, author, reviewer, action
):
    container.reviewers.add(reviewer.actor)
    _in_review(revision)

    response = _post(author, revision, action)
    assert response.status_code == 403
    assert response.json() == {"error": "documentReviewReservedToReviewers"}
    revision.refresh_from_db()
    assert revision.status == DocumentRevision.Status.IN_REVIEW


def test_a_team_member_counts_as_reviewer(container, revision, reviewer, folder):
    from core.models import Team

    team = Team.objects.create(name="Doc reviewers", folder=folder)
    team.members.add(reviewer)
    container.reviewers.add(team.actor)
    _in_review(revision)

    assert _post(reviewer, revision, "approve").status_code == 200


def test_without_reviewers_review_stays_open(revision, author):
    _in_review(revision)
    assert _post(author, revision, "approve").status_code == 200


@pytest.mark.parametrize(
    "action,state",
    [("approve", "validated"), ("request-changes", "change_requested")],
)
def test_decision_tells_the_author(
    container,
    revision,
    author,
    reviewer,
    action,
    state,
    django_capture_on_commit_callbacks,
):
    container.reviewers.add(reviewer.actor)
    _in_review(revision)
    with _producer(django_capture_on_commit_callbacks) as (notify, send_email):
        assert (
            _post(reviewer, revision, action, reviewer_comments="Fix 3.2").status_code
            == 200
        )

    notification_type, recipients, target, context = notify.call_args.args
    assert notification_type == "document_revision_reviewed"
    assert recipients == [author.email]
    assert target == container
    assert context == {"document_name": "Access policy", "decision_key": state}
    assert send_email.call_args.args[2] == author.email


def test_author_acting_on_own_revision_is_not_told(
    revision, author, django_capture_on_commit_callbacks
):
    _in_review(revision)
    with _producer(django_capture_on_commit_callbacks) as (notify, _send_email):
        assert _post(author, revision, "approve").status_code == 200

    notify.assert_not_called()


def test_adding_a_reviewer_uses_the_generic_review_type(
    container, reviewer, django_capture_on_commit_callbacks
):
    with patch("core.tasks.send_object_assignment_notification") as send:
        with django_capture_on_commit_callbacks(execute=True):
            response = _client(reviewer).patch(
                f"/api/document-containers/{container.id}/",
                {"reviewers": [str(reviewer.actor.id)]},
                format="json",
            )
    assert response.status_code == 200, response.json()
    assert send.call_args.args[:2] == (
        "object_review_assignment",
        "doc_management.documentcontainer",
    )
