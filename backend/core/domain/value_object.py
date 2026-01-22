"""
Value Object Base Class

Value objects are immutable objects that are defined by their attributes
rather than their identity.
"""

from typing import Any, Dict
from dataclasses import dataclass, field
from django.db import models


@dataclass(frozen=True)
class ValueObject:
    """
    Base class for value objects.
    
    Value objects:
    - Are immutable (frozen dataclass)
    - Are compared by value, not identity
    - Have no identity of their own
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert value object to dictionary"""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create value object from dictionary"""
        return cls(**data)
    
    def __eq__(self, other):
        """Value objects are equal if all fields are equal"""
        if not isinstance(other, self.__class__):
            return False
        return self.to_dict() == other.to_dict()
    
    def __hash__(self):
        """Value objects are hashable"""
        return hash(tuple(sorted(self.to_dict().items())))


class ValueObjectField(models.JSONField):
    """
    Django field for storing value objects as JSON.
    
    Usage:
        class MyModel(models.Model):
            scoring = ValueObjectField(RiskScoring)
    """
    
    def __init__(self, value_object_class, *args, **kwargs):
        self.value_object_class = value_object_class
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        """Convert database value to value object"""
        if value is None:
            return None
        if isinstance(value, self.value_object_class):
            return value
        return self.value_object_class.from_dict(value)
    
    def to_python(self, value):
        """Convert Python value to value object"""
        if value is None:
            return None
        if isinstance(value, self.value_object_class):
            return value
        if isinstance(value, dict):
            return self.value_object_class.from_dict(value)
        return value
    
    def get_prep_value(self, value):
        """Convert value object to database value"""
        if value is None:
            return None
        if isinstance(value, self.value_object_class):
            return value.to_dict()
        return value

