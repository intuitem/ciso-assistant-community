"""
Tests for ff_is_enabled: cached lookups, cache invalidation at the single
write point (FeatureFlagsSerializer.update), and the CE short-circuit for
enterprise-only flags.
"""

import pytest

from global_settings import utils
from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
from global_settings.utils import (
    ENTERPRISE_ONLY_FEATURE_FLAGS,
    clear_feature_flags_cache,
    ff_is_enabled,
)


@pytest.fixture
def flags_row(db):
    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    gs.value = {"incidents": True, "xrays": False}
    gs.save(update_fields=["value"])
    # Direct ORM writes bypass the serializer (the single invalidation
    # point), and the audit-log handler warms the cache during save.
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


def test_enterprise_only_flags_short_circuit_on_ce(db, django_assert_num_queries):
    # CE (enterprise_core not installed): False without any settings query.
    for flag in ENTERPRISE_ONLY_FEATURE_FLAGS:
        with django_assert_num_queries(0):
            assert ff_is_enabled(flag) is False


def test_enterprise_only_flags_resolve_normally_on_ee(flags_row, monkeypatch):
    monkeypatch.setattr(utils, "_is_enterprise", lambda: True)
    flags_row.value = {**flags_row.value, "idp_groups": True}
    flags_row.save(update_fields=["value"])
    clear_feature_flags_cache()
    assert ff_is_enabled("idp_groups") is True
