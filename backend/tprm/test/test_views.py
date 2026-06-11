"""
Tests for tprm.views.

Scope: the destroy-409 contract on EntityViewSet, introduced by the DORA
Art. 28(2) subcontracting data model. When an Entity is referenced by any
SolutionSubcontractor row, on_delete=PROTECT blocks the delete; the view
catches the resulting ProtectedError and returns a structured 409 instead of
Django's default 500.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder
from tprm.models import (
    Contract,
    Entity,
    Solution,
    SolutionSubcontractor,
)
from tprm.views import EntityViewSet

User = get_user_model()


class EntityDestroyConflictTestCase(TestCase):
    """
    Verify that deleting an Entity referenced as a subcontractor returns
    409 Conflict with a structured body, rather than 500 from the uncaught
    ProtectedError.
    """

    def setUp(self):
        self.folder = Folder.objects.create(name="Destroy Test Folder")
        self.user = User.objects.create_user(
            email="destroy@test.local", password="password"
        )
        self.direct = Entity.objects.create(
            name="Direct",
            folder=self.folder,
            legal_identifiers={"LEI": "DIRE1"},
        )
        self.subcontractor = Entity.objects.create(
            name="Blocking Sub",
            folder=self.folder,
            legal_identifiers={"LEI": "BLKS1"},
        )
        self.orphan = Entity.objects.create(
            name="Orphan Entity",
            folder=self.folder,
            legal_identifiers={"LEI": "ORPH1"},
        )
        self.solution = Solution.objects.create(
            name="Blocking Solution", provider_entity=self.direct
        )
        self.contract = Contract.objects.create(
            name="Blocking Contract",
            ref_id="CA-BLOCK",
            folder=self.folder,
            provider_entity=self.direct,
            beneficiary_entity=self.direct,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        self.contract.solutions.add(self.solution)
        SolutionSubcontractor.objects.create(
            solution=self.solution, subcontractor=self.subcontractor
        )
        self.factory = APIRequestFactory()

    def _call_destroy(self, entity):
        view = EntityViewSet.as_view({"delete": "destroy"})
        request = self.factory.delete(f"/entities/{entity.id}/")
        force_authenticate(request, user=self.user)
        return view(request, pk=entity.id)

    @patch(
        "iam.models.RoleAssignment.get_accessible_object_ids",
        side_effect=lambda folder, user, model: (
            list(model.objects.values_list("id", flat=True)),
            list(model.objects.values_list("id", flat=True)),
            list(model.objects.values_list("id", flat=True)),
        ),
    )
    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_destroy_returns_409_when_entity_is_subcontractor(self, _is_allowed, _ids):
        """ProtectedError from on_delete=PROTECT surfaces as structured 409."""
        response = self._call_destroy(self.subcontractor)
        self.assertEqual(response.status_code, 409)
        data = response.data
        self.assertIn("detail", data)
        self.assertIn("Blocking Sub", data["detail"])
        self.assertIn("blocking_subcontracts", data)
        self.assertEqual(len(data["blocking_subcontracts"]), 1)
        entry = data["blocking_subcontracts"][0]
        self.assertEqual(entry["solution_name"], "Blocking Solution")
        # Entity must still exist — destroy was prevented.
        self.assertTrue(Entity.objects.filter(pk=self.subcontractor.pk).exists())

    @patch(
        "iam.models.RoleAssignment.get_accessible_object_ids",
        side_effect=lambda folder, user, model: (
            list(model.objects.values_list("id", flat=True)),
            list(model.objects.values_list("id", flat=True)),
            list(model.objects.values_list("id", flat=True)),
        ),
    )
    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_destroy_succeeds_when_entity_is_not_referenced(self, _is_allowed, _ids):
        """Happy path: destroy returns 204 and actually deletes."""
        response = self._call_destroy(self.orphan)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Entity.objects.filter(pk=self.orphan.pk).exists())

    @patch(
        "iam.models.RoleAssignment.get_accessible_object_ids",
        side_effect=lambda folder, user, model: (
            list(model.objects.values_list("id", flat=True)),
            list(model.objects.values_list("id", flat=True)),
            list(model.objects.values_list("id", flat=True)),
        ),
    )
    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_destroy_lists_all_blocking_solutions(self, _is_allowed, _ids):
        """Response carries all solutions that block deletion, not just the first."""
        # Add a second solution that also subcontracts to this entity.
        solution_b = Solution.objects.create(
            name="Second Blocking Solution", provider_entity=self.direct
        )
        SolutionSubcontractor.objects.create(
            solution=solution_b, subcontractor=self.subcontractor
        )
        response = self._call_destroy(self.subcontractor)
        self.assertEqual(response.status_code, 409)
        solution_names = sorted(
            e["solution_name"] for e in response.data["blocking_subcontracts"]
        )
        self.assertEqual(
            solution_names,
            ["Blocking Solution", "Second Blocking Solution"],
        )
