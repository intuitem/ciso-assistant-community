import requests
from settings import API_URL, get_access_token

session = requests.Session()


def update_session_token():
    token = get_access_token()
    if token is None:
        raise ValueError("Failed to obtain access token for API authentication")
    session.headers.update({"Authorization": f"Token {token}"})


def get(url, **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30  # Default timeout of 30 seconds
    response = session.get(url, **kwargs)
    response.raise_for_status()
    return response


def post(url, **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30  # Default timeout of 30 seconds
    response = session.post(url, **kwargs)
    response.raise_for_status()
    return response


def patch(url, **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30  # Default timeout of 30 seconds
    response = session.patch(url, **kwargs)
    response.raise_for_status()
    return response


def put(url, **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30  # Default timeout of 30 seconds
    response = session.put(url, **kwargs)
    response.raise_for_status()
    return response


def delete(url, **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30  # Default timeout of 30 seconds
    response = session.delete(url, **kwargs)
    response.raise_for_status()
    return response


def get_api_headers(content_type: str = "", extra_headers: dict | None = None) -> dict:
    if extra_headers is None:
        extra_headers = {}
    token = get_access_token()
    if token is None:
        raise ValueError("Failed to obtain access token for API authentication")
    headers = {"Authorization": f"Token {token}"}
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
