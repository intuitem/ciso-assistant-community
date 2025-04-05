import json

from loguru import logger
import requests
from settings import API_URL, TOKEN, VERIFY_CERTIFICATE


def get_api_headers(content_type: str = "", extra_headers: dict = {}) -> dict:
    headers = {"Authorization": f"Token {TOKEN}", "Accept": "application/json"}
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


def api_get(endpoint: str) -> dict:
    response = requests.get(
        endpoint, headers=get_api_headers(), verify=VERIFY_CERTIFICATE
    )
    if not response.ok:
        logger.error(
            "GET request failed",
            endpoint=endpoint,
            status_code=response.status_code,
            response=response.text,
        )
        raise Exception(f"GET request failed: {response.status_code}, {response.text}")
    return response.json()


def api_post(
    endpoint: str, data, json_data: bool = False, extra_headers: dict = {}
) -> dict:
    headers = get_api_headers("application/json" if json_data else "", extra_headers)
    if json_data:
        data = json.dumps(data)
    response = requests.post(
        endpoint, data=data, headers=headers, verify=VERIFY_CERTIFICATE
    )
    if not response.ok:
        logger.error(
            "POST request failed",
            endpoint=endpoint,
            status_code=response.status_code,
            response=response.text,
        )
        raise Exception(f"POST request failed: {response.status_code}, {response.text}")
    return response.json() if response.text else {}


def api_patch(
    endpoint: str, data, json_data: bool = True, extra_headers: dict = None
) -> dict:
    headers = get_api_headers("application/json" if json_data else "", extra_headers)
    if json_data:
        data = json.dumps(data)
    response = requests.patch(
        endpoint, data=data, headers=headers, verify=VERIFY_CERTIFICATE
    )
    if not response.ok:
        logger.error(
            "PATCH request failed",
            endpoint=endpoint,
            status_code=response.status_code,
            response=response.text,
        )
        raise Exception(
            f"PATCH request failed: {response.status_code}, {response.text}"
        )
    return response.json() if response.text else {}
