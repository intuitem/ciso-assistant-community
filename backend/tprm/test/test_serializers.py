from unittest.mock import patch, MagicMock, PropertyMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from core.models import ComplianceAssessment, Framework, Perimeter
from iam.models import Folder
from tprm.models import Entity, EntityAssessment, Representative, Solution
from tprm.serializers import (
    EntityReadSerializer,
    EntityWriteSerializer,
    EntityImportExportSerializer,
    EntityAssessmentReadSerializer,
    EntityAssessmentWriteSerializer,
    RepresentativeReadSerializer,
    RepresentativeWriteSerializer,
    SolutionReadSerializer,
    SolutionWriteSerializer,
)

User = get_user_model()


class EntitySerializersTestCase(TestCase):
    """Tests for Entity-related serializers"""

    def setUp(self):
        self.folder = Folder.objects.create(name="Test Folder")
        self.entity_data = {
            "name": "Test Entity",
            "description": "Entity description",
            "mission": "Entity mission",
            "reference_link": "https://example.com",
            "folder": self.folder,
        }
        self.entity = Entity.objects.create(**self.entity_data)
        self.owned_folder = Folder.objects.create(name="Owned Folder")
        self.entity.owned_folders.add(self.owned_folder)

    def test_entity_read_serializer(self):
        """Test that EntityReadSerializer correctly serializes an Entity"""
        serializer = EntityReadSerializer(self.entity)
        data = serializer.data

        self.assertEqual(data["name"], self.entity_data["name"])
        self.assertEqual(data["description"], self.entity_data["description"])
        self.assertEqual(data["mission"], self.entity_data["mission"])
        self.assertEqual(data["reference_link"], self.entity_data["reference_link"])
        self.assertIn("folder", data)
        self.assertIn("owned_folders", data)

    def test_entity_write_serializer(self):
        """Test that EntityWriteSerializer correctly creates an Entity"""
        new_entity_data = {
            "name": "New Entity",
            "description": "New description",
            "mission": "New mission",
            "reference_link": "https://newexample.com",
            "folder": self.folder.id,
        }

        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_request.user = mock_user

        with patch("iam.models.RoleAssignment.is_access_allowed", return_value=True):
            serializer = EntityWriteSerializer(
                data=new_entity_data, context={"request": mock_request}
            )
            self.assertTrue(serializer.is_valid())
            entity = serializer.save()

        self.assertEqual(entity.name, new_entity_data["name"])
        self.assertEqual(entity.description, new_entity_data["description"])
        self.assertEqual(entity.mission, new_entity_data["mission"])
        self.assertEqual(entity.reference_link, new_entity_data["reference_link"])
        self.assertEqual(entity.folder, self.folder)

    def test_entity_import_export_serializer(self):
        """Test that EntityImportExportSerializer correctly serializes an Entity for import/export"""
        serializer = EntityImportExportSerializer(self.entity)
        data = serializer.data

        self.assertEqual(data["name"], self.entity_data["name"])
        self.assertEqual(data["description"], self.entity_data["description"])
        self.assertEqual(data["mission"], self.entity_data["mission"])
        self.assertEqual(data["reference_link"], self.entity_data["reference_link"])
        self.assertIn("folder", data)
        self.assertIn("owned_folders", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)


