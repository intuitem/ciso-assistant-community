"""
Tests for custom DDD fields
"""

import uuid
from django.test import TestCase
from django.db import models
from django.core.exceptions import ValidationError

from core.domain.fields import EmbeddedIdArrayField


class TestModel(models.Model):
    """Test model with embedded ID array"""
    
    controlIds = EmbeddedIdArrayField(
        models.UUIDField(),
        default=list,
        blank=True
    )
    
    class Meta:
        app_label = "core"


class EmbeddedIdArrayFieldTests(TestCase):
    """Tests for EmbeddedIdArrayField"""
    
    def test_field_creation(self):
        """Test creating a field"""
        field = EmbeddedIdArrayField(models.UUIDField())
        self.assertIsNotNone(field)
    
    def test_save_uuid_array(self):
        """Test saving array of UUIDs"""
        model = TestModel()
        model.controlIds = [uuid.uuid4(), uuid.uuid4()]
        model.save()
        
        retrieved = TestModel.objects.get(id=model.id)
        self.assertEqual(len(retrieved.controlIds), 2)
        self.assertIsInstance(retrieved.controlIds[0], uuid.UUID)
    
    def test_validate_uuid_array(self):
        """Test validation of UUID array"""
        field = EmbeddedIdArrayField(models.UUIDField())
        model = TestModel()
        
        # Valid UUIDs
        model.controlIds = [uuid.uuid4(), uuid.uuid4()]
        field.validate(model.controlIds, model)
        
        # Invalid (should raise ValidationError)
        model.controlIds = ["not-a-uuid"]
        with self.assertRaises(ValidationError):
            field.validate(model.controlIds, model)
    
    def test_empty_array(self):
        """Test empty array handling"""
        model = TestModel()
        model.controlIds = []
        model.save()
        
        retrieved = TestModel.objects.get(id=model.id)
        self.assertEqual(retrieved.controlIds, [])

