"""
Shared fixtures for all iam tests.
"""

import pytest
from django.core.cache import cache

from global_settings import utils as ff_utils


@pytest.fixture(autouse=True)
def _enterprise_flags(monkeypatch):
    """service_accounts is enterprise-only (declared on the EE
    FeatureFlagsSerializer, hence unsupported on CE); these tests exercise
    the EE-gated behavior from the CE test bed."""
    supported = ff_utils.get_supported_feature_flags() | {"service_accounts"}
    monkeypatch.setattr(ff_utils, "get_supported_feature_flags", lambda: supported)


@pytest.fixture(autouse=True)
def clear_oidc_cache():
    """LocMemCache is process-global and pytest-django doesn't clear it between
    tests, so cached OIDC discovery/JWKS documents would otherwise leak across
    tests (and test files) that share a server_url."""
    cache.clear()
    yield
    cache.clear()
