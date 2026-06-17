from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from core.serializer_fields import FieldsRelatedField
from core.serializers import BaseModelSerializer
from iam.models import Folder

from .models import (
    CustomFieldChoice,
    CustomFieldDefinition,
    FieldType,
    coerce_value,
)


def _resolve_content_type(model: str) -> ContentType:
    """Resolve an 'app_label.model' string to a ContentType."""
    try:
        app_label, model_name = model.lower().split(".")
        return ContentType.objects.get(app_label=app_label, model=model_name)
    except ValueError, ContentType.DoesNotExist:
        raise serializers.ValidationError(
            {"model": f"'{model}' is not a valid app_label.model"}
        )


class CustomFieldChoiceSerializer(serializers.ModelSerializer):
    """Choices are read and written nested under their definition."""

    label_localized = serializers.CharField(read_only=True)

    class Meta:
        model = CustomFieldChoice
        fields = ["id", "value", "label", "label_localized", "translations", "order"]
        read_only_fields = ["id"]


class CustomFieldDefinitionReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    choices = CustomFieldChoiceSerializer(many=True, read_only=True)
    model = serializers.SerializerMethodField()
    label_localized = serializers.CharField(read_only=True)
    help_text_localized = serializers.CharField(read_only=True)

    class Meta:
        model = CustomFieldDefinition
        exclude = ["content_type", "is_published"]

    def get_model(self, obj) -> str:
        return f"{obj.content_type.app_label}.{obj.content_type.model}"


class CustomFieldDefinitionWriteSerializer(BaseModelSerializer):
    model = serializers.CharField(write_only=True, required=False)
    choices = CustomFieldChoiceSerializer(many=True, required=False)

    class Meta:
        model = CustomFieldDefinition
        exclude = ["content_type", "is_published"]

    def validate(self, data):
        data = super().validate(data)
        model = data.pop("model", None)
        if model is not None:
            data["content_type"] = _resolve_content_type(model)
        elif self.instance is not None:
            data["content_type"] = self.instance.content_type
        else:
            raise serializers.ValidationError(
                {"model": "This field is required (e.g. 'pmbok.project')."}
            )

        field_type = data.get("field_type", getattr(self.instance, "field_type", None))
        if "choices" in data and field_type not in (
            FieldType.CHOICE,
            FieldType.MULTI_CHOICE,
        ):
            raise serializers.ValidationError(
                {"choices": "Choices are only allowed for choice fields."}
            )
        return data

    def _sync_choices(self, definition, choices):
        definition.choices.all().delete()
        CustomFieldChoice.objects.bulk_create(
            CustomFieldChoice(definition=definition, **choice) for choice in choices
        )

    def create(self, validated_data):
        choices = validated_data.pop("choices", None)
        definition = super().create(validated_data)
        if choices is not None:
            self._sync_choices(definition, choices)
        return definition

    def update(self, instance, validated_data):
        choices = validated_data.pop("choices", None)
        definition = super().update(instance, validated_data)
        if choices is not None:
            self._sync_choices(definition, choices)
        return definition


class CustomFieldsSerializerMixin(serializers.ModelSerializer):
    """Adds a writable ``custom_fields`` dict to a host model's serializer.

    Read: {key: value} for the object. Write: values are validated against the
    definitions applicable to the (prospective) folder, then applied after save.
    """

    custom_fields = serializers.SerializerMethodField()

    def get_custom_fields(self, obj) -> dict:
        return obj.custom_fields

    def validate(self, attrs):
        attrs = super().validate(attrs)
        raw = self.initial_data.get("custom_fields")
        if raw is None:
            self._pending_custom_fields = None
            return attrs
        if not isinstance(raw, dict):
            raise serializers.ValidationError(
                {"custom_fields": "Expected an object of {key: value}."}
            )
        folder = attrs.get("folder") or (
            getattr(self.instance, "folder", None) or Folder.get_root_folder()
        )
        self._pending_custom_fields = self._clean(raw, folder)
        return attrs

    def _clean(self, raw: dict, folder: Folder) -> list:
        content_type = ContentType.objects.get_for_model(self.Meta.model)
        definitions = {
            d.key: d
            for d in CustomFieldDefinition.objects.filter(
                content_type=content_type,
                folder_id__in={Folder.get_root_folder_id()}
                | CustomFieldDefinition._ancestor_or_self_ids(folder),
            ).prefetch_related("choices")
        }

        errors: dict = {}
        cleaned = []
        for key, value in raw.items():
            definition = definitions.get(key)
            if definition is None:
                errors[key] = "Unknown custom field for this object."
                continue
            try:
                cleaned.append((definition, self._clean_one(definition, value)))
            except ValueError as exc:
                errors[key] = str(exc)

        for key, definition in definitions.items():
            if not definition.required or key in raw:
                continue
            already_set = (
                self.instance is not None
                and self.instance.custom_field_values.filter(
                    definition=definition
                ).exists()
            )
            if not already_set:
                errors[key] = "This field is required."

        if errors:
            raise serializers.ValidationError({"custom_fields": errors})
        return cleaned

    @staticmethod
    def _clean_one(definition: CustomFieldDefinition, value):
        if definition.field_type == FieldType.MULTI_CHOICE:
            if value in (None, ""):
                return []
            if not isinstance(value, (list, tuple)):
                raise ValueError("Expected a list of choice values.")
            valid = set(definition.choices.values_list("value", flat=True))
            slugs = [str(v) for v in value]
            for slug in slugs:
                if slug not in valid:
                    raise ValueError(f"'{slug}' is not a valid choice.")
            return slugs

        coerced = coerce_value(definition.field_type, value)
        if coerced is not None and definition.field_type == FieldType.CHOICE:
            valid = set(definition.choices.values_list("value", flat=True))
            if coerced not in valid:
                raise ValueError(f"'{coerced}' is not a valid choice.")
        return coerced

    def _apply(self, instance):
        pending = getattr(self, "_pending_custom_fields", None)
        if not pending:
            return
        for definition, value in pending:
            instance.set_custom_field(definition, value)

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._apply(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._apply(instance)
        return instance
