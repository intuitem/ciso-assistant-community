"""Tests for the transactional folder reorganisation endpoint.

The endpoint exists so that a reorganisation drafted client-side lands all at once:
the folder tree is what the IAM resolves role assignments against, so a partial apply
would leave access in a state nobody designed.
"""

import pytest
from rest_framework import status

from core.models import Perimeter
from core.serializers import FolderWriteSerializer
from iam.models import Folder

ENDPOINT = "/api/folders/reorganize/"

# `authenticated_client` is the suite's admin fixture (knox token, BI-UG-ADM): these
# tests exercise the endpoint, not the permission layer, which has its own tests.


def _tree():
    """root -> a -> a1, root -> b -> b1"""
    root = Folder.get_root_folder()
    a = Folder.objects.create(name="reorg A", parent_folder=root)
    a1 = Folder.objects.create(name="reorg A1", parent_folder=a)
    b = Folder.objects.create(name="reorg B", parent_folder=root)
    b1 = Folder.objects.create(name="reorg B1", parent_folder=b)
    return root, a, a1, b, b1


@pytest.fixture
def nesting_allowed(monkeypatch):
    """Run with a serializer that permits nesting, as the PRO edition's does.

    The endpoint is edition-independent — it reuses whichever FolderWriteSerializer
    MODULE_PATHS resolves — so leaving these cases to the community policy would mean
    never testing the endpoint's own logic: the two-phase apply, its atomicity, and
    the inverse it returns. Cycle protection is untouched; that lives in Folder.save().
    """

    def permissive(self, value):
        return self._resolve_parent_folder(value)

    monkeypatch.setattr(FolderWriteSerializer, "validate_parent_folder", permissive)


@pytest.mark.django_db
class TestFolderReorganize:
    def test_cannot_be_used_to_bypass_the_pro_gate(self, authenticated_client):
        """Nesting is refused here exactly as it is on a single PATCH."""
        _, a, a1, b, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a1.id),
                        "parent_folder": str(b.id),
                        "from_parent": str(a.id),
                    }
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["parent_folder"] == ["subDomainsRequirePro"]

        a1.refresh_from_db()
        assert a1.parent_folder_id == a.id

    def test_rejects_empty_payload(self, authenticated_client):
        response = authenticated_client.post(ENDPOINT, {"moves": []}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_rejects_move_without_from_parent(self, authenticated_client):
        """The concurrency guard is mandatory, not opt-in."""
        _, a, a1, b, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT,
            {"moves": [{"folder": str(a1.id), "parent_folder": str(b.id)}]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "from_parent" in response.json()["moves"]

        a1.refresh_from_db()
        assert a1.parent_folder_id == a.id

    def test_rejects_duplicate_folder(self, authenticated_client):
        root, a, _, b, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a.id),
                        "parent_folder": str(b.id),
                        "from_parent": str(root.id),
                    },
                    {
                        "folder": str(a.id),
                        "parent_folder": str(root.id),
                        "from_parent": str(root.id),
                    },
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_applies_several_moves_at_once(self, authenticated_client, nesting_allowed):
        root, a, a1, b, b1 = _tree()
        response = authenticated_client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a1.id),
                        "parent_folder": str(b.id),
                        "from_parent": str(a.id),
                    },
                    {
                        "folder": str(b1.id),
                        "parent_folder": str(a.id),
                        "from_parent": str(b.id),
                    },
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["applied"] == 2

        a1.refresh_from_db()
        b1.refresh_from_db()
        assert a1.parent_folder_id == b.id
        assert b1.parent_folder_id == a.id

    def test_swapping_subtrees_survives_the_transient_cycle(
        self, authenticated_client, nesting_allowed
    ):
        """root->a->a1 becomes root->a1->a.

        Whichever half is applied first is momentarily a cycle, so this only passes
        because every mover is parked at the root before any is attached.
        """
        root, a, a1, _, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a1.id),
                        "parent_folder": str(root.id),
                        "from_parent": str(a.id),
                    },
                    {
                        "folder": str(a.id),
                        "parent_folder": str(a1.id),
                        "from_parent": str(root.id),
                    },
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        a.refresh_from_db()
        a1.refresh_from_db()
        assert a1.parent_folder_id == root.id
        assert a.parent_folder_id == a1.id
        # The closure table must agree with the new shape, not the old one.
        assert a in a1.get_sub_folders()
        assert a1 not in a.get_sub_folders()

    def test_stale_draft_is_refused_whole(self, authenticated_client):
        """If anything moved since drafting, nothing is applied."""
        root, a, a1, b, b1 = _tree()
        a1.parent_folder = b  # somebody else moved it in the meantime
        a1.save()

        response = authenticated_client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a1.id),
                        "parent_folder": str(root.id),
                        "from_parent": str(a.id),  # what the draft believed
                    },
                    {
                        "folder": str(b1.id),
                        "parent_folder": str(a.id),
                        "from_parent": str(b.id),
                    },
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["conflicts"][0]["reason"] == "movedElsewhere"

        # The unaffected move must not have been applied either.
        b1.refresh_from_db()
        assert b1.parent_folder_id == b.id

    def test_inverse_restores_the_previous_shape(
        self, authenticated_client, nesting_allowed
    ):
        root, a, a1, b, b1 = _tree()
        client = authenticated_client
        response = client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a1.id),
                        "parent_folder": str(b.id),
                        "from_parent": str(a.id),
                    },
                    {
                        "folder": str(b1.id),
                        "parent_folder": str(a.id),
                        "from_parent": str(b.id),
                    },
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "inverse" not in response.json(), (
            "the endpoint must not hand back a replayable undo payload"
        )

        back = [
            {
                "folder": str(a1.id),
                "parent_folder": str(a.id),
                "from_parent": str(b.id),
            },
            {
                "folder": str(b1.id),
                "parent_folder": str(b.id),
                "from_parent": str(a.id),
            },
        ]
        revert = client.post(ENDPOINT, {"moves": back}, format="json")
        assert revert.status_code == status.HTTP_200_OK

        a1.refresh_from_db()
        b1.refresh_from_db()
        assert a1.parent_folder_id == a.id
        assert b1.parent_folder_id == b.id

    def test_noop_moves_are_skipped_not_applied(self, authenticated_client):
        root, a, a1, _, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a1.id),
                        "parent_folder": str(a.id),
                        "from_parent": str(a.id),
                    }
                ]
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"applied": 0, "deleted": 0, "skipped": 1}


