from hashlib import sha256
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


class IdRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Related field that only exposes the primary key.

    Accepts legacy FieldsRelatedField arguments (fields, serializer, positional fields)
    and ignores them to keep call sites compatible.
    """

    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], (list, dict)):
            args = args[1:]
        kwargs.pop("fields", None)
        kwargs.pop("serializer", None)
        kwargs.setdefault("read_only", True)
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        if value is None:
            return None
        if isinstance(value, dict):
            return value.get("id", value.get("pk"))
        return super().to_representation(value)


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
