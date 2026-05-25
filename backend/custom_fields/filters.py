"""Dynamic FilterSet injection: each FieldDefinition becomes a ?field_<name>=<value> filter."""

from decimal import Decimal, InvalidOperation
from datetime import date, datetime

import django_filters as df
from django.contrib.contenttypes.models import ContentType
from django.db import DatabaseError
from django.db.models import Prefetch

from custom_fields.models import FieldDefinition, FieldValue


TYPE_TO_VALUE_COLUMN = {
    "text": "value_text__icontains",
    "long_text": "value_text__icontains",
    "url": "value_text__icontains",
    "number": "value_number",
    "boolean": "value_boolean",
    "date": "value_date",
    "datetime": "value_datetime",
    "single_choice": "value_choice__value__in",
    "multi_choice": "value_choices__value__in",
    "actor": "value_actor_id",
}

# CharFilter on scalar types so our `method` (and `_coerce`) runs on every input.
# Native NumberFilter/etc would silently drop invalid input → unfiltered queryset.
TYPE_TO_FILTER_CLASS: dict[str, type[df.Filter]] = {
    "text": df.CharFilter,
    "long_text": df.CharFilter,
    "url": df.CharFilter,
    "number": df.CharFilter,
    "boolean": df.CharFilter,
    "date": df.CharFilter,
    "datetime": df.CharFilter,
    "single_choice": df.BaseCSVFilter,
    "multi_choice": df.BaseCSVFilter,
    "actor": df.CharFilter,
}


# Sentinel: garbage input. _coerce returns this; filter translates to .none().
_PARSE_FAILURE = object()


def _coerce(value, d_type: str):
    if value in (None, "", []):
        return None
    if d_type == "number":
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            return _PARSE_FAILURE
    if d_type == "boolean":
        if isinstance(value, bool):
            return value
        lowered = str(value).lower()
        if lowered in ("true", "1", "yes", "y"):
            return True
        if lowered in ("false", "0", "no", "n"):
            return False
        return _PARSE_FAILURE
    if d_type == "date":
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        try:
            return date.fromisoformat(str(value))
        except (ValueError, TypeError):
            return _PARSE_FAILURE
    if d_type == "datetime":
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except (ValueError, TypeError):
            return _PARSE_FAILURE
    return value


def _make_filter_method(definition_name: str, d_type: str, content_type_id: int):
    lookup = TYPE_TO_VALUE_COLUMN[d_type]
    is_csv = d_type in ("single_choice", "multi_choice")

    def method(self, queryset, name, value):
        if is_csv:
            if not value:
                return queryset
            filter_value: object = [v for v in value if v not in (None, "")]
            if not filter_value:
                return queryset
        else:
            scalar = _coerce(value, d_type)
            if scalar is None:
                return queryset
            if scalar is _PARSE_FAILURE:
                return queryset.none()
            filter_value = scalar

        object_ids = FieldValue.objects.filter(
            definition__name=definition_name,
            content_type_id=content_type_id,
            **{lookup: filter_value},
        ).values_list("object_id", flat=True)
        return queryset.filter(id__in=object_ids).distinct()

    method.__name__ = f"filter_field_{definition_name}"
    return method


def _build_filterset(
    base_filterset_class: type[df.FilterSet], model
) -> type[df.FilterSet]:
    try:
        ct = ContentType.objects.get_for_model(model)
        definitions = list(
            FieldDefinition.objects.filter(
                target_content_type=ct,
                filterable=True,
                is_visible=True,
            )
        )
    except DatabaseError:
        return base_filterset_class

    if not definitions:
        return base_filterset_class

    class_attrs: dict = {}
    for d in definitions:
        if d.type not in TYPE_TO_FILTER_CLASS:
            continue
        filter_method = _make_filter_method(d.name, d.type, ct.id)
        method_name = filter_method.__name__
        class_attrs[method_name] = filter_method
        class_attrs[f"field_{d.name}"] = TYPE_TO_FILTER_CLASS[d.type](
            method=method_name
        )

    if not class_attrs:
        return base_filterset_class

    return type(
        f"{base_filterset_class.__name__}WithCustomFields",
        (base_filterset_class,),
        class_attrs,
    )


class CustomFieldsViewSetMixin:
    """Mix in BEFORE BaseModelViewSet — overrides filterset_class and get_queryset."""

    @property
    def filterset_class(self):
        base = super().filterset_class
        if base is None or self.model is None:
            return base
        return _build_filterset(base, self.model)

    def get_queryset(self):
        queryset = super().get_queryset()
        if queryset is None or self.model is None:
            return queryset
        if hasattr(self.model, "field_values"):
            try:
                queryset = queryset.prefetch_related(
                    Prefetch(
                        "field_values",
                        queryset=FieldValue.objects.select_related(
                            "definition", "value_choice", "value_actor"
                        ).prefetch_related("value_choices"),
                    )
                )
            except DatabaseError:
                pass
        return queryset
