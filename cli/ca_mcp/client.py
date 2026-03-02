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


def make_delete_request(endpoint):
    """
    Make a DELETE request to the API

    Args:
        endpoint: API endpoint (e.g., "/task-templates/{id}/")

    Returns:
        Response object
    """
    url = f"{API_URL}{endpoint}"
    return requests.delete(
        url,
        headers=get_headers(),
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


def fetch_all_results(endpoint, params=None):
    """
    Fetch all paginated results from an API endpoint by following 'next' links.

    This function handles Django REST Framework's LimitOffsetPagination by following
    the 'next' URL in the response until all pages are retrieved.

    Args:
        endpoint: API endpoint (e.g., "/compliance-assessments/")
        params: Optional query parameters (only applied to first request)

    Returns:
        Tuple of (list of all results, error_message or None)

    Example:
        results, error = fetch_all_results("/compliance-assessments/")
        if error:
            return error
        # process results...
    """
    results_list = []
    next_url = endpoint

    # Only apply params to the first request
    current_params = params

    while next_url:
        # Make request - if next_url is a full URL from pagination, extract just the path
        if next_url.startswith("http://") or next_url.startswith("https://"):
            # Parse the full URL to extract path and query params
            from urllib.parse import urlparse, parse_qs

            parsed = urlparse(next_url)
            next_url = parsed.path
            # Convert query string to params dict for subsequent requests
            current_params = {
                k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()
            }

        res = make_get_request(next_url, params=current_params)

        if res.status_code != 200:
            error_msg = f"Error: HTTP {res.status_code} - {res.text}"
            return results_list, error_msg

        data = res.json()

        # Handle paginated response
        if isinstance(data, dict) and "results" in data:
            results = data.get("results", [])
            results_list.extend(results)
            next_url = data.get("next")  # Get next page URL
            current_params = (
                None  # Clear params for subsequent requests (included in next_url)
            )
        # Handle non-paginated response (list)
        elif isinstance(data, list):
            results_list.extend(data)
            next_url = None  # No pagination for list responses
        else:
            error_msg = f"Unexpected API response format: {type(data)}"
            return results_list, error_msg

    return results_list, None
