import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import Actor
from iam.models import Folder, User
from pmbok.models import (
    ResponsibilityMatrixActivity,
    ResponsibilityAssignment,
    ResponsibilityMatrix,
    ResponsibilityMatrixActor,
    ResponsibilityRole,
)
from pmbok.views import ResponsibilityMatrixActorViewSet, ResponsibilityMatrixViewSet


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="matrix_test_admin@example.com", password="x"
    )


@pytest.fixture
def seeded_roles(db):
    """Seed the builtin RACI/RASCI/RAPID roles.

    The data migration that seeds these in production is gated on the root folder
    existing (which is created by startup.py post-migrate). The test DB doesn't
    run startup, so we seed via the model classmethod directly.
    """
    ResponsibilityRole.create_default_roles()


@pytest.fixture
def matrix(seeded_roles):
    """A RACI matrix in the root folder with builtin RACI roles attached."""
    m = ResponsibilityMatrix.objects.create(
        name="Test RACI", folder=Folder.get_root_folder(), preset="raci"
    )
    raci_roles = ResponsibilityRole.objects.filter(
        taxonomy="raci", builtin=True
    ).order_by("order", "code")
    assert raci_roles.count() == 4, "RACI seed missing"
    m.roles.set(raci_roles)
    return m


@pytest.fixture
def activity(matrix):
    return ResponsibilityMatrixActivity.objects.create(
        matrix=matrix, name="Draft policy", order=0
    )


@pytest.fixture
def actor_in_matrix(db, matrix):
    """An actor attached to the matrix via ResponsibilityMatrixActor."""
    user = User.objects.create_user(email="member@example.com", password="x")
    actor = user.actor
    ResponsibilityMatrixActor.objects.create(matrix=matrix, actor=actor, order=0)
    return actor


@pytest.fixture
def actor_outside_matrix(db):
    """An actor that exists but is NOT a member of any matrix."""
    user = User.objects.create_user(email="outsider@example.com", password="x")
    return user.actor


def _call_cycle(matrix, activity, actor, user, direction="forward"):
    factory = APIRequestFactory()
    view = ResponsibilityMatrixViewSet.as_view({"post": "cycle_cell"})
    req = factory.post(
        f"/api/pmbok/responsibility-matrices/{matrix.id}/cycle-cell/",
        {"activity": str(activity.id), "actor": str(actor.id), "direction": direction},
        format="json",
    )
    force_authenticate(req, user=user)
    return view(req, pk=str(matrix.id))


@pytest.mark.django_db
class TestCycleCell:
    """Cell cycling: empty → R → A → C → I → empty (RACI order)."""

    def test_forward_cycle_walks_all_roles_then_empties(
        self, matrix, activity, actor_in_matrix, superuser
    ):
        seen_codes = []
        for _ in range(6):
            resp = _call_cycle(matrix, activity, actor_in_matrix, superuser)
            assert resp.status_code == 200
            role = resp.data.get("role")
            seen_codes.append(role["code"] if role else None)

        # RACI order from seed migration is R, A, C, I (by .order field)
        assert seen_codes == ["R", "A", "C", "I", None, "R"]

    def test_backward_cycle_from_empty_picks_last_role(
        self, matrix, activity, actor_in_matrix, superuser
    ):
        resp = _call_cycle(
            matrix, activity, actor_in_matrix, superuser, direction="backward"
        )
        assert resp.status_code == 200
        assert resp.data["role"]["code"] == "I"

    def test_response_includes_assignment_id_when_filled(
        self, matrix, activity, actor_in_matrix, superuser
    ):
        resp = _call_cycle(matrix, activity, actor_in_matrix, superuser)
        assignment_id = resp.data["assignment_id"]
        assert assignment_id is not None
        # And the assignment really exists in the DB with that ID
        assert ResponsibilityAssignment.objects.filter(id=assignment_id).exists()

    def test_response_clears_assignment_id_when_cycled_to_empty(
        self, matrix, activity, actor_in_matrix, superuser
    ):
        # Cycle forward 4 times to reach the wrap-to-empty step
        for _ in range(4):
            _call_cycle(matrix, activity, actor_in_matrix, superuser)
        resp = _call_cycle(matrix, activity, actor_in_matrix, superuser)
        assert resp.data["role"] is None
        assert resp.data["assignment_id"] is None
        # And the assignment row is gone
        assert not ResponsibilityAssignment.objects.filter(
            activity=activity, actor=actor_in_matrix
        ).exists()


