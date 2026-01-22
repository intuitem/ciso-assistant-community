"""
RiskScoring Value Object

Immutable value object representing risk scoring.
"""

from typing import Optional
from core.domain.value_object import ValueObject


class RiskScoring(ValueObject):
    """
    Risk scoring value object.
    
    Immutable value object representing likelihood, impact, and scores.
    """
    
    def __init__(self, likelihood: int, impact: int, inherent_score: int,
                 residual_score: int, rationale: Optional[str] = None):
        """
        Initialize risk scoring.
        
        Args:
            likelihood: Likelihood rating (1-5)
            impact: Impact rating (1-5)
            inherent_score: Inherent risk score
            residual_score: Residual risk score
            rationale: Optional rationale for the scoring
        """
        if not (1 <= likelihood <= 5):
            raise ValueError("Likelihood must be between 1 and 5")
        if not (1 <= impact <= 5):
            raise ValueError("Impact must be between 1 and 5")
        
        self.likelihood = likelihood
        self.impact = impact
        self.inherent_score = inherent_score
        self.residual_score = residual_score
        self.rationale = rationale
    
    def calculate_inherent_score(self) -> int:
        """Calculate inherent score from likelihood and impact"""
        # Simple multiplication, can be customized based on risk matrix
        return self.likelihood * self.impact
    
    def __repr__(self):
        return (
            f"RiskScoring(likelihood={self.likelihood}, impact={self.impact}, "
            f"inherent_score={self.inherent_score}, residual_score={self.residual_score})"
        )

