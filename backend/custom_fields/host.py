"""Host-model mixin. Opt in by inheriting CustomFieldsMixin on the model."""

from typing import Any

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction


_TYPE_TO_VALUE_COLUMN = {
    "text": "value_text",
    "long_text": "value_text",
    "url": "value_text",
    "number": "value_number",
    "boolean": "value_boolean",
    "date": "value_date",
    "datetime": "value_datetime",
}

_ALL_VALUE_COLUMNS = (
    "value_text",
    "value_number",
    "value_boolean",
    "value_date",
    "value_datetime",
    "value_choice",
    "value_actor",
)


class CustomFieldsMixin(models.Model):
    """
    Reverse-side accessors for FieldValue rows attached to a host record.

        project.custom_fields                            # → {name: value, ...}
        project.set_custom_field("criticality", "high")  # upsert
        project.set_custom_field("criticality", None)    # clear
        project.set_custom_field("tags", [])             # clear (multi_choice)
    """

    field_values = GenericRelation(
        "custom_fields.FieldValue",
        content_type_field="content_type",
        object_id_field="object_id",
        related_query_name="host",
    )

    class Meta:
        abstract = True

    @staticmethod
    def prefetch_for_queryset(queryset):
        from django.db.models import Prefetch
        from custom_fields.models import FieldValue

        return queryset.prefetch_related(
            Prefetch(
                "field_values",
                queryset=FieldValue.objects.select_related(
                    "definition", "value_choice", "value_actor"
                ).prefetch_related("value_choices"),
            )
        )

    @transaction.atomic
    def set_custom_field(self, name: str, value: Any) -> None:
        from custom_fields.models import (
            FieldChoice,
            FieldDefinition,
            FieldValue,
        )

        ct = ContentType.objects.get_for_model(type(self))
        try:
            definition = FieldDefinition.objects.get(target_content_type=ct, name=name)
        except FieldDefinition.DoesNotExist as exc:
            raise ValueError(f"No field definition '{name}' for {ct.model}") from exc

        is_empty_clear = value is None or (
            definition.type == "multi_choice"
            and isinstance(value, (list, tuple, set))
            and len(value) == 0
        )
        if is_empty_clear:
            FieldValue.objects.filter(
                definition=definition, content_type=ct, object_id=self.pk
            ).delete()
            self._invalidate_custom_fields_cache()
            return

        # Wipe every typed column except the active one to prevent ghost data
        # if the definition's type was changed under existing values.
        defaults: dict[str, Any] = {col: None for col in _ALL_VALUE_COLUMNS}
        m2m_choices: list[FieldChoice] | None = None

        if definition.type in _TYPE_TO_VALUE_COLUMN:
            defaults[_TYPE_TO_VALUE_COLUMN[definition.type]] = value
        elif definition.type == "single_choice":
            defaults["value_choice"] = FieldChoice.objects.get(
                definition=definition, value=value
            )
        elif definition.type == "multi_choice":
            if not isinstance(value, (list, tuple, set)):
                raise ValueError("multi_choice value must be a list of choice slugs")
            wanted = list(dict.fromkeys(value))
            found = list(
                FieldChoice.objects.filter(definition=definition, value__in=wanted)
            )
            found_values = {c.value for c in found}
            missing = [v for v in wanted if v not in found_values]
            if missing:
                raise FieldChoice.DoesNotExist(
                    f"Unknown choice(s) {missing!r} for field {name!r}"
                )
            m2m_choices = found
        elif definition.type == "actor":
            from core.models import Actor

            defaults["value_actor"] = (
                value if isinstance(value, Actor) else Actor.objects.get(pk=value)
            )
        else:
            raise ValueError(f"Unknown field type {definition.type!r}")

        fv, _ = FieldValue.objects.update_or_create(
            definition=definition,
            content_type=ct,
            object_id=self.pk,
            defaults=defaults,
        )
        if m2m_choices is not None:
            fv.value_choices.set(m2m_choices)
        else:
            fv.value_choices.clear()

        self._invalidate_custom_fields_cache()

    def _invalidate_custom_fields_cache(self) -> None:
        self.__dict__.pop("custom_fields", None)

    @property
    def custom_fields(self) -> dict[str, Any]:
        cached = self.__dict__.get("custom_fields")
        if cached is not None:
            return cached
        result = self._compute_custom_fields()
        self.__dict__["custom_fields"] = result
        return result

    def _compute_custom_fields(self) -> dict[str, Any]:
        from custom_fields.models import FieldDefinition, FieldValue

        ct = ContentType.objects.get_for_model(type(self))
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "field_values" in prefetched:
            values_iter = self.field_values.all()
        else:
            values_iter = (
                FieldValue.objects.select_related(
                    "definition", "value_choice", "value_actor"
                )
                .prefetch_related("value_choices")
                .filter(content_type=ct, object_id=self.pk)
            )
        values_by_def = {v.definition_id: v for v in values_iter}

        definitions = FieldDefinition.objects.filter(
            target_content_type=ct, is_visible=True
        )
        out: dict[str, Any] = {}
        for d in definitions:
            v = values_by_def.get(d.id)
            out[d.name] = v.resolved_value if v is not None else d.default
        return out
