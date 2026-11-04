from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction

from .models import (
    CustomFieldDefinition,
    CustomFieldValue,
    FieldType,
    coerce_value,
)


class CustomFieldsMixin(models.Model):
    """Opt-in mixin letting a host model carry custom field values.

    Adds a reverse generic relation plus thin read/write helpers. The serializer
    layer (CustomFieldsSerializerMixin) does validation/permissions; these helpers
    are the programmatic path used by it, tests, and scripts.
    """

    custom_field_values = GenericRelation(
        CustomFieldValue,
        content_type_field="content_type",
        object_id_field="object_id",
    )

    class Meta:
        abstract = True

    @property
    def custom_fields(self) -> dict:
        """{key: value} for every value stored on this object.

        choice → slug; multi_choice → list of slugs; others → typed python value.
        """
        result: dict = {}
        values = self.custom_field_values.all()
        if "custom_field_values" not in getattr(self, "_prefetched_objects_cache", {}):
            values = values.select_related("definition")
        for value in values:
            definition = value.definition
            if definition.field_type == FieldType.MULTI_CHOICE:
                result.setdefault(definition.key, []).append(value.value)
            else:
                result[definition.key] = value.value
        return result

    def copy_custom_fields_to(self, target):
        """Copy every stored value onto ``target``, a host of the same model."""
        CustomFieldValue.objects.bulk_create(
            CustomFieldValue(
                definition_id=value.definition_id,
                content_type_id=value.content_type_id,
                object_id=target.pk,
                value_text=value.value_text,
                value_number=value.value_number,
                value_date=value.value_date,
                value_boolean=value.value_boolean,
            )
            for value in self.custom_field_values.all()
        )
        target.clear_custom_field_cache()

    def clear_custom_field_cache(self):
        getattr(self, "_prefetched_objects_cache", {}).pop("custom_field_values", None)

    @transaction.atomic
    def set_custom_field(self, definition: CustomFieldDefinition, raw):
        """Upsert the value(s) of one definition on this object.

        ``raw`` is a list for multi_choice, a scalar otherwise. ``None``/empty
        clears the field. Choice values are validated against the definition.
        """
        content_type = ContentType.objects.get_for_model(self.__class__)
        if definition.content_type_id != content_type.id:
            raise ValueError("Custom field definition model does not match host model.")
        self.clear_custom_field_cache()
        base = self.custom_field_values.filter(definition=definition)

        if definition.field_type == FieldType.MULTI_CHOICE:
            base.delete()
            slugs = raw or []
            if not isinstance(slugs, (list, tuple, set)):
                raise ValueError("multi_choice value must be a list")
            valid = set(definition.choices.values_list("value", flat=True))
            for slug in slugs:
                slug = str(slug)
                if slug not in valid:
                    raise ValueError(f"'{slug}' is not a valid choice")
                CustomFieldValue.objects.create(
                    definition=definition,
                    content_type=content_type,
                    object_id=self.pk,
                    value_text=slug,
                )
            return

        coerced = coerce_value(definition.field_type, raw)
        if coerced is None:
            base.delete()
            return
        if definition.field_type == FieldType.CHOICE:
            valid = set(definition.choices.values_list("value", flat=True))
            if coerced not in valid:
                raise ValueError(f"'{coerced}' is not a valid choice")
        CustomFieldValue.objects.update_or_create(
            definition=definition,
            content_type=content_type,
            object_id=self.pk,
            defaults={definition.value_column: coerced},
        )
