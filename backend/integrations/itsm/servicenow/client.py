from typing import Any, Dict, List
import requests
from structlog import get_logger
from integrations.models import SyncMapping
from core.models import AppliedControl
from integrations.base import BaseIntegrationClient
from .mapper import ServiceNowFieldMapper

logger = get_logger(__name__)


class ServiceNowClient(BaseIntegrationClient):
    def __init__(self, configuration):
        super().__init__(configuration)
        self.base_url = self.credentials["instance_url"].rstrip("/")
        self.auth = (self.credentials["username"], self.credentials["password"])
        # Default to 'incident' if not specified, but for AppliedControl likely 'sn_compliance_control' or custom
        self.table = self.settings.get("table_name", "incident")
        self.mapper = ServiceNowFieldMapper(configuration)

    def _get_headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def create_remote_object(self, local_object: AppliedControl) -> str:
        """Creates a record in ServiceNow and returns the sys_id."""
        payload = self.mapper.to_remote(local_object)

        url = f"{self.base_url}/api/now/table/{self.table}"

        try:
            response = requests.post(
                url,
                auth=self.auth,
                headers=self._get_headers(),
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json().get("result", {})

            sys_id = result.get("sys_id")
            number = result.get("number")

            logger.info(f"Created ServiceNow record {number} ({sys_id})")

            # Optional: Update the local ref_id with the human-readable number immediately
            # This depends on your specific flow, but it's often useful.
            # local_object.ref_id = number
            # local_object.save(update_fields=['ref_id'])

            return sys_id

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to create ServiceNow record: {e.response.text if e.response else e}"
            )
            raise

    def update_remote_object(self, remote_id: str, changes: dict[str, Any]) -> bool:
        """Updates a record. Unlike Jira, we can usually update State directly here."""
        if not changes:
            return False

        url = f"{self.base_url}/api/now/table/{self.table}/{remote_id}"

        try:
            response = requests.patch(
                url,
                auth=self.auth,
                headers=self._get_headers(),
                json=changes,
                timeout=30,
            )
            response.raise_for_status()
            logger.info(
                f"Updated ServiceNow record {remote_id}: {list(changes.keys())}"
            )
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update ServiceNow record {remote_id}: {e}")
            raise

    def get_remote_object(self, remote_id: str) -> Dict[str, Any]:
        """Fetches a record by sys_id."""
        url = f"{self.base_url}/api/now/table/{self.table}/{remote_id}"

        try:
            response = requests.get(
                url, auth=self.auth, headers=self._get_headers(), timeout=30
            )
            response.raise_for_status()
            result = response.json().get("result", {})
            return {
                "key": result.get("sys_id"),  # internal ID
                "number": result.get("number"),  # human ID
                "fields": result,  # ServiceNow returns flat structure, unlike Jira's nested 'fields'
                "updated": result.get("sys_updated_on"),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch ServiceNow record {remote_id}: {e}")
            raise

    def list_remote_objects(
        self, query_params: dict[str, Any] | None = None
    ) -> List[dict[str, Any]]:
        if query_params is None:
            query_params = {}

        # Build Encoded Query
        # Example: active=true^sys_updated_on>=2024-01-01
        sysparm_query = self.settings.get("base_query", "active=true")

        url = f"{self.base_url}/api/now/table/{self.table}"
        params = {
            "sysparm_query": sysparm_query,
            "sysparm_fields": "sys_id,number,short_description,sys_updated_on",
            "sysparm_limit": query_params.get("max_results", 100),
        }

        try:
            used_ids = SyncMapping.objects.filter(
                configuration=self.configuration
            ).values_list("remote_id", flat=True)

            response = requests.get(
                url,
                auth=self.auth,
                headers=self._get_headers(),
                params=params,
                timeout=30,
            )
            response.raise_for_status()

            results = []
            for record in response.json().get("result", []):
                if record["sys_id"] not in used_ids:
                    results.append(
                        {
                            "key": record["sys_id"],  # The ID we sync on
                            "id": record["sys_id"],
                            "summary": f"{record.get('number')} - {record.get('short_description')}",
                        }
                    )
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search ServiceNow: {e}")
            raise

    def test_connection(self) -> bool:
        try:
            # Just try to fetch 1 record to validate auth and table existence
            url = f"{self.base_url}/api/now/table/{self.table}"
            params = {"sysparm_limit": 1}
            response = requests.get(
                url, auth=self.auth, headers=self._get_headers(), params=params
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"ServiceNow connection test failed: {e}")
            return False
