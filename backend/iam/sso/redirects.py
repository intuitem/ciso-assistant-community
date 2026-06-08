from urllib.parse import urlparse

from django.conf import settings

SSO_AUTHENTICATE_PATH = "/sso/authenticate"


def get_sso_authenticate_url(next_url: str | None = None) -> str:
    fallback_url = f"{settings.CISO_ASSISTANT_URL.rstrip('/')}{SSO_AUTHENTICATE_PATH}"
    if not next_url:
        return fallback_url

    parsed_next_url = urlparse(next_url)
    if parsed_next_url.scheme or parsed_next_url.netloc:
        parsed_app_url = urlparse(settings.CISO_ASSISTANT_URL)
        if (
            parsed_next_url.scheme != parsed_app_url.scheme
            or parsed_next_url.netloc != parsed_app_url.netloc
        ):
            return fallback_url

    if parsed_next_url.path != SSO_AUTHENTICATE_PATH:
        return fallback_url

    if not parsed_next_url.scheme and not parsed_next_url.netloc:
        query = f"?{parsed_next_url.query}" if parsed_next_url.query else ""
        return f"{fallback_url}{query}"

    return next_url