class EntityAssessmentSerializersTestCase(TestCase):
    """Tests for EntityAssessment-related serializers"""

    def setUp(self):
        self.folder = Folder.objects.create(name="Test Folder")
        self.perimeter_folder = Folder.objects.create(name="Perimeter Folder")
        self.perimeter = Perimeter.objects.create(
            name="Test Perimeter", folder=self.perimeter_folder
        )
        self.entity = Entity.objects.create(name="Test Entity", folder=self.folder)

        self.framework = Framework.objects.create(
            name="Test Framework", min_score=0, max_score=100
        )

        self.assessment = EntityAssessment.objects.create(
            name="Test Assessment",
            entity=self.entity,
            folder=self.folder,
            perimeter=self.perimeter,
        )

        self.user = User.objects.create_user(
            email="test@example.com", password="password"
        )
        self.assessment.authors.add(self.user.actor)
        self.assessment.reviewers.add(self.user.actor)

        self.solution = Solution.objects.create(
            name="Test Solution", provider_entity=self.entity
        )
        self.assessment.solutions.add(self.solution)

        self.representative = User.objects.create_user(
            email="rep@example.com", password="password"
        )
        self.assessment.representatives.add(self.representative)

    def test_entity_assessment_read_serializer(self):
        """Test that EntityAssessmentReadSerializer correctly serializes an EntityAssessment"""
        serializer = EntityAssessmentReadSerializer(self.assessment)
        data = serializer.data

        self.assertEqual(data["name"], "Test Assessment")
        self.assertIn("entity", data)
        self.assertIn("folder", data)
        self.assertIn("perimeter", data)
        self.assertIn("solutions", data)
        self.assertIn("representatives", data)
        self.assertIn("authors", data)
        self.assertIn("reviewers", data)

    # The use of Audit for testing this methode create a mess bc of the databases, become a test with too many patch and mock
    @patch("core.models.ComplianceAssessment.objects.create")
    @patch("iam.models.Folder.objects.create")
    @patch.object(EntityAssessment, "compliance_assessment", new_callable=PropertyMock)
    @patch(
        "tprm.serializers.EntityAssessmentWriteSerializer._assign_third_party_respondents"
    )
    @patch(
        "tprm.serializers.EntityAssessmentWriteSerializer._create_requirement_assignment"
    )
    def test_entity_assessment_write_serializer_with_audit(
        self,
        mock_create_requirement_assignment,
        mock_assign_third_party,
        mock_compliance_assessment,
        mock_folder_create,
        mock_audit_create,
    ):
        """Test that EntityAssessmentWriteSerializer correctly creates an EntityAssessment with audit"""
        mock_enclave_folder = MagicMock()
        mock_folder_create.return_value = mock_enclave_folder

        mock_audit = MagicMock(spec=ComplianceAssessment)
        mock_audit._state = MagicMock()
        mock_audit.folder = mock_enclave_folder
        mock_audit_create.return_value = mock_audit

        mock_compliance_assessment.return_value = mock_audit

        data = {
            "name": "New Assessment",
            "entity": self.entity.id,
            "folder": self.folder.id,
            "perimeter": self.perimeter.id,
            "create_audit": True,
            "framework": self.framework.id,
            "selected_implementation_groups": ["group1", "group2"],
        }
        with patch("iam.models.RoleAssignment.is_access_allowed", return_value=True):
            serializer = EntityAssessmentWriteSerializer(
                data=data, context={"request": MagicMock()}
            )
            self.assertTrue(serializer.is_valid())
            serializer.save()

        mock_audit_create.assert_called_once()
        self.assertEqual(mock_audit_create.call_args[1]["name"], data["name"])
        self.assertEqual(
            mock_audit_create.call_args[1]["framework"].id, self.framework.id
        )
        self.assertEqual(mock_audit_create.call_args[1]["perimeter"], self.perimeter)
        self.assertEqual(
            mock_audit_create.call_args[1]["selected_implementation_groups"],
            data["selected_implementation_groups"],
        )

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_entity_assessment_write_serializer_without_framework(
        self, mock_is_access_allowed
    ):
        """Test that EntityAssessmentWriteSerializer raises ValidationError if framework is not provided"""
        data = {
            "name": "New Assessment",
            "entity": self.entity.id,
            "folder": self.folder.id,
            "perimeter": self.perimeter.id,
            "create_audit": True,
        }

        serializer = EntityAssessmentWriteSerializer(
            data=data, context={"request": MagicMock()}
        )
        self.assertTrue(serializer.is_valid())

        with self.assertRaises(ValidationError) as context:
            serializer.save()

        self.assertIn("framework", context.exception.detail)

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    @patch(
        "tprm.serializers.EntityAssessmentWriteSerializer._assign_third_party_respondents"
    )
    def test_entity_assessment_write_update(self, mock_assign, mock_is_access_allowed):
        """Test that EntityAssessmentWriteSerializer correctly updates an EntityAssessment"""
        new_rep = User.objects.create_user(
            email="newrep@example.com", password="password"
        )

        data = {"name": "Updated Assessment", "representatives": [new_rep.id]}

        request = MagicMock()
        request.user.is_authenticated = True

        with patch(
            "iam.models.RoleAssignment.get_accessible_object_ids",
            return_value=([new_rep.id], None),
        ):
            serializer = EntityAssessmentWriteSerializer(
                self.assessment, data=data, partial=True, context={"request": request}
            )
            self.assertTrue(serializer.is_valid())
        updated_assessment = serializer.save()

        self.assertEqual(updated_assessment.name, "Updated Assessment")
        self.assertIn(new_rep, updated_assessment.representatives.all())

        self.assertEqual(updated_assessment.representatives.count(), 1)
        self.assertNotIn(self.representative, updated_assessment.representatives.all())

        mock_assign.assert_called_once()


