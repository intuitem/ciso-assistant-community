from typing import Any

from django.conf import settings

# This file is separated from `rate_limiting.py` as the functions in this file must be usable(ready) before the django apps load.


def is_custom_rate_limiting_enabled() -> bool:
    """Return `True` if the (custom)rate limiting is activated, return `False` otherwise."""
    try:
        from global_settings.models import GlobalSettings

        obj = GlobalSettings.objects.filter(
            name=GlobalSettings.Names.RATE_LIMITING
        ).first()

        value = obj.value if obj and isinstance(obj.value, dict) else {}
        return value.get("enabled", False) is True
    except Exception:
        # DB not ready (startup checks, migrations).
        return False


def _get_allauth_setting(name: str, default: Any) -> Any:
    value = getattr(settings, name, default)
    if name == "ACCOUNT_RATE_LIMITS" and value is not False:
        if is_custom_rate_limiting_enabled():
            # Keep the inconsistent allauth per-account rate-limiting for now (as it's obviously better than removing it).
            attempts_amount = getattr(settings, "ACCOUNT_LOGIN_ATTEMPTS_LIMIT", 5)
            attempts_timeout = getattr(
                settings, "ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT", 60 * 5
            )
            value = {
                **value,
                "login": None,
                "login_failed": f"{attempts_amount}/{attempts_timeout}s/key",
            }

    return value
