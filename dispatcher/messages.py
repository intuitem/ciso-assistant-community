import base64
import io
import urllib.parse
from .filtering import process_selector
from s3fs import S3FileSystem

from .settings import API_URL, S3_URL, VERIFY_CERTIFICATE, get_access_token

from loguru import logger

import settings
from utils.api import get_api_headers
import utils.api as api


class MessageRegistry:
    REGISTRY = {}

    def add(self, message):
        self.REGISTRY[message.__name__] = message


message_registry = MessageRegistry()


def get_resource_endpoint(message: dict, resource_endpoint: str | None = None) -> str:
    """
    Determines the resource endpoint from either the function parameter or the message.
    """
    if resource_endpoint is None:
        resource_endpoint = message.get("resource")
        if resource_endpoint is None:
            raise Exception(
                "No resource endpoint provided. Provide via function parameter or message 'resource' key."
            )
    return resource_endpoint


def extract_update_data(message: dict) -> tuple[dict, dict]:
    """
    Extracts and validates the selector and update values from the message.
    Returns a tuple of (selector, values).
    """
    selector = message.get("selector", {})
    values = message.get("values", {})

    if not values:
        raise Exception("No update values provided in the message.")

    if not selector:
        raise Exception("No selector provided.")

    return selector, values


def get_object_ids(
    selector: dict,
    resource_endpoint: str,
    selector_mapping: dict[str, str] | None = None,
) -> list:
    """
    Uses the selector to query the API and return a list of object IDs.
    """
    if selector_mapping is None:
        selector_mapping = {}

    search_endpoint = f"{API_URL}/{resource_endpoint}/"
    result = process_selector(
        selector,
        selector_mapping=selector_mapping,
        endpoint=search_endpoint,
        token=str(get_access_token()),
        verify_certificate=VERIFY_CERTIFICATE,
    )

    if result is None:
        logger.error(
            "Selector query returned no ids",
            selector=selector,
            endpoint=search_endpoint,
        )
        raise Exception("No objects matched the provided selector.")
    return result if isinstance(result, list) else [result]


def update_single_object(resource_endpoint: str, obj_id: str, values: dict) -> dict:
    """
    Updates a single object using a PATCH request and returns the updated object.
    """
    patch_url = f"{API_URL}/{resource_endpoint}/{obj_id}/"

    logger.debug(f"Updating {resource_endpoint} {obj_id}", values=values)

    res = api.patch(
        patch_url,
        json=values,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Token {get_access_token()}",
        },
        verify=VERIFY_CERTIFICATE,
    )

    if res.status_code not in [200, 204]:
        logger.error(
            f"Failed to update {resource_endpoint} {obj_id}: {res.status_code}",
            response=res.text,
        )
        raise Exception(
            f"Failed to update {resource_endpoint} {obj_id}: {res.status_code}, {res.text}"
        )

    logger.success(
        f"Successfully updated object {obj_id}",
        resource=resource_endpoint,
        response=res.json() if res.text else {"id": obj_id, **values},
    )
    # Return JSON response if available, else construct a dict with the provided values.
    return res.json() if res.text else {"id": obj_id, **values}


def update_objects(
    message: dict,
    resource_endpoint: str | None = None,
    selector_mapping: dict[str, str] | None = None,
) -> list:
    """
    Generic function to update an object.

    Args:
        message (dict): The update message which must include:
            - "values" (dict): The fields and values to update.
            - "selector" (dict): A dictionary of key/value pairs to select object(s).
            - Optionally, "resource": the resource endpoint (e.g. "applied-controls")
              if not provided via the function parameter.
        resource_endpoint (str, optional): The API resource endpoint (e.g., "applied-controls").
            If not provided, the function will look for a "resource" key in the message.
        selector_mapping (dict, optional): Mapping rules for selectors if needed.

    Returns:
        list: A list containing the responses for the updated objects.

    Raises:
        Exception: If no selector is provided, or if the update fails.
    """
    if selector_mapping is None:
        selector_mapping = {}

    # Determine resource endpoint
    resource_endpoint = get_resource_endpoint(message, resource_endpoint)

    # Extract update data (selector and values)
    selector, values = extract_update_data(message)

    # Retrieve object IDs to update using the selector
    object_ids = get_object_ids(selector, resource_endpoint, selector_mapping)

    updated_objects = []

    logger.info("Updating objects", resource=resource_endpoint, ids=object_ids)

    # Process each update
    for obj_id in object_ids:
        updated_obj = update_single_object(resource_endpoint, obj_id, values)
        updated_objects.append(updated_obj)

    logger.success(
        "Successfully updated objects", resource=resource_endpoint, ids=object_ids
    )

    return updated_objects


def update_applied_control(message: dict):
    return update_objects(message, "applied-controls")


def update_requirement_assessment(message: dict):
    return update_objects(message, "requirement-assessments")


def get_file_from_message(values: dict) -> tuple[str, io.IOBase]:
    """
    Determines how to load the file.
    If a base64 encoded content is provided under 'file_content', it decodes it.
    If S3 details are provided (i.e. 'file_s3_bucket'), it opens the file from S3.
    """
    file_name = values.get("file_name")
    if not file_name:
        logger.error("No file_name provided")
        raise Exception("No file_name provided")

    if "file_content" in values:
        file_content_b64 = values.get("file_content")
        if not file_content_b64:
            logger.error("No file_content provided")
            raise Exception("No file_content provided")
        file_content = base64.b64decode(file_content_b64)
        in_memory_file = io.BytesIO(file_content)
        logger.info("Loaded file from base64 encoded content", file_name=file_name)
        return file_name, in_memory_file

    elif "file_s3_bucket" in values:
        s3 = S3FileSystem(
            anon=False,
            endpoint_url=S3_URL,
            key=settings.S3_ACCESS_KEY,
            secret=settings.S3_SECRET_KEY,
        )
        bucket = values["file_s3_bucket"]
        key = file_name
        file_path = f"{bucket}/{key}"
        try:
            in_memory_file = s3.open(file_path, "rb")
        except Exception as e:
            logger.error(
                "Failed to open file from S3", bucket=bucket, key=key, error=str(e)
            )
            raise Exception(f"Failed to open file from S3: {e}") from e
        logger.info("Loaded file from S3", file_name=file_name, bucket=bucket, key=key)
        return file_name, in_memory_file

    else:
        logger.error(
            "No valid file source provided. Provide base64 file content or S3 bucket and key."
        )
        raise Exception(
            "No valid file source provided. Provide base64 file content or S3 bucket and key."
        )


