import pytest
from django.test import TestCase
from unittest.mock import patch, MagicMock, ANY
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from tprm.models import Entity, EntityAssessment, Representative, Solution
from tprm.serializers import (
    EntityReadSerializer, EntityWriteSerializer,
    EntityAssessmentReadSerializer, EntityAssessmentWriteSerializer,
    RepresentativeReadSerializer, RepresentativeWriteSerializer,
    SolutionReadSerializer, SolutionWriteSerializer
)
from iam.models import Folder, Role, RoleAssignment, UserGroup
from core.models import Framework, ComplianceAssessment

User = get_user_model()


class TestEntitySerializers(TestCase):
    def setUp(self):
        """Configuration initiale pour les tests de sérialiseurs d'entité."""
        self.folder = Folder.objects.create(name="Test Folder")
        self.entity_data = {
            "name": "Test Entity",
            "description": "Test description",
            "mission": "Test mission",
            "reference_link": "https://example.com",
            "folder": self.folder.id,
            "is_published": True
        }
        self.entity = Entity.objects.create(
            name="Existing Entity",
            folder=self.folder
        )
        
    def test_entity_read_serializer(self):
        """Test du sérialiseur de lecture d'entité."""
        serializer = EntityReadSerializer(self.entity)
        data = serializer.data
        
        self.assertEqual(data["name"], "Existing Entity")
        self.assertIn("folder", data)
        self.assertIn("owned_folders", data)
        
    def test_entity_write_serializer_create(self):
        """Test du sérialiseur d'écriture d'entité pour la création."""
        serializer = EntityWriteSerializer(data=self.entity_data)
        self.assertTrue(serializer.is_valid())
        
        entity = serializer.save()
        self.assertEqual(entity.name, "Test Entity")
        self.assertEqual(entity.description, "Test description")
        self.assertEqual(entity.mission, "Test mission")
        self.assertEqual(entity.reference_link, "https://example.com")
        self.assertEqual(entity.folder, self.folder)
        self.assertTrue(entity.is_published)
        
    def test_entity_write_serializer_update(self):
        """Test du sérialiseur d'écriture d'entité pour la mise à jour."""
        serializer = EntityWriteSerializer(self.entity, data={
            "name": "Updated Entity",
            "folder": self.folder.id,
            "is_published": True
        })
        
        self.assertTrue(serializer.is_valid())
        updated_entity = serializer.save()
        
        self.assertEqual(updated_entity.name, "Updated Entity")


class TestEntityAssessmentSerializers(TestCase):
    def setUp(self):
        """Configuration initiale pour les tests de sérialiseurs d'évaluation d'entité."""
        self.folder = Folder.objects.create(name="Test Folder")
        self.entity = Entity.objects.create(
            name="Test Entity",
            folder=self.folder
        )
        self.perimeter = MagicMock()
        self.perimeter.name = "Test Perimeter"
        self.perimeter.id = "perimeter-id"
        
        self.framework = Framework.objects.create(name="Test Framework")
        
        self.assessment_data = {
            "name": "Test Assessment",
            "description": "Test description",
            "status": EntityAssessment.Status.PLANNED,
            "criticality": 3,
            "entity": self.entity.id,
            "folder": self.folder.id,
            "perimeter": self.perimeter.id,
            "create_audit": True,
            "framework": self.framework.id,
            "selected_implementation_groups": ["IG1", "IG2"]
        }
        
        self.assessment = EntityAssessment.objects.create(
            name="Existing Assessment",
            entity=self.entity,
            folder=self.folder,
            perimeter=self.perimeter
        )
        
    @patch('tprm.serializers.ComplianceAssessment')
    @patch('tprm.serializers.Folder')
    @patch('tprm.serializers.RoleAssignment')
    def test_entity_assessment_write_serializer_create(self, mock_role_assignment, mock_folder, mock_compliance_assessment):
        """Test du sérialiseur d'écriture d'évaluation d'entité pour la création avec audit."""
        # Mock pour la création du dossier enclave
        mock_enclave = MagicMock()
        mock_folder.objects.create.return_value = mock_enclave
        
        # Mock pour l'évaluation de conformité
        mock_audit = MagicMock()
        mock_compliance_assessment.objects.create.return_value = mock_audit
        
        serializer = EntityAssessmentWriteSerializer(data=self.assessment_data)
        self.assertTrue(serializer.is_valid())
        
        with patch.object(serializer, '_assign_third_party_respondents') as mock_assign:
            assessment = serializer.save()
            mock_assign.assert_called_once()
        
        # Vérifier que l'audit a été créé
        mock_compliance_assessment.objects.create.assert_called_once_with(
            name="Test Assessment",
            framework=self.framework,
            perimeter=self.perimeter,
            selected_implementation_groups=["IG1", "IG2"]
        )
        
        # Vérifier que le dossier a été créé
        mock_folder.objects.create.assert_called_once_with(
            content_type=mock_folder.ContentType.ENCLAVE,
            name=f"{self.perimeter.name}/{assessment.name}",
            parent_folder=self.folder
        )
        
        self.assertEqual(assessment.name, "Test Assessment")
        self.assertEqual(assessment.compliance_assessment, mock_audit)
        
    def test_entity_assessment_write_serializer_create_no_audit(self):
        """Test du sérialiseur d'écriture d'évaluation d'entité sans création d'audit."""
        data = self.assessment_data.copy()
        data["create_audit"] = False
        
        serializer = EntityAssessmentWriteSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        with patch.object(serializer, '_assign_third_party_respondents'):
            assessment = serializer.save()
        
        self.assertEqual(assessment.name, "Test Assessment")
        self.assertIsNone(assessment.compliance_assessment)
        
    def test_entity_assessment_write_serializer_create_invalid_audit(self):
        """Test du sérialiseur avec création d'audit mais sans framework."""
        data = self.assessment_data.copy()
        data.pop("framework")
        
        serializer = EntityAssessmentWriteSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        with self.assertRaises(ValidationError):
            with patch.object(serializer, '_assign_third_party_respondents'):
                serializer.save()


