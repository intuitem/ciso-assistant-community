"""CRUD serializers for FieldDefinition/FieldChoice + host-side `custom_fields` mixin."""

from typing import Any

from django.db import transaction
from rest_framework import serializers

from custom_fields.models import (
    FieldChoice,
    FieldDefinition,
    FieldValue,
)


class FieldChoiceReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldChoice
        fields = [
            "id",
            "value",
            "label",
            "translations",
            "color",
            "order",
            "is_visible",
        ]


class FieldChoiceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldChoice
        fields = [
            "id",
            "definition",
            "value",
            "label",
            "translations",
            "color",
            "order",
            "is_visible",
        ]


class FieldDefinitionReadSerializer(serializers.ModelSerializer):
    target_content_type = serializers.SlugRelatedField(
        read_only=True, slug_field="model"
    )
    choices = FieldChoiceReadSerializer(many=True, read_only=True)

    class Meta:
        model = FieldDefinition
        fields = [
            "id",
            "target_content_type",
            "name",
            "label",
            "translations",
            "description",
            "type",
            "required",
            "default",
            "order",
            "is_visible",
            "filterable",
            "builtin",
            "choices",
            "created_at",
            "updated_at",
        ]


class FieldDefinitionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldDefinition
        fields = [
            "id",
            "target_content_type",
            "name",
            "label",
            "translations",
            "description",
            "type",
            "required",
            "default",
            "order",
            "is_visible",
            "filterable",
        ]

    def validate_name(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("Required.")
        if not all(c.isascii() and (c.isalnum() or c == "_") for c in value):
            raise serializers.ValidationError(
                "Use lowercase ASCII letters, digits, and underscores only."
            )
        return value.lower()

    def update(
        self, instance: FieldDefinition, validated_data: dict
    ) -> FieldDefinition:
        # target_content_type is the anchor for existing FieldValue rows; mutating
        # it would orphan them. Silently ignore on update.
        validated_data.pop("target_content_type", None)
        return super().update(instance, validated_data)


# Sentinel for PATCH semantics: "field omitted" vs "field explicitly null".
_UNSET = object()


class CustomFieldsSerializerMixin:
    """Adds a `custom_fields` dict to a host serializer.
    Read: {name: resolved_value}. Write: same shape; `null` clears all.
    Mix in BEFORE the base serializer so create/update overrides win."""

    def get_fields(self):  # type: ignore[no-untyped-def]
        fields = super().get_fields()  # type: ignore[misc]
        fields["custom_fields"] = serializers.JSONField(required=False, allow_null=True)
        return fields

    @transaction.atomic
    def create(self, validated_data):  # type: ignore[no-untyped-def]
        custom = validated_data.pop("custom_fields", _UNSET)
        instance = super().create(validated_data)  # type: ignore[misc]
        if custom is not _UNSET:
            self._apply_custom_fields(instance, custom or {})
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):  # type: ignore[no-untyped-def]
        custom = validated_data.pop("custom_fields", _UNSET)
        instance = super().update(instance, validated_data)  # type: ignore[misc]
        if custom is _UNSET:
            return instance
        if custom is None:
            self._clear_all_custom_fields(instance)
        else:
            self._apply_custom_fields(instance, custom)
        return instance

    def _apply_custom_fields(self, instance, custom: dict[str, Any]) -> None:
        from core.models import Actor

        if not isinstance(custom, dict):
            raise serializers.ValidationError({"custom_fields": "Must be an object."})
        errors: dict[str, str] = {}
        for name, value in custom.items():
            try:
                instance.set_custom_field(name, value)
            except (ValueError, FieldValue.DoesNotExist) as exc:
                errors[name] = str(exc)
            except FieldChoice.DoesNotExist as exc:
                errors[name] = str(exc) or f"Unknown choice for field {name!r}."
            except Actor.DoesNotExist:
                errors[name] = f"Unknown actor for field {name!r}."
        if errors:
            raise serializers.ValidationError({"custom_fields": errors})

    def _clear_all_custom_fields(self, instance) -> None:
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(type(instance))
        FieldValue.objects.filter(content_type=ct, object_id=instance.pk).delete()
        if hasattr(instance, "_invalidate_custom_fields_cache"):
            instance._invalidate_custom_fields_cache()
