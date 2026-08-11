"""HTTP client utilities for CISO Assistant API"""

import requests
import sys
from urllib.parse import urlsplit
from rich import print as rprint
from .auth import get_request_token
from .config import (
    API_URL,
    VERIFY_CERTIFICATE,
    HTTP_TIMEOUT,
    DEFAULT_PAGE_LIMIT,
    MAX_TOTAL_ITEMS,
)


API_PATH = urlsplit(API_URL).path.rstrip("/")


def get_headers():
    """Get common headers for API requests"""
    return {
        "Authorization": f"Token {get_request_token()}",
    }


def get_json_headers():
    """Get headers for JSON API requests"""
    return {
        "Authorization": f"Token {get_request_token()}",
        "Content-Type": "application/json",
    }


def make_get_request(endpoint, params=None):
    """
    Make a GET request to the API

    A default `limit` is injected when the caller supplies none, so an
    unbounded list endpoint cannot return an entire register into the model's
    context. Callers that need a different page size just pass their own.

    Args:
        endpoint: API endpoint (e.g., "/risk-scenarios/")
        params: Optional query parameters

    Returns:
        Response object
    """
    url = f"{API_URL}{endpoint}"
    params = dict(params or {})
    params.setdefault("limit", DEFAULT_PAGE_LIMIT)
    # A caller-supplied limit must not escape the bounded-response contract:
    # an MCP client can ask for any number, and every returned row then gets
    # fetched and formatted. Clamp instead of trusting it.
    try:
        requested = int(params["limit"])
        params["limit"] = max(1, min(requested, MAX_TOTAL_ITEMS))
    except (TypeError, ValueError):
        params["limit"] = DEFAULT_PAGE_LIMIT
    return requests.get(
        url,
        headers=get_headers(),
        params=params,
        verify=VERIFY_CERTIFICATE,
        timeout=HTTP_TIMEOUT,
    )


class ResultList(list):
    """A results list that can carry paging context without changing the
    (results, error) contract every caller relies on."""

    truncation_note = ""
    total = None


def found_line(items, noun, paginated=False, offset=0):
    """'Found N of TOTAL x' when the page is short of the total, else 'Found N x'.

    Bounding responses without this makes every count a lie: the tool would
    report the page size as though it were the total.

    Only advertise `offset` when the calling tool actually accepts it
    (paginated=True). Telling a model to retry with a parameter the schema
    rejects makes the truncation disclosed but not recoverable, which is worse
    than saying nothing -- it burns a turn on a call that cannot succeed.
    """
    n = len(items)
    total = getattr(items, "total", None)
    if total is None:
        return f"Found {n} {noun}"
    start = int(offset or 0)
    end = start + n
    if start == 0 and end >= total:
        return f"Found {n} {noun}"
    if end >= total:
        return f"Found {n} of {total} {noun} (rows {start + 1}-{end}; end of results)"
    how = (
        f"pass offset={end} for the next page"
        if paginated
        else "narrow the query with filters, or use count_objects for totals"
    )
    return f"Found {n} of {total} {noun} (rows {start + 1}-{end}; {how})"


def pagination_hint(data, shown):
    """Explicit paging metadata for the model: what it got, what exists, how to continue."""
    if not isinstance(data, dict):
        return ""
    total = data.get("count")
    if total is None or total <= shown:
        return ""
    return (
        f"\nShowing {shown} of {total}. "
        f"Pass offset={shown} (and limit) to retrieve the next page, "
        f"or narrow the query with filters.\n"
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
        out = ResultList(data["results"])
        out.total = data.get("count")
        return out
    elif isinstance(data, list):
        return ResultList(data)
    return ResultList()


def fetch_all_results(endpoint, params=None, max_items=MAX_TOTAL_ITEMS):
    """
    Fetch all paginated results from an API endpoint by following 'next' links.

    max_items bounds the fetch for *display* callers, which only show rows.
    Pass max_items=None when the caller computes an aggregate (totals,
    percentages, scores): a partial fetch there does not truncate a list, it
    silently produces a wrong denominator — 'Total Requirements: 200' for a
    500-requirement audit. Bound the output, never the computation.

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

        # CustomLimitOffsetPagination returns `next` as an absolute *path*
        # (e.g. /api/loaded-libraries/?...), while make_get_request prepends
        # API_URL which already carries that prefix -> /api/api/... -> 404.
        # Latent until now because PAGINATE_BY defaults to 5000, so page 2 was
        # rarely reached.
        if API_PATH and next_url.startswith(API_PATH + "/"):
            next_url = next_url[len(API_PATH) :]

        res = make_get_request(next_url, params=current_params)

        if res.status_code != 200:
            error_msg = f"Error: HTTP {res.status_code} - {res.text[:500]}"
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
            # Following `next` to exhaustion can pull an entire register into
            # the model's context; stop at a bound. The notice rides on the
            # list rather than the error slot, which callers treat as fatal.
            if max_items is not None and len(results_list) >= max_items:
                total = data.get("count")
                capped = ResultList(results_list[:max_items])
                capped.total = total
                capped.truncation_note = (
                    f"\nTRUNCATED: showing the first {max_items}"
                    + (f" of {total}" if total else "")
                    + ". Narrow the query with filters to see the rest.\n"
                )
                return capped, None
        # Handle non-paginated response (list)
        elif isinstance(data, list):
            results_list.extend(data)
            next_url = None  # No pagination for list responses
        else:
            error_msg = f"Unexpected API response format: {type(data)}"
            return results_list, error_msg

    return results_list, None