def get_or_create(resource: str, selector: dict, values: dict, name: str) -> str:
    """
    Either finds an existing object using a selector or creates a new object.
    """
    objects_endpoint = f"{API_URL}/{resource}/"
    if selector:
        logger.info("Using provided selector to find object", selector=selector)
        selector["target"] = "single"
        object_ids = get_object_ids(selector, resource)
        if not object_ids:
            logger.error(
                "No object found for the provided selector.", selector=selector
            )
            raise Exception("No object found for the provided selector.")
        object_id = object_ids[0]
        logger.info("Found object", object_id=object_id)
    else:
        logger.info("Creating new object with name: {}", name, values=values)
        response = api.post(
            objects_endpoint,
            data={"name": values.get("name", name)},
            headers={"Authorization": f"Token {get_access_token()}"},
            verify=VERIFY_CERTIFICATE,
        )
        if not response.ok:
            logger.error(
                "Failed to create object",
                status_code=response.status_code,
                response=response.text,
            )
            raise Exception(
                f"Failed to create object: {response.status_code}, {response.text}"
            )
        data = response.json()
        object_id = data["id"]
        logger.info("Created object", object_id=object_id, object=data)
    return object_id


def upload_file_to_evidence(
    evidence_id: str, file_name: str, file_obj: io.IOBase
) -> None:
    """
    Uploads the file to the evidence upload endpoint.
    """
    extra_headers = {
        "Content-Disposition": f"attachment; filename={urllib.parse.quote(file_name)}",
    }
    endpoint = f"{API_URL}/evidences/{evidence_id}/upload/"
    logger.info(
        "Uploading attachment to evidence", evidence_id=evidence_id, file_name=file_name
    )
    response = api.post(
        endpoint,
        headers=get_api_headers(extra_headers=extra_headers),
        data=file_obj.read(),
        verify=VERIFY_CERTIFICATE,
    )
    if not response.ok:
        logger.error(
            "Failed to upload attachment to evidence",
            evidence_id=evidence_id,
            status_code=response.status_code,
            response=response.text,
            request_headers=response.request.headers,
            endpoint=endpoint,
        )
        raise Exception(
            f"Failed to update evidence {evidence_id}: {response.status_code}, {response.text}"
        )
    logger.success(
        "Uploaded attachment to evidence", evidence_id=evidence_id, file_name=file_name
    )


def update_applied_controls_with_evidence(
    values: dict, evidence_id: str, file_name: str
) -> None:
    """
    If applied controls are provided in the values, update each with the new evidence.
    """
    applied_controls_selector: dict = values.get("applied_controls", {})
    if applied_controls_selector:
        logger.info(
            "Updating applied controls with evidence",
            selector=applied_controls_selector,
        )
        applied_controls = get_object_ids(applied_controls_selector, "applied-controls")
        if not applied_controls:
            logger.error(
                "No applied controls found for the provided selector.",
                selector=applied_controls_selector,
            )
            raise Exception("No applied controls found for the provided selector.")
        for control in applied_controls:
            control_endpoint = f"{API_URL}/applied-controls/{control}/"
            get_response = api.get(
                control_endpoint,
                headers={"Authorization": f"Token {get_access_token()}"},
                verify=VERIFY_CERTIFICATE,
            )
            control_data = get_response.json()
            evidences = control_data.get("evidences", [])
            logger.info(
                "Attaching evidence to applied control",
                control=control_data,
                evidence=evidence_id,
            )
            update_response = api.patch(
                control_endpoint,
                json={"evidences": [e.get("id") for e in evidences] + [evidence_id]},
                headers={"Authorization": f"Token {get_access_token()}"},
                verify=VERIFY_CERTIFICATE,
            )
            if not update_response.ok:
                logger.error(
                    "Failed to update applied control",
                    control=control,
                    response=update_response.text,
                )
                raise Exception(
                    f"Failed to update applied control {control}: {update_response.status_code}, {update_response.text}"
                )
            logger.success(
                "Updated applied control",
                control=control,
                response=update_response.json(),
            )
        logger.success(
            "Successfully updated applied controls with evidence",
            applied_controls=applied_controls,
            evidence=evidence_id,
            file_name=file_name,
        )


def upload_attachment(message: dict):
    """
    Main function to process attachment upload.
    Determines file source (base64 or S3), creates or finds the related evidence,
    uploads the file, and then updates applied controls if provided.
    """
    selector = message.get("selector", {})
    values = message.get("values", {})

    # Load file from provided source (base64 or S3)
    file_name, file_obj = get_file_from_message(values)

    # Get or create the evidence and upload the file
    evidence_id = get_or_create("evidences", selector, values, file_name)
    upload_file_to_evidence(evidence_id, file_name, file_obj)

    # Update applied controls if any
    update_applied_controls_with_evidence(values, evidence_id, file_name)


message_registry.add(update_applied_control)
message_registry.add(update_requirement_assessment)
message_registry.add(upload_attachment)