@pytest.mark.django_db
class TestFolderReorganizeDeletes:
    """Deleting from the board is restricted to empty leaves.

    That restriction is what makes it safe to draft a deletion and apply it later:
    a stale staged delete has nothing inside it to destroy.
    """

    def test_deletes_an_empty_leaf(self, authenticated_client):
        _, _, a1, _, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT, {"deletes": [{"folder": str(a1.id)}]}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["deleted"] == 1
        assert not Folder.objects.filter(pk=a1.pk).exists()

    def test_refuses_a_folder_with_sub_domains(self, authenticated_client):
        _, a, a1, _, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT, {"deletes": [{"folder": str(a.id)}]}, format="json"
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["conflicts"][0]["reason"] == "hasSubDomains"
        assert Folder.objects.filter(pk=a.pk).exists()
        assert Folder.objects.filter(pk=a1.pk).exists()

    def test_refuses_a_folder_holding_content(self, authenticated_client):
        _, _, a1, _, _ = _tree()
        Perimeter.objects.create(name="occupant", folder=a1)
        response = authenticated_client.post(
            ENDPOINT, {"deletes": [{"folder": str(a1.id)}]}, format="json"
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["conflicts"][0]["reason"] == "notEmpty"
        assert Folder.objects.filter(pk=a1.pk).exists()

    def test_refuses_to_delete_the_root(self, authenticated_client):
        root, _, _, _, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT, {"deletes": [{"folder": str(root.id)}]}, format="json"
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["conflicts"][0]["reason"] == "cannotDeleteRoot"

    def test_a_folder_emptied_by_the_same_draft_becomes_deletable(
        self, authenticated_client, nesting_allowed
    ):
        """Moves run before deletes, so emptying and removing a level is one apply."""
        root, a, a1, b, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a1.id),
                        "parent_folder": str(b.id),
                        "from_parent": str(a.id),
                    }
                ],
                "deletes": [{"folder": str(a.id)}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"applied": 1, "deleted": 1, "skipped": 0}

        a1.refresh_from_db()
        assert a1.parent_folder_id == b.id, "the child must have been rehomed"
        assert not Folder.objects.filter(pk=a.pk).exists()

    def test_a_refused_delete_rolls_the_moves_back(
        self, authenticated_client, nesting_allowed
    ):
        """All or nothing: a blocked delete must not leave the moves applied."""
        root, a, a1, b, b1 = _tree()
        Perimeter.objects.create(name="occupant", folder=a)

        response = authenticated_client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a1.id),
                        "parent_folder": str(b.id),
                        "from_parent": str(a.id),
                    }
                ],
                "deletes": [{"folder": str(a.id)}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["conflicts"][0]["reason"] == "notEmpty"

        a1.refresh_from_db()
        assert a1.parent_folder_id == a.id, "the move must have been rolled back"
        assert Folder.objects.filter(pk=a.pk).exists()

    def test_refuses_moving_and_deleting_the_same_folder(self, authenticated_client):
        root, a, a1, b, _ = _tree()
        response = authenticated_client.post(
            ENDPOINT,
            {
                "moves": [
                    {
                        "folder": str(a1.id),
                        "parent_folder": str(b.id),
                        "from_parent": str(a.id),
                    }
                ],
                "deletes": [{"folder": str(a1.id)}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["conflicts"][0]["reason"] == "movedAndDeleted"
        assert Folder.objects.filter(pk=a1.pk).exists()
