import pytest


@pytest.fixture(autouse=True)
def _cold_feature_flags_cache():
    """Test-DB rollbacks don't fire post_save, so a flags dict cached by one
    test would otherwise leak into the next; every test starts cold."""
    from global_settings.utils import clear_feature_flags_cache

    clear_feature_flags_cache()
    yield


@pytest.fixture
def mcp_on(db):
    """Turn the MCP kill switch on (it is off by default)."""
    from global_settings.models import GlobalSettings
    from global_settings.utils import clear_feature_flags_cache

    settings_row, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
    )
    settings_row.value = {**(settings_row.value or {}), "mcp": True}
    settings_row.save()
    clear_feature_flags_cache()


@pytest.fixture
def app_profile(db):
    """A profile for the connections a test makes: a transactional test flushes
    the ones the migration seeds."""
    from iam.models import ConnectionProfile

    profile, _ = ConnectionProfile.objects.get_or_create(
        name="Read and change", defaults={"level": "update", "is_default": True}
    )
    return profile