@pytest.mark.django_db
class TestCycleCellValidation:
    """Inputs that shouldn't be allowed to mutate the DB."""

    def test_rejects_actor_not_in_matrix(
        self, matrix, activity, actor_outside_matrix, superuser
    ):
        resp = _call_cycle(matrix, activity, actor_outside_matrix, superuser)
        assert resp.status_code == 400
        assert "actor is not a member of this matrix" in str(
            resp.data.get("detail", "")
        )
        # No assignment was created despite passing valid activity + actor UUIDs
        assert not ResponsibilityAssignment.objects.filter(
            activity=activity, actor=actor_outside_matrix
        ).exists()

    def test_rejects_activity_from_different_matrix(
        self, matrix, actor_in_matrix, superuser
    ):
        other_matrix = ResponsibilityMatrix.objects.create(
            name="Other matrix", folder=Folder.get_root_folder()
        )
        foreign_activity = ResponsibilityMatrixActivity.objects.create(
            matrix=other_matrix, name="Wrong matrix activity"
        )
        resp = _call_cycle(matrix, foreign_activity, actor_in_matrix, superuser)
        assert resp.status_code == 400
        assert "activity does not belong to this matrix" in str(
            resp.data.get("detail", "")
        )

    def test_rejects_missing_payload_fields(self, matrix, superuser):
        factory = APIRequestFactory()
        view = ResponsibilityMatrixViewSet.as_view({"post": "cycle_cell"})
        req = factory.post(
            f"/api/pmbok/responsibility-matrices/{matrix.id}/cycle-cell/",
            {},
            format="json",
        )
        force_authenticate(req, user=superuser)
        resp = view(req, pk=str(matrix.id))
        assert resp.status_code == 400


@pytest.mark.django_db
class TestActorRemovalCascade:
    """Removing an actor from a matrix must wipe their assignments in that matrix
    (and only that matrix)."""

    def test_remove_actor_deletes_assignments_in_same_matrix(
        self, matrix, activity, actor_in_matrix, superuser
    ):
        # Set a role for this actor
        _call_cycle(matrix, activity, actor_in_matrix, superuser)
        assert ResponsibilityAssignment.objects.filter(
            activity=activity, actor=actor_in_matrix
        ).exists()

        membership = ResponsibilityMatrixActor.objects.get(
            matrix=matrix, actor=actor_in_matrix
        )

        factory = APIRequestFactory()
        view = ResponsibilityMatrixActorViewSet.as_view({"delete": "destroy"})
        req = factory.delete(
            f"/api/pmbok/responsibility-matrix-actors/{membership.id}/"
        )
        force_authenticate(req, user=superuser)
        resp = view(req, pk=str(membership.id))
        assert resp.status_code == 204

        # Membership AND the assignment are gone
        assert not ResponsibilityMatrixActor.objects.filter(id=membership.id).exists()
        assert not ResponsibilityAssignment.objects.filter(
            activity=activity, actor=actor_in_matrix
        ).exists()

    def test_remove_actor_does_not_touch_other_matrix_assignments(
        self, matrix, activity, actor_in_matrix, superuser
    ):
        # Make a second matrix where the same actor has an assignment
        other_matrix = ResponsibilityMatrix.objects.create(
            name="Other", folder=Folder.get_root_folder()
        )
        other_matrix.roles.set(matrix.roles.all())
        other_activity = ResponsibilityMatrixActivity.objects.create(
            matrix=other_matrix, name="Other activity"
        )
        other_membership = ResponsibilityMatrixActor.objects.create(
            matrix=other_matrix, actor=actor_in_matrix
        )
        _call_cycle(other_matrix, other_activity, actor_in_matrix, superuser)
        assert ResponsibilityAssignment.objects.filter(activity=other_activity).exists()

        # Now remove the actor from the *first* matrix only
        first_membership = ResponsibilityMatrixActor.objects.get(
            matrix=matrix, actor=actor_in_matrix
        )
        factory = APIRequestFactory()
        view = ResponsibilityMatrixActorViewSet.as_view({"delete": "destroy"})
        req = factory.delete(
            f"/api/pmbok/responsibility-matrix-actors/{first_membership.id}/"
        )
        force_authenticate(req, user=superuser)
        view(req, pk=str(first_membership.id))

        # The other matrix's assignment for this actor must still be intact
        assert ResponsibilityAssignment.objects.filter(
            activity=other_activity, actor=actor_in_matrix
        ).exists()
        assert ResponsibilityMatrixActor.objects.filter(id=other_membership.id).exists()


@pytest.mark.django_db
class TestFolderPropagation:
    """Moving a matrix to a different folder must update its children's folder
    so IAM scoping stays consistent."""

    def test_matrix_move_updates_descendants(
        self, matrix, activity, actor_in_matrix, superuser
    ):
        _call_cycle(matrix, activity, actor_in_matrix, superuser)
        assignment = ResponsibilityAssignment.objects.get(
            activity=activity, actor=actor_in_matrix
        )
        membership = ResponsibilityMatrixActor.objects.get(
            matrix=matrix, actor=actor_in_matrix
        )
        assert activity.folder_id == matrix.folder_id
        assert assignment.folder_id == matrix.folder_id
        assert membership.folder_id == matrix.folder_id

        # Move the matrix to a new folder
        new_folder = Folder.objects.create(
            name="Other domain",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=Folder.get_root_folder(),
        )
        matrix.folder = new_folder
        matrix.save()

        activity.refresh_from_db()
        assignment.refresh_from_db()
        membership.refresh_from_db()
        assert activity.folder_id == new_folder.id
        assert assignment.folder_id == new_folder.id
        assert membership.folder_id == new_folder.id
