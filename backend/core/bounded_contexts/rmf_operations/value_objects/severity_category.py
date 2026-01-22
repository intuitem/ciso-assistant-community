"""
Severity Category Value Object

Represents the severity category (CAT I/II/III) of a vulnerability.
"""

from typing import Optional
from django.core.exceptions import ValidationError

from core.domain.value_object import ValueObject


class SeverityCategory(ValueObject):
    """
    Severity Category value object.

    Represents the severity category of a vulnerability finding
    using the DoD categorization (CAT I/II/III).
    """

    VALID_CATEGORIES = {
        'cat1': {'name': 'CAT I', 'description': 'High', 'weight': 3},
        'cat2': {'name': 'CAT II', 'description': 'Medium', 'weight': 2},
        'cat3': {'name': 'CAT III', 'description': 'Low', 'weight': 1}
    }

    def __init__(self, category: str):
        """
        Initialize severity category.

        Args:
            category: Severity category ('cat1', 'cat2', 'cat3')
        """
        self.category = category.lower()
        self._validate()

    def _validate(self) -> None:
        """Validate the severity category"""
        if self.category not in self.VALID_CATEGORIES:
            raise ValidationError(
                f"Invalid severity category '{self.category}'. "
                f"Must be one of: {list(self.VALID_CATEGORIES.keys())}"
            )

    @property
    def name(self) -> str:
        """Get category name (e.g., 'CAT I')"""
        return self.VALID_CATEGORIES[self.category]['name']

    @property
    def description(self) -> str:
        """Get category description (e.g., 'High')"""
        return self.VALID_CATEGORIES[self.category]['description']

    @property
    def weight(self) -> int:
        """Get category weight for sorting/prioritization"""
        return self.VALID_CATEGORIES[self.category]['weight']

    def is_high(self) -> bool:
        """Check if this is high severity (CAT I)"""
        return self.category == 'cat1'

    def is_medium(self) -> bool:
        """Check if this is medium severity (CAT II)"""
        return self.category == 'cat2'

    def is_low(self) -> bool:
        """Check if this is low severity (CAT III)"""
        return self.category == 'cat3'

    def is_critical(self) -> bool:
        """Check if this represents a critical finding (CAT I)"""
        return self.is_high()

    def __str__(self) -> str:
        return self.name

    def __lt__(self, other) -> bool:
        """Support sorting by severity (higher weight = higher priority)"""
        if isinstance(other, SeverityCategory):
            return self.weight < other.weight
        return NotImplemented

    def __le__(self, other) -> bool:
        if isinstance(other, SeverityCategory):
            return self.weight <= other.weight
        return NotImplemented

    def __gt__(self, other) -> bool:
        if isinstance(other, SeverityCategory):
            return self.weight > other.weight
        return NotImplemented

    def __ge__(self, other) -> bool:
        if isinstance(other, SeverityCategory):
            return self.weight >= other.weight
        return NotImplemented

    @classmethod
    def from_weight(cls, weight: int) -> 'SeverityCategory':
        """Create category from weight"""
        for cat, info in cls.VALID_CATEGORIES.items():
            if info['weight'] == weight:
                return cls(cat)
        raise ValidationError(f"No category found for weight {weight}")

    @classmethod
    def high(cls) -> 'SeverityCategory':
        """Create CAT I (High) category"""
        return cls('cat1')

    @classmethod
    def medium(cls) -> 'SeverityCategory':
        """Create CAT II (Medium) category"""
        return cls('cat2')

    @classmethod
    def low(cls) -> 'SeverityCategory':
        """Create CAT III (Low) category"""
        return cls('cat3')
