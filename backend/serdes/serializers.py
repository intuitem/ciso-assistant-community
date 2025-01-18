"""
Serializers for handling data import and export operations.

This module provides a set of serializers for managing data backup and restoration,
with support for versioning and field validation. It handles the serialization
of Django model instances to a portable format and back.
"""

import re

from django.utils import timezone
from django.conf import settings
from django.db.models.query import QuerySet
from rest_framework import serializers
from hashlib import sha256

from .utils import app_dot_model, import_export_serializer_class


class LoadBackupSerializer(serializers.Serializer):
    file = serializers.Field

    class Meta:
        fields = ("file",)


class MetaSerializer(serializers.Serializer):
    """
    Serializer for backup metadata information.

    Handles the metadata section of backups, including version information
    and timestamp data.

    Attributes:
        media_version (str): Version of CISO Assistant at the time the backup was created.
        exported_at (str): ISO 8601 format timestamp indicating when the backup was created.
    """

    media_version = serializers.CharField()
    exported_at = serializers.CharField()


class ObjectSerializer(serializers.Serializer):
    """
    Serializer for individual model instances in the backup.

    Handles the serialization of individual model instances, including their
    identifiers and field data. Ensures field names follow the required pattern.

    Attributes:
        model (str): Dotted path string identifying the Django model (e.g., 'app.Model').
        id (str): String representation of the instance's primary key or its backup local identifier.
        fields (dict): Dictionary containing the instance's field values.

    Raises:
        ValidationError: If any field name doesn't match the required pattern of
            lowercase letters and underscores.
    """

    model = serializers.CharField()
    id = serializers.CharField()
    fields = serializers.DictField(
        child=serializers.JSONField(),  # Accept any JSON-serializable value
        allow_empty=True,
    )

    def validate_fields(self, value):
        # Validate that all field names match the pattern ^[a-z_]+$
        pattern = re.compile(r"^[a-z_]+$")

        for field_name in value.keys():
            if not pattern.match(field_name):
                raise serializers.ValidationError(
                    f"Field name '{field_name}' must contain only lowercase letters and underscores"
                )
        return value


class ExportSerializer(serializers.Serializer):
    meta = MetaSerializer()
    objects = ObjectSerializer(many=True)

    @staticmethod
    def dump_data(scope: list[QuerySet]) -> dict:
        """
        Serialize multiple querysets into a complete backup format.

        This method creates a full backup representation including metadata
        and serialized model instances from multiple querysets.

        Args:
            scope (list[QuerySet]): List of querysets to be included in the backup.

        Returns:
            dict: A dictionary containing:
                - meta: Dictionary with version and timestamp information
                - objects: List of serialized model instances

        Example:
            >>> querysets = [User.objects.all(), UserGroup.objects.all()]
            >>> data = ExportSerializer.dump_data(querysets)
            >>> {
            ...     'meta': {
            ...         'media_version': '1.0',
            ...         'exported_at': '2025-01-14T10:00:00Z'
            ...     },
            ...     'objects': [
            ...         {
            ...             'model': 'iam.user',
            ...             'id': '1',
            ...             'fields': {...}
            ...         },
            ...         ...
            ...     ]
            ... }
        """

        meta = {
            "media_version": settings.VERSION,
            "exported_at": timezone.now().isoformat(),
        }

        objects = []

        for queryset in scope:
            for obj in queryset:
                objects.append(
                    {
                        "model": app_dot_model(queryset.model),
                        "id": sha256(str(obj.id).encode()).hexdigest()[:12],
                        "fields": import_export_serializer_class(queryset.model)(
                            obj
                        ).data,
                    }
                )

        return {"meta": meta, "objects": objects}
