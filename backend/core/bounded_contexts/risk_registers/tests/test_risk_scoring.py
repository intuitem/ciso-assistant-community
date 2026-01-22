"""
Tests for RiskScoring value object
"""

from django.test import TestCase

from core.bounded_contexts.risk_registers.value_objects.risk_scoring import RiskScoring


class RiskScoringTests(TestCase):
    """Tests for RiskScoring value object"""
    
    def test_create_risk_scoring(self):
        """Test creating a risk scoring"""
        scoring = RiskScoring(
            likelihood=4,
            impact=5,
            inherent_score=20,
            residual_score=10,
            rationale="High likelihood, critical impact"
        )
        
        self.assertEqual(scoring.likelihood, 4)
        self.assertEqual(scoring.impact, 5)
        self.assertEqual(scoring.inherent_score, 20)
        self.assertEqual(scoring.residual_score, 10)
        self.assertEqual(scoring.rationale, "High likelihood, critical impact")
    
    def test_invalid_likelihood(self):
        """Test that invalid likelihood raises error"""
        with self.assertRaises(ValueError):
            RiskScoring(
                likelihood=6,  # Invalid: must be 1-5
                impact=3,
                inherent_score=18,
                residual_score=9
            )
    
    def test_invalid_impact(self):
        """Test that invalid impact raises error"""
        with self.assertRaises(ValueError):
            RiskScoring(
                likelihood=3,
                impact=0,  # Invalid: must be 1-5
                inherent_score=15,
                residual_score=8
            )
    
    def test_calculate_inherent_score(self):
        """Test calculating inherent score"""
        scoring = RiskScoring(
            likelihood=3,
            impact=4,
            inherent_score=12,
            residual_score=8
        )
        
        calculated = scoring.calculate_inherent_score()
        self.assertEqual(calculated, 12)  # 3 * 4 = 12
    
    def test_equality(self):
        """Test that equal risk scorings are equal"""
        scoring1 = RiskScoring(3, 4, 12, 8, "Test")
        scoring2 = RiskScoring(3, 4, 12, 8, "Test")
        
        self.assertEqual(scoring1, scoring2)
    
    def test_inequality(self):
        """Test that different risk scorings are not equal"""
        scoring1 = RiskScoring(3, 4, 12, 8)
        scoring2 = RiskScoring(4, 4, 16, 10)
        
        self.assertNotEqual(scoring1, scoring2)

