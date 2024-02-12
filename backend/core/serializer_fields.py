from typing import Any
from django.db import models
from rest_framework import serializers

from iam.models import Folder


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

        if value == Folder.get_root_folder():
            return res

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
