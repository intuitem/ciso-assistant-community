"""Derives, from the real DRF router registrations and their FilterSets, which
model each SavedFilter.properties field references -- so the mapping used to
enforce read visibility (see SavedFilterViewSet) can never drift from the
actual filterable fields exposed on a model's list view.
"""

from functools import lru_cache

import django_filters as df
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers


def _build_model_to_filterset_class() -> dict:
    from core.urls import router as drf_router
    from core.views import BaseModelViewSet

    mapping = {}
    for _, viewset, _ in drf_router.registry:
        if not (isinstance(viewset, type) and issubclass(viewset, BaseModelViewSet)):
            continue
        model = getattr(viewset, "model", None)
        if model is None:
            continue
        try:
            filterset_class = viewset().filterset_class
        except Exception:
            filterset_class = None
        if filterset_class is not None:
            mapping[model] = filterset_class
    return mapping


@lru_cache(maxsize=1)
def get_model_to_filterset_class() -> dict:
    return _build_model_to_filterset_class()


@lru_cache(maxsize=None)
def get_referenced_models(model: type) -> dict:
    """{properties_field_name: referenced_model} for every filter field of
    ``model``'s FilterSet that references another model's id(s). ``id`` always
    refers to the target model itself (GenericFilterSet.UUIDInFilter)."""
    refs = {"id": model}
    filterset_class = get_model_to_filterset_class().get(model)
    if filterset_class is None:
        return refs
    for field_name, filt in filterset_class.base_filters.items():
        if isinstance(filt, (df.ModelChoiceFilter, df.ModelMultipleChoiceFilter)):
            queryset = filt.queryset
            if queryset is not None:
                refs[field_name] = queryset.model
    return refs


def eligible_models() -> set:
    """Models usable as SavedFilter.content_type: those with an RBAC-scoped
    list view (a BaseModelViewSet + FilterSet) to check references against."""
    return set(get_model_to_filterset_class().keys())


def eligible_models_by_urlmodel() -> dict:
    """{router URL prefix: 'app_label.model'} for every eligible model, so the
    frontend can resolve its URLModel to a content_type without hardcoding
    the mapping -- a backend model rename then needs no frontend change."""
    from core.urls import router as drf_router

    eligible = get_model_to_filterset_class()
    mapping = {}
    for prefix, viewset, _ in drf_router.registry:
        model = getattr(viewset, "model", None)
        if model not in eligible:
            continue
        ct = ContentType.objects.get_for_model(model)
        mapping[prefix] = f"{ct.app_label}.{ct.model}"
    return mapping


def resolve_saved_filter_content_type(model: str) -> ContentType:
    """Resolve an 'app_label.model' string to a ContentType, restricted to
    models with a real FilterSet (see eligible_models) so read-visibility
    checks stay meaningful."""
    try:
        app_label, model_name = model.lower().split(".")
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
    except (ValueError, ContentType.DoesNotExist):
        raise serializers.ValidationError(
            {"model": f"'{model}' is not a valid app_label.model"}
        )
    if content_type.model_class() not in eligible_models():
        raise serializers.ValidationError(
            {"model": f"'{model}' does not support saved filters"}
        )
    return content_type
