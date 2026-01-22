"""
Migration Utilities for DDD Refactoring

Utilities to help migrate from traditional Django ORM patterns
to DDD patterns (ManyToMany → Embedded ID Arrays, etc.)
"""

from typing import List, Type
from django.db import models, transaction
from django.apps import apps


def migrate_manytomany_to_id_array(
    model_class: Type[models.Model],
    field_name: str,
    related_model_class: Type[models.Model],
    id_array_field_name: str = None
) -> int:
    """
    Migrate a ManyToManyField to an embedded ID array.
    
    Args:
        model_class: The model with the ManyToManyField
        field_name: Name of the ManyToManyField (e.g., "controls")
        related_model_class: The related model class
        id_array_field_name: Name of the new ID array field (defaults to field_name + "Ids")
    
    Returns:
        Number of records migrated
    """
    if id_array_field_name is None:
        id_array_field_name = field_name + "Ids"
    
    many_to_many_field = model_class._meta.get_field(field_name)
    if not isinstance(many_to_many_field, models.ManyToManyField):
        raise ValueError(f"{field_name} is not a ManyToManyField")
    
    migrated_count = 0
    
    with transaction.atomic():
        for instance in model_class.objects.all():
            # Get related IDs
            related_ids = list(
                getattr(instance, field_name).values_list('id', flat=True)
            )
            
            # Set ID array field
            setattr(instance, id_array_field_name, related_ids)
            instance.save(update_fields=[id_array_field_name])
            
            migrated_count += 1
    
    return migrated_count


def migrate_foreignkey_to_id(
    model_class: Type[models.Model],
    field_name: str,
    id_field_name: str = None
) -> int:
    """
    Migrate a ForeignKey to an embedded ID field.
    
    Args:
        model_class: The model with the ForeignKey
        field_name: Name of the ForeignKey (e.g., "parent")
        id_field_name: Name of the new ID field (defaults to field_name + "Id")
    
    Returns:
        Number of records migrated
    """
    if id_field_name is None:
        id_field_name = field_name + "Id"
    
    foreign_key_field = model_class._meta.get_field(field_name)
    if not isinstance(foreign_key_field, models.ForeignKey):
        raise ValueError(f"{field_name} is not a ForeignKey")
    
    migrated_count = 0
    
    with transaction.atomic():
        for instance in model_class.objects.all():
            related_instance = getattr(instance, field_name)
            if related_instance:
                setattr(instance, id_field_name, related_instance.id)
            else:
                setattr(instance, id_field_name, None)
            
            instance.save(update_fields=[id_field_name])
            migrated_count += 1
    
    return migrated_count


def validate_migration(
    model_class: Type[models.Model],
    old_field_name: str,
    new_field_name: str,
    related_model_class: Type[models.Model] = None
) -> dict:
    """
    Validate that a migration was successful.
    
    Args:
        model_class: The model that was migrated
        old_field_name: Name of the old field (ManyToMany or ForeignKey)
        new_field_name: Name of the new field (ID array or ID)
        related_model_class: The related model class (for ManyToMany)
    
    Returns:
        Dictionary with validation results
    """
    results = {
        "total_records": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "errors": []
    }
    
    old_field = model_class._meta.get_field(old_field_name)
    is_many_to_many = isinstance(old_field, models.ManyToManyField)
    
    for instance in model_class.objects.all():
        results["total_records"] += 1
        
        try:
            if is_many_to_many:
                # Get IDs from old ManyToMany
                old_ids = set(
                    getattr(instance, old_field_name).values_list('id', flat=True)
                )
                
                # Get IDs from new array
                new_ids = set(getattr(instance, new_field_name, []))
                
                # Compare
                if old_ids == new_ids:
                    results["valid_records"] += 1
                else:
                    results["invalid_records"] += 1
                    results["errors"].append({
                        "id": instance.id,
                        "old_ids": list(old_ids),
                        "new_ids": list(new_ids)
                    })
            else:
                # ForeignKey case
                old_id = getattr(instance, old_field_name).id if getattr(instance, old_field_name) else None
                new_id = getattr(instance, new_field_name)
                
                if old_id == new_id:
                    results["valid_records"] += 1
                else:
                    results["invalid_records"] += 1
                    results["errors"].append({
                        "id": instance.id,
                        "old_id": old_id,
                        "new_id": new_id
                    })
        except Exception as e:
            results["invalid_records"] += 1
            results["errors"].append({
                "id": instance.id,
                "error": str(e)
            })
    
    return results

