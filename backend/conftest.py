import pytest


@pytest.fixture(autouse=True)
def _cold_feature_flags_cache():
    """Test-DB rollbacks don't fire post_save, so a flags dict cached by one
    test would otherwise leak into the next; every test starts cold."""
    from global_settings.utils import clear_feature_flags_cache

    clear_feature_flags_cache()
    yield


@pytest.fixture
def mcp_on(db, monkeypatch):
    monkeypatch.setattr("iam.mcp_access.has_shared_cache", lambda: True)
    from global_settings.models import GlobalSettings
    from global_settings.utils import clear_feature_flags_cache

    settings_row, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
    )
    settings_row.value = {**(settings_row.value or {}), "mcp": True}
    settings_row.save()
    clear_feature_flags_cache()


@pytest.fixture
def mcp_write_on(mcp_on):
    from global_settings.models import GlobalSettings
    from global_settings.utils import clear_feature_flags_cache

    settings_row = GlobalSettings.objects.get(name=GlobalSettings.Names.FEATURE_FLAGS)
    settings_row.value = {**settings_row.value, "mcp_write": True}
    settings_row.save()
    clear_feature_flags_cache()
