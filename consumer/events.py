import json
from filtering import process_selector

import requests

from settings import API_URL, TOKEN, VERIFY_CERTIFICATE


class EventRegistry:
    REGISTRY = {}

    def add(self, event):
        self.REGISTRY[event.__name__] = event


event_registry = EventRegistry()


def update_object(message: dict, resource_endpoint: str = None):
    """
    Generic function to update an object.

    Args:
        message (dict): The update message which must include:
            - "values" (dict): The fields and values to update.
            - Optionally, "selector": a list of key/value pairs to select object(s).
            - Optionally, "resource": the resource endpoint (e.g. "applied-controls")
              if not provided via the function parameter.
        resource_endpoint (str, optional): The API resource endpoint (e.g., "applied-controls").
            If not provided, the function will look for a "resource" key in the message.

    Returns:
        list: A list containing the responses for the updated objects.

    Raises:
        Exception: If no selector is provided, or if the update fails.
    """
    # Determine resource endpoint
    if resource_endpoint is None:
        resource_endpoint = message.get("resource")
        if resource_endpoint is None:
            raise Exception(
                "No resource endpoint provided. Provide via function parameter or message 'resource' key."
            )

    selector = message.get("selector", {})
    values = message.get("values", {})

    if not values:
        raise Exception("No update values provided in the message.")

    updated_objects = []

    # Determine which object(s) to update based on selector.
    if not selector:
        raise Exception("No selector provided.")

    search_endpoint = f"{API_URL}/{resource_endpoint}/"
    result = process_selector(selector, search_endpoint, TOKEN, VERIFY_CERTIFICATE)
    if isinstance(result, list):
        object_ids = result
    else:
        object_ids = [result]

    # Process each update
    for obj_id in object_ids:
        patch_url = f"{API_URL}/{resource_endpoint}/{obj_id}/"
        data = json.dumps(values)
        res = requests.patch(
            patch_url,
            data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Token {TOKEN}",
            },
            verify=VERIFY_CERTIFICATE,
        )

        if res.status_code not in [200, 204]:
            raise Exception(
                f"Failed to update {resource_endpoint} {obj_id}: {res.status_code}, {res.text}"
            )

        updated_objects.append(res.json() if res.text else {"id": obj_id, **values})

    return updated_objects


def update_applied_control(message: dict):
    return update_object(message, "applied-controls")


def update_requirement_assessment(message: dict):
    return update_object(message, "requirement-assessments")


event_registry.add(update_applied_control)
event_registry.add(update_requirement_assessment)