class RepresentativeSerializersTestCase(TestCase):
    """Tests for Representative-related serializers"""

    def setUp(self):
        self.folder = Folder.objects.create(name="Test Folder")
        self.entity = Entity.objects.create(name="Test Entity", folder=self.folder)
        self.user = User.objects.create_user(
            email="existing@example.com", password="password"
        )

        self.representative_data = {
            "email": "rep@example.com",
            "first_name": "Test",
            "last_name": "Representative",
            "phone": "123456789",
            "role": "Manager",
            "description": "Test description",
            "entity": self.entity,
        }
        self.representative = Representative.objects.create(**self.representative_data)

    def test_representative_read_serializer(self):
        """Test that RepresentativeReadSerializer correctly serializes a Representative"""
        serializer = RepresentativeReadSerializer(self.representative)
        data = serializer.data

        self.assertEqual(data["email"], self.representative_data["email"])
        self.assertEqual(data["first_name"], self.representative_data["first_name"])
        self.assertEqual(data["last_name"], self.representative_data["last_name"])
        self.assertEqual(data["phone"], self.representative_data["phone"])
        self.assertEqual(data["role"], self.representative_data["role"])
        self.assertEqual(data["description"], self.representative_data["description"])
        self.assertIn("entity", data)
        self.assertIn("user", data)

    @patch("tprm.serializers.RepresentativeWriteSerializer._create_or_update_user")
    def test_representative_write_serializer_create_user(self, mock_create_or_update):
        """Test that RepresentativeWriteSerializer correctly creates a Representative and user"""
        data = {
            "email": "newrep@example.com",
            "first_name": "New",
            "last_name": "Representative",
            "entity": self.entity.id,
            "create_user": True,
        }

        with patch("iam.models.RoleAssignment.is_access_allowed", return_value=True):
            serializer = RepresentativeWriteSerializer(
                data=data, context={"request": MagicMock()}
            )
            self.assertTrue(serializer.is_valid())
            serializer.save()

        mock_create_or_update.assert_called_once()

        call_args = mock_create_or_update.call_args[0]
        self.assertIsInstance(call_args[0], Representative)

        self.assertEqual(call_args[0].email, data["email"])
        self.assertEqual(call_args[0].first_name, data["first_name"])
        self.assertEqual(call_args[0].last_name, data["last_name"])

        self.assertEqual(call_args[1], data["create_user"])

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    @patch("iam.models.User.objects.filter")
    def test_representative_write_serializer_existing_third_party_user(
        self, mock_filter, mock_is_access_allowed
    ):
        """Test that RepresentativeWriteSerializer correctly associates an existing third-party user with a Representative"""
        self.user.is_third_party = True

        mock_filter_result = MagicMock()
        mock_filter_result.first.return_value = self.user
        mock_filter.return_value = mock_filter_result

        data = {
            "email": "existing@example.com",
            "first_name": "Updated",
            "last_name": "User",
            "entity": self.entity.id,
            "create_user": True,
        }

        serializer = RepresentativeWriteSerializer(
            data=data, context={"request": MagicMock()}
        )
        self.assertTrue(serializer.is_valid())
        representative = serializer.save()

        self.assertEqual(representative.user, self.user)

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    @patch("iam.models.User.objects.filter")
    def test_representative_write_serializer_rejects_internal_user(
        self, mock_filter, mock_is_access_allowed
    ):
        """Test that RepresentativeWriteSerializer refuses to convert an internal user to third-party"""
        mock_filter_result = MagicMock()
        mock_filter_result.first.return_value = self.user
        mock_filter.return_value = mock_filter_result

        data = {
            "email": "existing@example.com",
            "first_name": "Updated",
            "last_name": "User",
            "entity": self.entity.id,
            "create_user": True,
        }

        serializer = RepresentativeWriteSerializer(
            data=data, context={"request": MagicMock()}
        )
        self.assertTrue(serializer.is_valid())

        with self.assertRaises(ValidationError):
            serializer.save()

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    @patch("iam.models.User.objects.create_user")
    @patch("iam.models.User.objects.filter")
    def test_representative_write_serializer_error_handling(
        self, mock_filter, mock_create_user, mock_is_access_allowed
    ):
        """Test that RepresentativeWriteSerializer handles errors when creating a user"""
        mock_filter_result = MagicMock()
        mock_filter_result.first.return_value = None
        mock_filter.return_value = mock_filter_result

        mock_create_user.side_effect = Exception("Error creating user")

        data = {
            "email": "error@example.com",
            "first_name": "Error",
            "last_name": "Test",
            "entity": self.entity.id,
            "create_user": True,
        }

        serializer = RepresentativeWriteSerializer(
            data=data, context={"request": MagicMock()}
        )
        self.assertTrue(serializer.is_valid())

        with self.assertRaises(ValidationError):
            serializer.save()


