"""
Tests for ff_is_enabled: cached lookups, cache invalidation at the write
points, and the edition gating derived from the FeatureFlags serializer
(enterprise-only flags short-circuit to False on CE).
"""

import pytest

from global_settings import utils as ff_utils
from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
from global_settings.utils import (
    clear_feature_flags_cache,
    ff_is_enabled,
    get_supported_feature_flags,
)

ENTERPRISE_ONLY_SAMPLE = ("idp_groups", "service_accounts", "custom_fields")


@pytest.fixture
def flags_row(db):
    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    gs.value = {"incidents": True, "xrays": False}
    gs.save(update_fields=["value"])
    # Direct ORM writes bypass the write-point invalidation, and the
    # audit-log handler warms the cache during save.
    clear_feature_flags_cache()
    return gs


def test_returns_flag_value(flags_row):
    assert ff_is_enabled("incidents") is True
    assert ff_is_enabled("xrays") is False


def test_unknown_flag_returns_false(flags_row):
    assert ff_is_enabled("does_not_exist") is False


def test_missing_row_returns_false(db):
    assert not GlobalSettings.objects.filter(
        name=GlobalSettings.Names.FEATURE_FLAGS
    ).exists()
    assert ff_is_enabled("incidents") is False


def test_malformed_row_returns_false(db):
    # A legacy row may carry a non-dict value; treat it as missing.
    GlobalSettings.objects.update_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": []}
    )
    clear_feature_flags_cache()
    assert ff_is_enabled("incidents") is False


def test_flag_lookups_are_cached(flags_row, django_assert_num_queries):
    ff_is_enabled("incidents")  # warm the cache
    with django_assert_num_queries(0):
        assert ff_is_enabled("incidents") is True
        assert ff_is_enabled("xrays") is False
        assert ff_is_enabled("does_not_exist") is False


def test_missing_row_is_cached(db, django_assert_num_queries):
    ff_is_enabled("incidents")  # warm the cache with the missing-row state
    with django_assert_num_queries(0):
        assert ff_is_enabled("incidents") is False


def test_serializer_update_invalidates_cache(flags_row):
    assert ff_is_enabled("incidents") is True  # warm the cache
    serializer = FeatureFlagsSerializer(flags_row, data={"incidents": False})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    assert ff_is_enabled("incidents") is False


def test_unsupported_flags_short_circuit_on_ce(flags_row, django_assert_num_queries):
    # Enterprise-only flags are outside CE's SUPPORTED_FEATURE_FLAGS:
    # False without any settings query, even when the row carries them.
    flags_row.value = {**flags_row.value, "idp_groups": True}
    flags_row.save(update_fields=["value"])
    clear_feature_flags_cache()
    for flag in ENTERPRISE_ONLY_SAMPLE:
        with django_assert_num_queries(0):
            assert ff_is_enabled(flag) is False


def test_supported_flags_resolve_normally_when_extended(flags_row, monkeypatch):
    # On EE the FeatureFlags serializer (resolved via MODULE_PATHS) declares
    # the extra flags; a supported flag resolves against the row normally.
    supported = get_supported_feature_flags() | {"idp_groups"}
    monkeypatch.setattr(ff_utils, "get_supported_feature_flags", lambda: supported)
    flags_row.value = {**flags_row.value, "idp_groups": True}
    flags_row.save(update_fields=["value"])
    clear_feature_flags_cache()
    assert ff_is_enabled("idp_groups") is True


def test_supported_flags_derived_from_serializer():
    # The supported set is derived from the edition's FeatureFlags serializer,
    # the single source of truth — CE flags in, enterprise-only flags out.
    supported = get_supported_feature_flags()
    declared = {
        field.source.split(".")[-1]
        for field in FeatureFlagsSerializer().fields.values()
        if getattr(field, "source", None) and field.source.startswith("value.")
    }
    assert supported == declared
    assert "incidents" in supported
    assert "idp_groups" not in supported
