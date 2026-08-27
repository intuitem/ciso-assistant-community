"""API tests for RequirementAssignmentViewSet.set_status.

Covers the transition matrix introduced/extended by SUP-1488 (reopening a
submitted/changes_requested/in_progress/closed assignment back to "draft"),
plus the EDITABLE_STATUSES guard on update/partial_update/destroy.

reviewer_only / actor_only are exercised by monkeypatching the same seams
used elsewhere in this test suite (get_respondent_scoped_folder_ids,
Actor.get_all_for_user) rather than wiring full RBAC role assignments, to
keep the tests focused on RequirementAssignmentViewSet's own logic.
"""

import pytest
from rest_framework.test import APIClient
from knox.models import AuthToken

import core.views as core_views
from core.apps import startup
from core.models import (
    Actor,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssignment,
    RequirementAssignmentEvent,
)
from iam.models import Folder, User, UserGroup


@pytest.fixture
def app_config():
    startup(sender=None, **{})


def _admin_client(email):
    """A user in BI-UG-ADM: full permissions everywhere, not respondent-scoped."""
    user = User.objects.create_user(email=email, is_published=True)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = admin_group.folder
    user.save()
    admin_group.user_set.add(user)
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {_auth_token[1]}")
    return user, client


@pytest.fixture
def assignment_fixture(app_config):
    root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    folder = Folder.objects.create(
        parent_folder=root_folder,
        name="assignment test folder",
    )
    perimeter = Perimeter.objects.create(
        name="assignment test perimeter", folder=folder
    )
    framework = Framework.objects.create(
        name="assignment test framework", folder=folder
    )
    compliance_assessment = ComplianceAssessment.objects.create(
        name="assignment test compliance assessment",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
    )

    reviewer, reviewer_client = _admin_client("assignment_reviewer@tests.com")
    other_reviewer, other_reviewer_client = _admin_client(
        "assignment_other_reviewer@tests.com"
    )
    actor_user, actor_client = _admin_client("assignment_actor@tests.com")

    assignment = RequirementAssignment.objects.create(
        compliance_assessment=compliance_assessment,
        folder=folder,
    )
    assignment.actor.set([actor_user.actor])

    return {
        "folder": folder,
        "compliance_assessment": compliance_assessment,
        "assignment": assignment,
        "reviewer": reviewer,
        "reviewer_client": reviewer_client,
        "other_reviewer_client": other_reviewer_client,
        "actor_user": actor_user,
        "actor_client": actor_client,
    }


def _set_status(client, assignment_id, target_status, observation=None):
    payload = {"status": target_status}
    if observation is not None:
        payload["reviewer_observation"] = observation
    return client.post(
        f"/api/requirement-assignments/{assignment_id}/set_status/",
        data=payload,
    )