class SolutionSerializersTestCase(TestCase):
    """Tests for Solution-related serializers"""

    def setUp(self):
        self.folder = Folder.objects.create(name="Test Folder")
        self.provider_entity = Entity.objects.create(
            name="Provider Entity", folder=self.folder
        )
        self.recipient_entity = Entity.objects.create(
            name="Recipient Entity", folder=self.folder
        )

        self.solution = Solution.objects.create(
            name="Test Solution",
            description="Solution description",
            provider_entity=self.provider_entity,
            recipient_entity=self.recipient_entity,
            ref_id="SOL-001",
            criticality=3,
        )

    def test_solution_read_serializer(self):
        """Test that SolutionReadSerializer correctly serializes a Solution"""
        serializer = SolutionReadSerializer(self.solution)
        data = serializer.data

        self.assertEqual(data["name"], "Test Solution")
        self.assertEqual(data["description"], "Solution description")
        self.assertEqual(data["ref_id"], "SOL-001")
        self.assertEqual(data["criticality"], 3)
        self.assertIn("provider_entity", data)
        self.assertIn("recipient_entity", data)
        self.assertIn("assets", data)

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_solution_write_serializer(self, mock_is_access_allowed):
        """Test that SolutionWriteSerializer correctly creates a Solution"""
        new_solution_data = {
            "name": "New Solution",
            "description": "New description",
            "provider_entity": self.provider_entity.id,
            "ref_id": "SOL-002",
            "criticality": 2,
        }

        serializer = SolutionWriteSerializer(
            data=new_solution_data, context={"request": MagicMock()}
        )
        self.assertTrue(serializer.is_valid())
        solution = serializer.save()

        self.assertEqual(solution.name, new_solution_data["name"])
        self.assertEqual(solution.description, new_solution_data["description"])
        self.assertEqual(solution.provider_entity, self.provider_entity)
        self.assertEqual(solution.ref_id, new_solution_data["ref_id"])
        self.assertEqual(solution.criticality, new_solution_data["criticality"])
        self.assertIsNone(solution.recipient_entity)


# ===========================================================================
# SolutionSubcontractor serialization + chain semantics
# ===========================================================================