class TestRepresentativeSerializers(TestCase):
    def setUp(self):
        """Configuration initiale pour les tests de sérialiseurs de représentant."""
        self.folder = Folder.objects.create(name="Test Folder")
        self.entity = Entity.objects.create(
            name="Test Entity",
            folder=self.folder
        )
        
        self.representative_data = {
            "entity": self.entity.id,
            "email": "test@example.com",
            "first_name": "Patrick",
            "last_name": "Bruel",
            "phone": "123456789",
            "role": "Manager",
            "description": "Test representative",
            "create_user": True,
            "is_published": True
        }
        
        self.representative = Representative.objects.create(
            entity=self.entity,
            email="existing@example.com",
            first_name="Existing",
            last_name="User"
        )
        
    @patch('tprm.serializers.User.objects.create_user')
    def test_representative_write_serializer_create_with_user(self, mock_create_user):
        """Test du sérialiseur d'écriture de représentant avec création d'utilisateur."""
        mock_user = MagicMock()
        mock_create_user.return_value = mock_user
        
        serializer = RepresentativeWriteSerializer(data=self.representative_data)
        self.assertTrue(serializer.is_valid())
        
        representative = serializer.save()
        
        # Vérifier que l'utilisateur a été créé
        mock_create_user.assert_called_once_with(
            email="test@example.com",
            first_name="Patrick",
            last_name="Bruel"
        )
        
        self.assertEqual(representative.email, "test@example.com")
        self.assertEqual(representative.user, mock_user)
        self.assertTrue(mock_user.is_third_party)
        
    @patch('tprm.serializers.User.objects.create_user')
    @patch('tprm.serializers.User.objects.filter')
    def test_representative_write_serializer_existing_user(self, mock_filter, mock_create_user):
        """Test du sérialiseur avec un utilisateur existant."""
        mock_user = MagicMock()
        mock_filter.return_value.first.return_value = mock_user
        
        serializer = RepresentativeWriteSerializer(data=self.representative_data)
        self.assertTrue(serializer.is_valid())
        
        representative = serializer.save()
        
        # Vérifier que l'utilisateur n'a pas été créé mais récupéré
        mock_create_user.assert_not_called()
        mock_filter.assert_called_with(email="test@example.com")
        
        self.assertEqual(representative.user, mock_user)
        self.assertTrue(mock_user.is_third_party)
        

class TestSolutionSerializers(TestCase):
    def setUp(self):
        """Configuration initiale pour les tests de sérialiseurs de solution."""
        self.folder = Folder.objects.create(name="Test Folder")
        self.provider_entity = Entity.objects.create(
            name="Provider Entity",
            folder=self.folder
        )
        self.recipient_entity = Entity.objects.create(
            name="Recipient Entity",
            folder=self.folder
        )
        
        self.solution_data = {
            "name": "Test Solution",
            "description": "Test description",
            "provider_entity": self.provider_entity.id,
            "ref_id": "SOL-001",
            "criticality": 4,
            "is_published": True
        }
        
        self.solution = Solution.objects.create(
            name="Existing Solution",
            provider_entity=self.provider_entity,
            recipient_entity=self.recipient_entity
        )
        
    def test_solution_read_serializer(self):
        """Test du sérialiseur de lecture de solution."""
        serializer = SolutionReadSerializer(self.solution)
        data = serializer.data
        
        self.assertEqual(data["name"], "Existing Solution")
        self.assertIn("provider_entity", data)
        self.assertIn("recipient_entity", data)
        
    def test_solution_write_serializer_create(self):
        """Test du sérialiseur d'écriture de solution pour la création."""
        serializer = SolutionWriteSerializer(data=self.solution_data)
        self.assertTrue(serializer.is_valid())
        
        solution = serializer.save()
        self.assertEqual(solution.name, "Test Solution")
        self.assertEqual(solution.description, "Test description")
        self.assertEqual(solution.provider_entity, self.provider_entity)
        self.assertEqual(solution.ref_id, "SOL-001")
        self.assertEqual(solution.criticality, 4)