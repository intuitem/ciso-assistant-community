import time
from typing import Any

from django.conf import settings

# This file is separated from `rate_limiting.py` as the functions in this file must be usable(ready) before the django apps load.

_RATE_LIMIT_CACHE_TTL = 5
_rate_limit_cache: tuple[float, bool] = (0.0, False)


def _is_custom_rate_limit_activated() -> bool:
    global _rate_limit_cache
    expires_at, is_activated = _rate_limit_cache
    if time.monotonic() < expires_at:
        return is_activated

    try:
        from global_settings.models import GlobalSettings

        obj = GlobalSettings.objects.filter(
            name=GlobalSettings.Names.INFRA_CONFIG
        ).first()

        value = obj.value if obj and isinstance(obj.value, dict) else {}
        is_activated = bool(value.get("is_rate_limit_activated", False))
    except Exception:
        # DB not ready (startup checks, migrations).
        is_activated = False

    _rate_limit_cache = (time.monotonic() + _RATE_LIMIT_CACHE_TTL, is_activated)
    return is_activated


def _get_allauth_setting(name: str, dflt: Any) -> Any:
    value = getattr(settings, name, dflt)
    if name == "ACCOUNT_RATE_LIMITS" and value is not False:
        if _is_custom_rate_limit_activated():
            # The custom rate limiting replaces allauth's IP login limit.
            value = {**value, "login": None}

    return value
