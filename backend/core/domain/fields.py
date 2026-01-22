"""
Custom Django Fields for DDD Patterns

Provides fields for embedded ID arrays and other DDD patterns.
"""

import uuid
from typing import List, Optional
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import ArrayField


class EmbeddedIdArrayField(ArrayField):
    """
    Field for storing arrays of UUIDs (embedded ID arrays).
    
    This replaces ManyToMany relationships with embedded arrays
    for aggregate-centric modeling.
    
    Usage:
        class Asset(AggregateRoot):
            controlIds = EmbeddedIdArrayField(
                models.UUIDField(),
                default=list,
                blank=True,
                help_text="Array of control IDs"
            )
    """
    
    def __init__(self, *args, **kwargs):
        # Default to UUID field if not specified
        if not args:
            args = (models.UUIDField(),)
        
        # Set defaults
        kwargs.setdefault('default', list)
        kwargs.setdefault('blank', True)
        
        super().__init__(*args, **kwargs)
    
    def validate(self, value, model_instance):
        """Validate that all values are UUIDs"""
        super().validate(value, model_instance)
        
        if value is not None:
            for item in value:
                if not isinstance(item, uuid.UUID):
                    try:
                        uuid.UUID(str(item))
                    except (ValueError, TypeError):
                        raise ValidationError(
                            f"All items in {self.name} must be valid UUIDs"
                        )
    
    def deconstruct(self):
        """Deconstruct for migrations"""
        name, path, args, kwargs = super().deconstruct()
        # Remove default from kwargs if it's list (will be added back)
        if kwargs.get('default') == list:
            kwargs.pop('default', None)
        return name, path, args, kwargs

