"""
Tests for value objects
"""

from dataclasses import dataclass
from django.test import TestCase

from core.domain.value_object import ValueObject, ValueObjectField


@dataclass(frozen=True)
class RiskScoring(ValueObject):
    """Test value object"""
    likelihood: int
    impact: int
    inherent_score: int
    residual_score: int


class ValueObjectTests(TestCase):
    """Tests for ValueObject"""
    
    def test_value_object_equality(self):
        """Test value object equality"""
        scoring1 = RiskScoring(
            likelihood=3,
            impact=4,
            inherent_score=12,
            residual_score=8
        )
        scoring2 = RiskScoring(
            likelihood=3,
            impact=4,
            inherent_score=12,
            residual_score=8
        )
        
        self.assertEqual(scoring1, scoring2)
    
    def test_value_object_inequality(self):
        """Test value object inequality"""
        scoring1 = RiskScoring(
            likelihood=3,
            impact=4,
            inherent_score=12,
            residual_score=8
        )
        scoring2 = RiskScoring(
            likelihood=4,
            impact=4,
            inherent_score=12,
            residual_score=8
        )
        
        self.assertNotEqual(scoring1, scoring2)
    
    def test_value_object_to_dict(self):
        """Test converting value object to dictionary"""
        scoring = RiskScoring(
            likelihood=3,
            impact=4,
            inherent_score=12,
            residual_score=8
        )
        
        data = scoring.to_dict()
        
        self.assertEqual(data["likelihood"], 3)
        self.assertEqual(data["impact"], 4)
        self.assertEqual(data["inherent_score"], 12)
        self.assertEqual(data["residual_score"], 8)
    
    def test_value_object_from_dict(self):
        """Test creating value object from dictionary"""
        data = {
            "likelihood": 3,
            "impact": 4,
            "inherent_score": 12,
            "residual_score": 8
        }
        
        scoring = RiskScoring.from_dict(data)
        
        self.assertEqual(scoring.likelihood, 3)
        self.assertEqual(scoring.impact, 4)
        self.assertEqual(scoring.inherent_score, 12)
        self.assertEqual(scoring.residual_score, 8)
    
    def test_value_object_hashable(self):
        """Test that value objects are hashable"""
        scoring = RiskScoring(
            likelihood=3,
            impact=4,
            inherent_score=12,
            residual_score=8
        )
        
        # Should not raise exception
        hash_value = hash(scoring)
        self.assertIsInstance(hash_value, int)

