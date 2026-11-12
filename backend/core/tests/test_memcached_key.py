"""With memcached, cache keys it would refuse are hashed
(ciso_assistant.settings._memcached_key)."""

import pytest
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheKey
from django.test import override_settings

from ciso_assistant import settings as project_settings

MEMCACHED = project_settings._memcached_cache("unix:/nonexistent/memcached.sock")


def test_valid_keys_are_unchanged():
    assert project_settings._memcached_key("allauth:rl:login", "", 1) == (
        ":1:allauth:rl:login"
    )


@override_settings(CACHES={"default": {**MEMCACHED, "KEY_FUNCTION": None}})
def test_django_refuses_long_keys_with_its_default_key_function():
    with pytest.raises(InvalidCacheKey):
        cache.get("saml.metadata." + "x" * 300)


@pytest.mark.parametrize(
    "key", ["saml.metadata." + "x" * 300, "with a space", "non-ascii-é"]
)
@override_settings(CACHES={"default": MEMCACHED})
def test_keys_memcached_would_refuse_are_hashed(key):
    assert len(project_settings._memcached_key(key, "", 1)) < 100
    assert cache.get(key) is None  # no InvalidCacheKey
