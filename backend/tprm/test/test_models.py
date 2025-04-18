from django.test import TestCase
from unittest.mock import patch, MagicMock

from tprm.models import Entity, EntityAssessment, Representative, Solution
from iam.models import Folder
from core.models import Asset


class TestEntity(TestCase):
    def setUp(self):
        """Initial setup for testing on Entity."""
        self.root_folder = Folder.objects.create(name="Root Folder")
        self.entity_folder = Folder.objects.create(name="Entity Folder", parent_folder=self.root_folder)

    def test_entity_creation(self):
        """Testing the creation of an entity."""
        entity = Entity.objects.create(
            name="Test Entity",
            description="Test description",
            mission="Test mission",
            reference_link="https://example.com",
            folder=self.entity_folder
        )
        
        self.assertEqual(entity.name, "Test Entity")
        self.assertEqual(entity.description, "Test description")
        self.assertEqual(entity.mission, "Test mission")
        self.assertEqual(entity.reference_link, "https://example.com")
        self.assertEqual(entity.folder, self.entity_folder)
        self.assertFalse(entity.builtin)
        
    @patch('tprm.models.Folder')
    @patch('tprm.models.Entity.owned_folders')
    def test_get_main_entity(self, mock_owned_folders, mock_folder_class):
        """Testing the get_main_entity method."""
        mock_root_folder = MagicMock()
        mock_folder_class.get_root_folder.return_value = mock_root_folder
        
        entity = Entity.objects.create(
            name="Main Entity",
            builtin=True,
            folder=self.entity_folder
        )
        
        with patch('tprm.models.Entity.objects') as mock_objects:
            mock_filter = MagicMock()
            mock_filter2 = MagicMock()
            mock_order_by = MagicMock()
            
            mock_objects.filter.return_value = mock_filter
            mock_filter.filter.return_value = mock_filter2
            mock_filter2.order_by.return_value = mock_order_by
            mock_order_by.first.return_value = entity
            
            result = Entity.get_main_entity()
            
            mock_objects.filter.assert_called_once_with(builtin=True)
            mock_filter.filter.assert_called_once()
            mock_filter2.order_by.assert_called_once_with("created_at")
            mock_order_by.first.assert_called_once()
            
            self.assertEqual(result, entity)


class TestEntityAssessment(TestCase):
    def setUp(self):
        """Initial setup for testing on EntityAssessment."""
        self.folder = Folder.objects.create(name="Test Folder")
        self.entity = Entity.objects.create(
            name="Test Entity",
            folder=self.folder
        )
        
    def test_entity_assessment_creation(self):
        """Testing the creation of an entity assessment."""
        assessment = EntityAssessment.objects.create(
            name="Test Assessment",
            description="Test description",
            status=EntityAssessment.Status.PLANNED,
            criticality=3,
            penetration=2,
            dependency=4,
            maturity=3,
            trust=3,
            entity=self.entity,
            folder=self.folder,
            perimeter=None, # Assuming perimeter is not used in this test
            conclusion=EntityAssessment.Conclusion.WARNING
        )
        
        self.assertEqual(assessment.name, "Test Assessment")
        self.assertEqual(assessment.description, "Test description")
        self.assertEqual(assessment.status, EntityAssessment.Status.PLANNED)
        self.assertEqual(assessment.criticality, 3)
        self.assertEqual(assessment.penetration, 2)
        self.assertEqual(assessment.dependency, 4)
        self.assertEqual(assessment.maturity, 3)
        self.assertEqual(assessment.trust, 3)
        self.assertEqual(assessment.entity, self.entity)
        self.assertEqual(assessment.conclusion, EntityAssessment.Conclusion.WARNING)


class TestRepresentative(TestCase):
    def setUp(self):
        """Initial setup for testing on Representative."""
        self.folder = Folder.objects.create(name="Test Folder")
        self.entity = Entity.objects.create(
            name="Test Entity",
            folder=self.folder
        )
        
    def test_representative_creation(self):
        """Testing the creation of a representative."""
        representative = Representative.objects.create(
            entity=self.entity,
            email="test@example.com",
            first_name="Patrick",
            last_name="Sebastien",
            phone="123456789",
            role="Manager",
            description="Test representative"
        )
        
        self.assertEqual(representative.entity, self.entity)
        self.assertEqual(representative.email, "test@example.com")
        self.assertEqual(representative.first_name, "Patrick")
        self.assertEqual(representative.last_name, "Sebastien")
        self.assertEqual(representative.phone, "123456789")
        self.assertEqual(representative.role, "Manager")
        self.assertEqual(representative.description, "Test representative")
        self.assertIsNone(representative.user)


class TestSolution(TestCase):
    def setUp(self):
        """Initial setup for testing on Solution."""
        self.folder = Folder.objects.create(name="Test Folder")
        self.provider_entity = Entity.objects.create(
            name="Provider Entity",
            folder=self.folder
        )
        self.recipient_entity = Entity.objects.create(
            name="Recipient Entity",
            folder=self.folder
        )
        self.asset = Asset.objects.create(
            name="Test Asset"
        )
        
    def test_solution_creation(self):
        """Testing the creation of a solution."""
        solution = Solution.objects.create(
            name="Test Solution",
            description="Test description",
            provider_entity=self.provider_entity,
            recipient_entity=self.recipient_entity,
            ref_id="SOL-001",
            criticality=4
        )
        solution.assets.add(self.asset)
        
        self.assertEqual(solution.name, "Test Solution")
        self.assertEqual(solution.description, "Test description")
        self.assertEqual(solution.provider_entity, self.provider_entity)
        self.assertEqual(solution.recipient_entity, self.recipient_entity)
        self.assertEqual(solution.ref_id, "SOL-001")
        self.assertEqual(solution.criticality, 4)
        self.assertEqual(solution.assets.count(), 1)
        self.assertEqual(solution.assets.first(), self.asset)