class SolutionSubcontractingChainTestCase(TestCase):
    """
    Tests for the nested `subcontracting_chain` field on Solution serializers
    (DORA Art. 28(2) data model). Covers:
      - Read serialization exposes the chain (id, subcontractor, recipient).
      - Write: create/update replacing the chain via bulk delete+insert.
      - PATCH empty array → clears; PATCH omitting → leaves untouched.
      - Recipient-based tree structure and fan-out.
    """

    def setUp(self):
        from tprm.models import SolutionSubcontractor

        self.folder = Folder.objects.create(name="Chain Test Folder")
        self.direct = Entity.objects.create(
            name="Direct", folder=self.folder, legal_identifiers={"LEI": "DIRE1"}
        )
        self.sub_a = Entity.objects.create(
            name="Sub A", folder=self.folder, legal_identifiers={"LEI": "SUBA1"}
        )
        self.sub_b = Entity.objects.create(
            name="Sub B", folder=self.folder, legal_identifiers={"LEI": "SUBB1"}
        )
        self.sub_c = Entity.objects.create(
            name="Sub C", folder=self.folder, legal_identifiers={"LEI": "SUBC1"}
        )
        self.solution = Solution.objects.create(
            name="Chain Sol", provider_entity=self.direct
        )
        self.SolutionSubcontractor = SolutionSubcontractor

    def _seed_chain(self):
        """Seed a 2-entry chain for tests that care about existing state."""
        self.SolutionSubcontractor.objects.create(
            solution=self.solution, subcontractor=self.sub_a
        )
        self.SolutionSubcontractor.objects.create(
            solution=self.solution, subcontractor=self.sub_b
        )

    # --- Read path --------------------------------------------------------

    def test_read_serializer_exposes_chain(self):
        self._seed_chain()
        data = SolutionReadSerializer(self.solution).data
        chain = data["subcontracting_chain"]
        self.assertEqual(len(chain), 2)
        # Each row exposes id, subcontractor, recipient — no rank.
        self.assertIn("id", chain[0])
        self.assertIn("subcontractor", chain[0])
        self.assertIn("recipient", chain[0])
        self.assertNotIn("rank", chain[0])
        # Ordered by created_at: sub_a first, sub_b second.
        self.assertEqual(str(chain[0]["subcontractor"]["id"]), str(self.sub_a.id))
        self.assertEqual(str(chain[1]["subcontractor"]["id"]), str(self.sub_b.id))

    def test_read_serializer_empty_chain_renders_empty_list(self):
        data = SolutionReadSerializer(self.solution).data
        self.assertEqual(data["subcontracting_chain"], [])

    # --- Write path: create ----------------------------------------------

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_create_with_chain_persists_rows(self, _):
        payload = {
            "name": "Fresh Sol",
            "provider_entity": self.direct.id,
            "subcontracting_chain": [
                {"subcontractor": self.sub_a.id},
                {"subcontractor": self.sub_b.id},
            ],
        }
        serializer = SolutionWriteSerializer(
            data=payload, context={"request": MagicMock()}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        solution = serializer.save()
        chain = list(solution.subcontracting_chain.all())
        self.assertEqual(len(chain), 2)
        self.assertEqual(
            [r.subcontractor_id for r in chain], [self.sub_a.id, self.sub_b.id]
        )

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_create_without_chain_leaves_chain_empty(self, _):
        payload = {"name": "No-Chain Sol", "provider_entity": self.direct.id}
        serializer = SolutionWriteSerializer(
            data=payload, context={"request": MagicMock()}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        solution = serializer.save()
        self.assertEqual(solution.subcontracting_chain.count(), 0)

    # --- Write path: validation ------------------------------------------

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_chain_rejects_direct_provider(self, _):
        payload = {
            "name": "Loop Sol",
            "provider_entity": self.direct.id,
            "subcontracting_chain": [
                {"subcontractor": self.direct.id},
            ],
        }
        serializer = SolutionWriteSerializer(
            data=payload, context={"request": MagicMock()}
        )
        # validation itself passes (direct check happens in _replace_chain
        # because it needs the bound Solution); .save() raises.
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(ValidationError) as cm:
            serializer.save()
        self.assertIn("subcontracting_chain", cm.exception.detail)

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_chain_rejects_duplicate_subcontractor(self, _):
        payload = {
            "name": "Dup Sol",
            "provider_entity": self.direct.id,
            "subcontracting_chain": [
                {"subcontractor": self.sub_a.id},
                {"subcontractor": self.sub_a.id},
            ],
        }
        serializer = SolutionWriteSerializer(
            data=payload, context={"request": MagicMock()}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("subcontracting_chain", serializer.errors)

    # --- Write path: update (PATCH) --------------------------------------

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_patch_with_empty_array_clears_chain(self, _):
        self._seed_chain()
        self.assertEqual(self.solution.subcontracting_chain.count(), 2)
        serializer = SolutionWriteSerializer(
            instance=self.solution,
            data={"subcontracting_chain": []},
            partial=True,
            context={"request": MagicMock()},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.solution.refresh_from_db()
        self.assertEqual(self.solution.subcontracting_chain.count(), 0)

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_patch_omitting_chain_leaves_unchanged(self, _):
        self._seed_chain()
        serializer = SolutionWriteSerializer(
            instance=self.solution,
            data={"name": "Renamed Only"},
            partial=True,
            context={"request": MagicMock()},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.solution.refresh_from_db()
        self.assertEqual(self.solution.name, "Renamed Only")
        # Chain untouched.
        self.assertEqual(self.solution.subcontracting_chain.count(), 2)

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_patch_replaces_chain_completely(self, _):
        """Write is replace-semantics, not merge — old rows go, new rows come."""
        self._seed_chain()
        serializer = SolutionWriteSerializer(
            instance=self.solution,
            data={
                "subcontracting_chain": [
                    {"subcontractor": self.sub_c.id},
                ]
            },
            partial=True,
            context={"request": MagicMock()},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.solution.refresh_from_db()
        chain = list(self.solution.subcontracting_chain.all())
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0].subcontractor_id, self.sub_c.id)

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_patch_updates_recipient_tree_structure(self, _):
        """Updating recipient on existing rows changes the tree topology."""
        self._seed_chain()  # A (null recipient), B (null recipient)
        # Re-patch: B now subcontracts under A.
        serializer = SolutionWriteSerializer(
            instance=self.solution,
            data={
                "subcontracting_chain": [
                    {"subcontractor": self.sub_a.id, "recipient": None},
                    {
                        "subcontractor": self.sub_b.id,
                        "recipient": self.sub_a.id,
                    },
                ]
            },
            partial=True,
            context={"request": MagicMock()},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        chain = list(self.solution.subcontracting_chain.all())
        self.assertEqual(len(chain), 2)
        row_a = next(r for r in chain if r.subcontractor_id == self.sub_a.id)
        row_b = next(r for r in chain if r.subcontractor_id == self.sub_b.id)
        self.assertIsNone(row_a.recipient_id)
        self.assertEqual(row_b.recipient_id, self.sub_a.id)

    @patch("iam.models.RoleAssignment.is_access_allowed", return_value=True)
    def test_fan_out_persists_via_shared_null_recipient(self, _):
        """Two subcontractors both with recipient=null (both children of direct provider)."""
        payload = {
            "name": "FanOut Sol",
            "provider_entity": self.direct.id,
            "subcontracting_chain": [
                {"subcontractor": self.sub_a.id, "recipient": None},
                {"subcontractor": self.sub_b.id, "recipient": None},
            ],
        }
        serializer = SolutionWriteSerializer(
            data=payload, context={"request": MagicMock()}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        solution = serializer.save()
        chain = list(solution.subcontracting_chain.all())
        self.assertEqual(len(chain), 2)
        self.assertTrue(all(r.recipient_id is None for r in chain))
        sub_ids = {r.subcontractor_id for r in chain}
        self.assertEqual(sub_ids, {self.sub_a.id, self.sub_b.id})
        # Verify read serializer also returns both.
        read_data = SolutionReadSerializer(solution).data
        self.assertEqual(len(read_data["subcontracting_chain"]), 2)


# ===========================================================================
# EntityReadSerializer subcontracts usage fields
# ===========================================================================


class EntitySubcontractsUsageTestCase(TestCase):
    def setUp(self):
        from tprm.models import SolutionSubcontractor

        self.folder = Folder.objects.create(name="Folder")
        self.direct = Entity.objects.create(
            name="Direct", folder=self.folder, legal_identifiers={"LEI": "DIRE1"}
        )
        self.aws = Entity.objects.create(
            name="AWS", folder=self.folder, legal_identifiers={"LEI": "AWSX1"}
        )
        # Two solutions both subcontract to AWS.
        self.sol_a = Solution.objects.create(
            name="Service A", provider_entity=self.direct
        )
        self.sol_b = Solution.objects.create(
            name="Service B", provider_entity=self.direct
        )
        SolutionSubcontractor.objects.create(
            solution=self.sol_a, subcontractor=self.aws
        )
        SolutionSubcontractor.objects.create(
            solution=self.sol_b, subcontractor=self.aws
        )

    def test_subcontracts_count_reflects_usage(self):
        data = EntityReadSerializer(self.aws).data
        self.assertEqual(data["subcontracts_count"], 2)

    def test_subcontracts_usage_lists_blocking_solutions(self):
        data = EntityReadSerializer(self.aws).data
        usage = data["subcontracts_usage"]
        self.assertEqual(len(usage), 2)
        solution_names = sorted(u["solution_name"] for u in usage)
        self.assertEqual(solution_names, ["Service A", "Service B"])
        # No rank field in usage rows.
        for u in usage:
            self.assertNotIn("rank", u)
            self.assertIn("solution_id", u)
            self.assertIn("solution_name", u)

    def test_non_subcontractor_has_zero_count(self):
        other = Entity.objects.create(name="Other", folder=self.folder)
        data = EntityReadSerializer(other).data
        self.assertEqual(data["subcontracts_count"], 0)
        self.assertEqual(data["subcontracts_usage"], [])
