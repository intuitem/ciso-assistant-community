import pytest


@pytest.fixture(autouse=True)
def _cold_feature_flags_cache():
    """Test-DB rollbacks don't fire post_save, so a flags dict cached by one
    test would otherwise leak into the next; every test starts cold."""
    from global_settings.utils import clear_feature_flags_cache

    clear_feature_flags_cache()
    yield
