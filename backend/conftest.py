import pytest
from django.test import override_settings


@pytest.fixture(autouse=True)
def _locmem_cache():
    """Production backs the cache with DatabaseCache so login-throttle counters
    are shared across gunicorn workers."""
    with override_settings(
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    ):
        yield


@pytest.fixture(autouse=True)
def _cold_feature_flags_cache(_locmem_cache):
    """Test-DB rollbacks don't fire post_save, so a flags dict cached by one
    test would otherwise leak into the next; every test starts cold."""
    from global_settings.utils import clear_feature_flags_cache

    clear_feature_flags_cache()
    yield
