from hashlib import sha256
from typing import Any

from django.db import models
from rest_framework import serializers

from structlog import get_logger

logger = get_logger(__name__)


class HashSlugRelatedField(serializers.SlugRelatedField):
    """
    A custom SlugRelatedField that hashes the slug value during serialization.
    """

    def to_representation(self, obj):
        # Get the original slug value
        value = super().to_representation(obj)
        if value is None:
            return None
        # Hash the value
        return sha256(str(value).encode()).hexdigest()[:12]


class FieldsRelatedField(serializers.RelatedField):
    """
    Serializer relational field that represents the target of the relationship by a
    specific set of fields.

    args:
    fields: list of fields to be serialized
    """

    fields = []

    def __init__(self, fields: list[str | dict[str, list[str]]] = ["id"], **kwargs):
        kwargs["read_only"] = True
        self.fields = fields
        super().__init__(**kwargs)

    def to_representation(
        self, value, fields: list[str | dict[str, list[str]]] | None = None
    ) -> dict[str, Any]:
        res = {"str": str(value)}

        fields = fields or self.fields

        field_data: dict[str, Any] = {
            field_name: self._process_field(value, field_name, sub_fields)
            for field_name, sub_fields in self._normalize_fields(fields)
        }

        res.update(field_data)
        return res

    def _normalize_fields(self, fields: list[str | dict[str, list[str]]]):
        for field in fields:
            if isinstance(field, dict):
                field_name, sub_fields = next(iter(field.items()))
                yield field_name, sub_fields
            elif isinstance(field, str):
                yield field, None
            else:
                # Handle other unexpected field types appropriately
                pass

    def _process_field(
        self,
        value,
        field_name: str,
        sub_fields: list[str] | None,
    ):
        if sub_fields is None:
            field_value = getattr(value, field_name, None)
            if isinstance(field_value, models.Model):
                return self.to_representation(field_value, ["id"])
            return field_value

        if isinstance(sub_fields, list):
            nested_value = getattr(value, field_name, None)
            if nested_value and isinstance(nested_value, models.Model):
                return self.to_representation(nested_value, fields=sub_fields)
            return None  # or some other default value as appropriate


class PathField(serializers.SerializerMethodField):
    """
    A custom serializer field to represent a path from a list of objects.

    This field takes a list of objects (e.g., folders) and
    serializes them into a list of dictionaries, each containing the
    object's ID and its string representation.

    > [!IMPORTANT]
    > This subclasses serializers.SerializerMethodField, therefore
    > there MUST be a method on the serializer class with the name 'get_<field_name>'
    """

    def to_representation(self, value):
        """
        Calls the serializer method (get_<field_name>) and normalizes the result
        to a list of {"id": ..., "str": ...} dicts. Accepts either:
        - an iterable of model instances, or
        - an iterable of dicts containing {"id", "str"} or {"id", "name"}.
        """
        if not self.method_name:
            logger.error("PathField requires a method_name")
            return []
        # Delegate to the serializer's method (DRF pattern for SerializerMethodField)
        method = getattr(self.parent, self.method_name)
        data = method(value)  # value is the object instance
        if not data:
            return []
        # Guard: ignore strings/bytes and mappings as top-level containers
        from collections.abc import Iterable, Mapping

        if (
            isinstance(data, (str, bytes))
            or isinstance(data, Mapping)
            or not isinstance(data, Iterable)
        ):
            return []
        out = []
        for item in data:
            if isinstance(item, models.Model):
                out.append({"id": getattr(item, "id", None), "str": str(item)})
            elif isinstance(item, dict):
                _id = item.get("id")
                _str = item.get("str", item.get("name", str(item)))
                out.append({"id": _id, "str": _str})
            else:
                out.append({"id": getattr(item, "id", None), "str": str(item)})
        return out
