from django.contrib.contenttypes.models import ContentType
from rest_framework.filters import BaseFilterBackend, SearchFilter

from .models import CustomFieldDefinition, CustomFieldValue, coerce_value

PREFIX = "cf."
LOOKUPS = {"exact", "in", "gte", "lte", "gt", "lt", "icontains"}
TEXT_ONLY_LOOKUPS = {"icontains"}


class CustomFieldFilterBackend(BaseFilterBackend):
    """Translates ``cf.<key>[__lookup]=`` query params into joins on the host
    model's custom field values.

    Each field predicate is applied in its own ``.filter()`` call so Django emits
    an independent join — the conditions AND across separate value rows. Combining
    them into one filter would require a single row to satisfy every field at once
    and return nothing.
    """

    def filter_queryset(self, request, queryset, view):
        params = request.query_params
        cf_params = [k for k in params if k.startswith(PREFIX)]
        if not cf_params:
            return queryset

        content_type = ContentType.objects.get_for_model(queryset.model)
        definitions = {
            d.key: d
            for d in CustomFieldDefinition.objects.filter(
                content_type=content_type, filterable=True
            )
        }

        for raw_key in cf_params:
            field_key, _, lookup = raw_key[len(PREFIX) :].partition("__")
            lookup = lookup or "exact"
            definition = definitions.get(field_key)
            if definition is None or lookup not in LOOKUPS:
                continue
            column = definition.value_column
            if lookup in TEXT_ONLY_LOOKUPS and column != "value_text":
                continue

            try:
                target = self._coerce(definition, lookup, params.getlist(raw_key))
            except ValueError:
                return queryset.none()

            queryset = queryset.filter(
                custom_field_values__definition__key=field_key,
                **{f"custom_field_values__{column}__{lookup}": target},
            )
        return queryset

    @staticmethod
    def _coerce(definition: CustomFieldDefinition, lookup: str, raw_values: list):
        # __in accepts repeated params and/or a single comma-separated value.
        if lookup == "in":
            tokens: list = []
            for raw in raw_values:
                tokens.extend(raw.split(","))
            return [coerce_value(definition.field_type, t.strip()) for t in tokens]

        raw = raw_values[-1]
        if lookup in TEXT_ONLY_LOOKUPS:
            return raw
        return coerce_value(definition.field_type, raw)


class CustomFieldSearchFilter(SearchFilter):
    """Extends DRF search to also match ``searchable`` custom text values.

    The default model-field search and the custom-field search are OR-ed so an
    object surfaces if either matches the term.
    """

    def filter_queryset(self, request, queryset, view):
        base = super().filter_queryset(request, queryset, view)
        term = " ".join(self.get_search_terms(request)).strip()
        if not term:
            return base
        content_type = ContentType.objects.get_for_model(queryset.model)
        cf_ids = CustomFieldValue.objects.filter(
            content_type=content_type,
            definition__searchable=True,
            value_text__icontains=term,
        ).values_list("object_id", flat=True)
        if not cf_ids:
            return base
        return (base | queryset.filter(pk__in=list(cf_ids))).distinct()
