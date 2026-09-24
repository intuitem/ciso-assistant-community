import pytest
from django.test import override_settings


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """The cache table is not a model, so `migrate` never creates it. Tests marked
    `db_cache` run against the real DatabaseCache and need it in the test database."""
    from django.core.management import call_command

    with django_db_blocker.unblock():
        call_command("setup_cache_table", verbosity=0)
    yield


@pytest.fixture(autouse=True)
def _locmem_cache(request):
    """Production backs the cache with DatabaseCache so login-throttle counters
    are shared across gunicorn workers."""
    if request.node.get_closest_marker("db_cache"):
        yield
        return
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
