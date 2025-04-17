import requests
from settings import API_URL, get_access_token

session = requests.Session()


def update_session_token():
    session.headers.update({"Authorization": f"Token {get_access_token()}"})


def get(url, **kwargs):
    response = session.get(url, **kwargs)
    response.raise_for_status()
    return response


def post(url, **kwargs):
    response = session.post(url, **kwargs)
    response.raise_for_status()
    return response


def patch(url, **kwargs):
    response = session.patch(url, **kwargs)
    response.raise_for_status()
    return response


def put(url, **kwargs):
    response = session.put(url, **kwargs)
    response.raise_for_status()
    return response


def delete(url, **kwargs):
    response = session.delete(url, **kwargs)
    response.raise_for_status()
    return response


def get_api_headers(content_type: str = "", extra_headers: dict = {}) -> dict:
    headers = {"Authorization": f"Token {get_access_token()}"}
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
