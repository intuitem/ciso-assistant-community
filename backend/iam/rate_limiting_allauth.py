import time
from typing import Any

from django.conf import settings

# This file is separated from `rate_limiting.py` as the functions in this file must be usable(ready) before the django apps load.

def _get_allauth_setting(name: str, default: Any) -> Any:
    is_custom_rate_limiting_enabled = getattr(settings, "ENABLE_CUSTOM_LOGIN_RATE_LIMITING", False)

    value = getattr(settings, name, default)
    if name == "ACCOUNT_RATE_LIMITS" and value is not False:
        if is_custom_rate_limiting_enabled:
            # The custom rate limiting replaces allauth's IP login limit.
            value = {**value, "login": None}

    return value