@pytest.mark.django_db
class TestSetStatusTransitions:
    @pytest.mark.parametrize(
        "start_status,target_status",
        [
            ("submitted", "draft"),
            ("changes_requested", "draft"),
            ("closed", "draft"),
            ("in_progress", "draft"),
        ],
    )
    def test_reviewer_can_reopen_to_draft(
        self, assignment_fixture, start_status, target_status
    ):
        """New transitions added by SUP-1488: any non-draft status can be
        reset to draft by a reviewer, unlocking the assignment for editing."""
        assignment = assignment_fixture["assignment"]
        assignment.status = start_status
        assignment.save(update_fields=["status"])

        response = _set_status(
            assignment_fixture["reviewer_client"], assignment.id, target_status
        )

        assert response.status_code == 200
        assert response.data["status"] == "draft"
        assignment.refresh_from_db()
        assert assignment.status == "draft"
        assert RequirementAssignmentEvent.objects.filter(
            assignment=assignment, event_type="draft"
        ).exists()

    def test_reopen_to_draft_clears_reviewer_observation_event_notes(
        self, assignment_fixture
    ):
        assignment = assignment_fixture["assignment"]
        assignment.status = "changes_requested"
        assignment.save(update_fields=["status"])

        response = _set_status(
            assignment_fixture["reviewer_client"],
            assignment.id,
            "draft",
            observation="this note must be dropped",
        )

        assert response.status_code == 200
        event = RequirementAssignmentEvent.objects.get(
            assignment=assignment, event_type="draft"
        )
        assert event.event_notes is None

    def test_invalid_transition_is_rejected(self, assignment_fixture):
        assignment = assignment_fixture["assignment"]
        assert assignment.status == "draft"

        response = _set_status(
            assignment_fixture["reviewer_client"], assignment.id, "closed"
        )

        assert response.status_code == 400
        assignment.refresh_from_db()
        assert assignment.status == "draft"

    def test_missing_status_is_rejected(self, assignment_fixture):
        assignment = assignment_fixture["assignment"]
        response = assignment_fixture["reviewer_client"].post(
            f"/api/requirement-assignments/{assignment.id}/set_status/", data={}
        )
        assert response.status_code == 400

    def test_respondent_cannot_reopen_to_draft(self, assignment_fixture, monkeypatch):
        """reviewer_only transitions must be forbidden to respondent-scoped users."""
        assignment = assignment_fixture["assignment"]
        assignment.status = "submitted"
        assignment.save(update_fields=["status"])
        folder = assignment_fixture["folder"]

        monkeypatch.setattr(
            core_views,
            "get_respondent_scoped_folder_ids",
            lambda user: {folder.id},
        )

        response = _set_status(
            assignment_fixture["actor_client"], assignment.id, "draft"
        )

        assert response.status_code == 403
        assignment.refresh_from_db()
        assert assignment.status == "submitted"

    def test_actor_can_submit_in_progress(self, assignment_fixture):
        assignment = assignment_fixture["assignment"]
        assignment.status = "in_progress"
        assignment.save(update_fields=["status"])

        response = _set_status(
            assignment_fixture["actor_client"], assignment.id, "submitted"
        )

        assert response.status_code == 200
        assignment.refresh_from_db()
        assert assignment.status == "submitted"

    def test_non_actor_cannot_submit_in_progress(self, assignment_fixture):
        """actor_only transitions must be forbidden to users not assigned as actor."""
        assignment = assignment_fixture["assignment"]
        assignment.status = "in_progress"
        assignment.save(update_fields=["status"])

        response = _set_status(
            assignment_fixture["other_reviewer_client"], assignment.id, "submitted"
        )

        assert response.status_code == 403
        assignment.refresh_from_db()
        assert assignment.status == "in_progress"


@pytest.mark.django_db
class TestEditableStatuses:
    """SUP-1488 narrowed EDITABLE_STATUSES to ("draft",) once "Reopen for
    editing" became the only supported path back into an editable state."""

    def _patch(self, client, assignment):
        return client.patch(
            f"/api/requirement-assignments/{assignment.id}/",
            data={"folder": str(assignment.folder.id)},
            format="json",
        )

    def test_draft_assignment_is_editable(self, assignment_fixture):
        assignment = assignment_fixture["assignment"]
        assert assignment.status == "draft"
        response = self._patch(assignment_fixture["reviewer_client"], assignment)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "blocked_status",
        ["in_progress", "submitted", "changes_requested", "closed"],
    )
    def test_non_draft_assignment_is_not_editable(
        self, assignment_fixture, blocked_status
    ):
        assignment = assignment_fixture["assignment"]
        assignment.status = blocked_status
        assignment.save(update_fields=["status"])

        response = self._patch(assignment_fixture["reviewer_client"], assignment)

        assert response.status_code == 403

    def test_non_draft_assignment_cannot_be_deleted(self, assignment_fixture):
        assignment = assignment_fixture["assignment"]
        assignment.status = "in_progress"
        assignment.save(update_fields=["status"])

        response = assignment_fixture["reviewer_client"].delete(
            f"/api/requirement-assignments/{assignment.id}/"
        )

        assert response.status_code == 403
        assert RequirementAssignment.objects.filter(id=assignment.id).exists()

    def test_draft_assignment_can_be_deleted(self, assignment_fixture):
        assignment = assignment_fixture["assignment"]
        assert assignment.status == "draft"

        response = assignment_fixture["reviewer_client"].delete(
            f"/api/requirement-assignments/{assignment.id}/"
        )

        assert response.status_code == 204
        assert not RequirementAssignment.objects.filter(id=assignment.id).exists()
