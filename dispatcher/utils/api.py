import json

from loguru import logger
import requests
from settings import API_URL, TOKEN, VERIFY_CERTIFICATE


def get_api_headers(content_type: str = "", extra_headers: dict = {}) -> dict:
    headers = {"Authorization": f"Token {TOKEN}"}
    if content_type:
        headers["Content-Type"] = content_type
    if extra_headers:
        headers.update(extra_headers)
    return headers


def make_api_endpoint(*parts: str) -> str:
    """Constructs an endpoint URL from API_URL and provided parts."""
    endpoint = "/".join(str(part).strip("/") for part in (API_URL,) + parts)
    # Ensure trailing slash if needed by API
    return endpoint + "/"
