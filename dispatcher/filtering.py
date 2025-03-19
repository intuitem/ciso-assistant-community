import requests
from loguru import logger


def process_selector(
    selector: dict[str, str],
    endpoint: str,
    token: str,
    selector_mapping: dict[str, str] | None = None,
    verify_certificate: bool = True,
):
    """
    Process a selector to filter objects from the API that uses LimitOffsetPagination.

    Args:
        selector (list): List of dictionaries with key-value pairs. Expected keys include 'domain', 'ref_id',
                         and optionally 'target' (default: 'single').
        endpoint (str): The API endpoint URL to query for objects.
        token (str): API token for authentication.
        selector_mapping (dict): Mapping of selector keys to the API filterset fields.
        verify_certificate (bool): Whether to verify the TLS certificate.

    Returns:
        For 'single' target: a single object ID (string).
        For 'multiple' target: a list of object IDs.

    Raises:
        Exception: If the API call fails, the response is not as expected, or if the result count
                   does not match the expected target.
    """
    if selector_mapping is None:
        selector_mapping = {}

    target = selector.pop("target", "single")

    if selector_mapping:
        for key, value in selector.items():
            if key in selector_mapping:
                selector[selector_mapping[key]] = selector.pop(key)

    query_params = selector

    headers = {
        "Accept": "application/json",
        "Authorization": f"Token {token}",
    }

    # Retrieve all paginated results
    results_list = []
    next_url = endpoint
    while next_url:
        response = requests.get(
            next_url,
            params=query_params if next_url == endpoint else {},
            headers=headers,
            verify=verify_certificate,
        )
        if not response.ok:
            logger.exception(
                "Search failed",
                status_code=response.status_code,
                response=response.text,
            )
            raise Exception(
                f"Search API call failed with status {response.status_code}: {response.text}"
            )

        data = response.json()
        if isinstance(data, dict) and "results" in data:
            results = data.get("results", [])
            results_list.extend(results)
            next_url = data.get("next")
        elif isinstance(data, list):
            results_list = data
            next_url = None
        else:
            logger.exception("Unexpected API response format", response=data)
            raise Exception("Unexpected API response format")

    if target == "single":
        if len(results_list) != 1:
            logger.exception(
                "Expected a single object, but got {} objects",
                len(results_list),
                results=results_list,
            )
            raise Exception(
                f"Expected a single object, but got {len(results_list)} objects."
            )
        return results_list[0].get("id")
    elif target == "multiple":
        if len(results_list) == 0:
            raise Exception("No objects returned for the selector.")
        return [item.get("id") for item in results_list]
    else:
        raise Exception(f"Unknown target specified in selector: {target}")
