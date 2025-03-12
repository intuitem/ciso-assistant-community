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
    Update the status of an applied control.

    If a selector is provided in the message, the API will be queried to determine the applied_control_id(s).
    For 'single' target, a single object's ID is returned; for 'multiple' target, a list of IDs is returned.
    In the case of multiple IDs, the function will update all matching applied controls.
    """
    new_status = message.get("new_status")
    applied_control_id = message.get("applied_control_id")
    selector = message.get("selector")
    updated_objects = []

    # If a selector is provided, use it to determine the applied_control_id(s)
    if selector:
        search_endpoint = f"{API_URL}/applied-controls/"
        result = process_selector(selector, search_endpoint, TOKEN, VERIFY_CERTIFICATE)
        if isinstance(result, list):
            applied_control_ids = result
        else:
            applied_control_ids = [result]
    else:
        if not applied_control_id:
            raise Exception("No applied_control_id provided and no selector available.")
        applied_control_ids = [applied_control_id]

    # Process each applied control update
    for ac_id in applied_control_ids:
        patch_url = f"{API_URL}/applied-controls/{ac_id}/"
        data = json.dumps({"status": new_status})
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
                f"Failed to update applied control {ac_id}: {res.status_code}, {res.text}"
            )

        updated_objects.append(
            res.json() if res.text else {"id": ac_id, "status": new_status}
        )

    return updated_objects


event_registry.add(update_applied_control)
