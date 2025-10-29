"""HTTP client utilities for CISO Assistant API"""

import requests
import sys
from rich import print as rprint
from .config import API_URL, TOKEN, VERIFY_CERTIFICATE, HTTP_TIMEOUT


def get_headers():
    """Get common headers for API requests"""
    return {
        "Authorization": f"Token {TOKEN}",
    }


def get_json_headers():
    """Get headers for JSON API requests"""
    return {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json",
    }


def make_get_request(endpoint, params=None):
    """
    Make a GET request to the API

    Args:
        endpoint: API endpoint (e.g., "/risk-scenarios/")
        params: Optional query parameters

    Returns:
        Response object
    """
    url = f"{API_URL}{endpoint}"
    return requests.get(
        url,
        headers=get_headers(),
        params=params,
        verify=VERIFY_CERTIFICATE,
        timeout=HTTP_TIMEOUT,
    )


def make_post_request(endpoint, payload):
    """
    Make a POST request to the API

    Args:
        endpoint: API endpoint (e.g., "/folders/")
        payload: JSON payload

    Returns:
        Response object
    """
    url = f"{API_URL}{endpoint}"
    return requests.post(
        url,
        headers=get_json_headers(),
        json=payload,
        verify=VERIFY_CERTIFICATE,
        timeout=HTTP_TIMEOUT,
    )


def make_patch_request(endpoint, payload):
    """
    Make a PATCH request to the API

    Args:
        endpoint: API endpoint (e.g., "/assets/{id}/")
        payload: JSON payload

    Returns:
        Response object
    """
    url = f"{API_URL}{endpoint}"
    return requests.patch(
        url,
        headers=get_json_headers(),
        json=payload,
        verify=VERIFY_CERTIFICATE,
        timeout=HTTP_TIMEOUT,
    )


def handle_response(res, error_message="Error"):
    """
    Handle API response and check for errors

    Args:
        res: Response object
        error_message: Error message prefix

    Returns:
        JSON data if successful, None if error
    """
    if res.status_code not in [200, 201]:
        rprint(f"{error_message}: HTTP {res.status_code} - {res.text}", file=sys.stderr)
        return None
    return res.json()


def get_paginated_results(data):
    """
    Extract results from paginated or non-paginated response

    Args:
        data: Response JSON data

    Returns:
        List of results
    """
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    elif isinstance(data, list):
        return data
    return []
