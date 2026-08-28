"""
Shared fixtures for all iam tests.
"""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clear_oidc_cache():
    """LocMemCache is process-global and pytest-django doesn't clear it between
    tests, so cached OIDC discovery/JWKS documents would otherwise leak across
    tests (and test files) that share a server_url."""
    cache.clear()
    yield
    cache.clear()
