import json
from filtering import process_selector

import requests

from settings import API_URL, TOKEN, VERIFY_CERTIFICATE


class EventRegistry:
    REGISTRY = {}

    def add(self, event):
        self.REGISTRY[event.__name__] = event


event_registry = EventRegistry()


def update_applied_control(message: dict):
    """
    Update an applied control.

    If a selector is provided in the message, the API will be queried to determine the applied_control_id(s).
    For 'single' target, a single object's ID is returned; for 'multiple' target, a list of IDs is returned.
    In the case of multiple IDs, the function will update all matching applied controls.
    """
    object_id: str = message.get("object_id", "")
    selector: dict = message.get("selector", {})
    values: dict = message.get("values", {})

    updated_objects = []

    if selector:
        search_endpoint = f"{API_URL}/applied-controls/"
        result = process_selector(selector, search_endpoint, TOKEN, VERIFY_CERTIFICATE)
        if isinstance(result, list):
            object_ids = result
        else:
            object_ids = [result]
    else:
        if not object_id:
            raise Exception("No applied_control_id provided and no selector available.")
        object_ids = [object_id]

    # Process each applied control update
    # NOTE: We should expose endpoints for bulk updates to speed this up
    for id in object_ids:
        patch_url = f"{API_URL}/applied-controls/{id}/"
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
                f"Failed to update applied control {id}: {res.status_code}, {res.text}"
            )

        updated_objects.append(res.json() if res.text else {"id": id, **values})

    return updated_objects


event_registry.add(update_applied_control)
