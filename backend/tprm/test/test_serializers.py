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
        self.assessment.authors.add(self.user)
        self.assessment.reviewers.add(self.user)

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
    def test_entity_assessment_write_serializer_with_audit(
        self,
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

    @patch(
        "tprm.serializers.EntityAssessmentWriteSerializer._assign_third_party_respondents"
    )
    def test_entity_assessment_write_update(self, mock_assign):
        """Test that EntityAssessmentWriteSerializer correctly updates an EntityAssessment"""
        new_rep = User.objects.create_user(
            email="newrep@example.com", password="password"
        )

        data = {"name": "Updated Assessment", "representatives": [new_rep.id]}

        serializer = EntityAssessmentWriteSerializer(
            self.assessment, data=data, partial=True
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
    def test_representative_write_serializer_existing_user(
        self, mock_filter, mock_is_access_allowed
    ):
        """Test that RepresentativeWriteSerializer correctly associates an existing user with a Representative"""
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
