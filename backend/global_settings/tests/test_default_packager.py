"""
Tests for the default_packager general setting: a library packager is capped at
32 characters, but a value predating the cap is resubmitted unchanged by the
settings form and must keep saving.
"""

import pytest
from rest_framework import serializers as drf_serializers

from global_settings.models import GlobalSettings
from global_settings.serializers import GeneralSettingsSerializer


@pytest.fixture
def general_settings(db):
    settings, _ = GlobalSettings.objects.get_or_create(name="general")
    settings.value = settings.value or {}
    settings.save()
    return settings


def _update(general_settings, packager):
    GeneralSettingsSerializer().update(
        general_settings, {"value": {"default_packager": packager}}
    )


def test_default_packager_is_capped_at_32_characters(general_settings):
    _update(general_settings, "p" * 32)
    with pytest.raises(drf_serializers.ValidationError):
        _update(general_settings, "p" * 33)


def test_default_packager_predating_the_cap_keeps_saving(general_settings):
    general_settings.value["default_packager"] = "p" * 40
    general_settings.save()
    _update(general_settings, "p" * 40)  # resubmitted unchanged
    with pytest.raises(drf_serializers.ValidationError):
        _update(general_settings, "q" * 40)
