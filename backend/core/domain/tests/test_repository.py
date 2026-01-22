"""
Tests for repository pattern
"""

import uuid
from django.test import TestCase
from django.db import models

from core.domain.aggregate import AggregateRoot
from core.domain.repository import Repository


class TestAggregate(AggregateRoot):
    """Test aggregate root"""
    
    name = models.CharField(max_length=255)
    
    class Meta:
        app_label = "core"


class RepositoryTests(TestCase):
    """Tests for Repository"""
    
    def setUp(self):
        self.repository = Repository(TestAggregate)
    
    def test_get_by_id(self):
        """Test getting aggregate by ID"""
        aggregate = TestAggregate(name="Test")
        aggregate.save()
        
        retrieved = self.repository.get_by_id(aggregate.id)
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, aggregate.id)
        self.assertEqual(retrieved.name, "Test")
    
    def test_get_by_id_not_found(self):
        """Test getting non-existent aggregate"""
        non_existent_id = uuid.uuid4()
        result = self.repository.get_by_id(non_existent_id)
        
        self.assertIsNone(result)
    
    def test_get_all(self):
        """Test getting all aggregates"""
        TestAggregate(name="Test1").save()
        TestAggregate(name="Test2").save()
        
        all_aggregates = self.repository.get_all()
        
        self.assertGreaterEqual(len(all_aggregates), 2)
        names = [a.name for a in all_aggregates]
        self.assertIn("Test1", names)
        self.assertIn("Test2", names)
    
    def test_save_aggregate(self):
        """Test saving aggregate"""
        aggregate = TestAggregate(name="Test")
        
        saved = self.repository.save(aggregate)
        
        self.assertIsNotNone(saved.id)
        self.assertTrue(self.repository.exists(saved.id))
    
    def test_delete_aggregate(self):
        """Test deleting aggregate"""
        aggregate = TestAggregate(name="Test")
        aggregate.save()
        
        self.repository.delete(aggregate)
        
        self.assertFalse(self.repository.exists(aggregate.id))
    
    def test_exists(self):
        """Test checking if aggregate exists"""
        aggregate = TestAggregate(name="Test")
        aggregate.save()
        
        self.assertTrue(self.repository.exists(aggregate.id))
        
        non_existent_id = uuid.uuid4()
        self.assertFalse(self.repository.exists(non_existent_id))
    
    def test_count(self):
        """Test counting aggregates"""
        initial_count = self.repository.count()
        
        TestAggregate(name="Test1").save()
        TestAggregate(name="Test2").save()
        
        self.assertEqual(self.repository.count(), initial_count + 2)

