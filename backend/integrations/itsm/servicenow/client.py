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
        self.base_url = self.credentials.get("instance_url", "").rstrip("/")
        username = self.credentials.get("username", "")
        password = self.credentials.get("password", "")
        self.auth = (username, password)
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

        logger.info("Attempting to create ServiceNow record", payload=payload)

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

            logger.info("Created ServiceNow record", number=number, sys_id=sys_id)

            # Optional: Update the local ref_id with the human-readable number immediately
            # This depends on your specific flow, but it's often useful.
            # local_object.ref_id = number
            # local_object.save(update_fields=['ref_id'])

            return sys_id

        except requests.exceptions.RequestException:
            logger.error(
                "Failed to create ServiceNow record", payload=payload, exc_info=True
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

    def get_available_tables(self) -> list[dict]:
        """
        Fetches 'user-facing' tables (Incidents, Controls, etc).
        Aggressively filters out system internals, import sets, and link tables.
        """
        # Noise filters:
        # imp_  -> Import Sets (Temporary data buffers, usually hundreds of them)
        # m2m_  -> Many-to-Many link tables (Internal relationship storage)
        # sys_  -> System tables (Metadata)
        # ts_   -> Text Search indices
        # v_    -> Database Views
        # var_  -> Variables (Service Catalog internals)
        # wf_   -> Workflow contexts
        # pa_   -> Performance Analytics
        # ecc_  -> External Communication Channel (Queue)
        # metric_ -> Metric definitions
        # etc.

        exclusions = [
            "nameNOT LIKEsys_",
            "nameNOT LIKEts_",
            "nameNOT LIKEv_",
            "nameNOT LIKEimp_",
            "nameNOT LIKEm2m",  # Catch m2m_ and ..._m2m
            "nameNOT LIKEvar_",
            "nameNOT LIKEwf_",
            "nameNOT LIKEpa_",
            "nameNOT LIKEecc_",
            "nameNOT LIKEmetric_",
            "nameNOT LIKEais_",
            "nameNOT LIKEsyslog_",
            "nameNOT LIKEsysevent_",
            "nameNOT LIKEsn_",
            "nameNOT LIKEprotected_",
            "nameNOT LIKEml_",
            "nameNOT LIKEexpert_panel",
            "nameNOT LIKEua_",
            "nameNOT LIKEusageanalytics_",
            "nameNOT LIKEautomation_pipeline_",
            "nameNOT LIKEcdc_",
            "nameNOT LIKEcmn_",
            "nameNOT LIKEcxs_",
            "nameNOT LIKEdiscovery_",
            "nameNOT LIKEhermes_",
            "nameNOT LIKEip_",
            "nameNOT LIKElicense_",
            "nameNOT LIKElicensing_",
            "nameNOT LIKEnlq_",
            "nameNOT LIKEnlu_",
            "nameNOT LIKEoauth_",
            "nameNOT LIKEoidc_",
            "nameNOT LIKEopen_nlu_predict_",
            "nameNOT LIKEpar_",
            "nameNOT LIKEproactive_analytics_",
            "nameNOT LIKEpromin_",
            "nameNOT LIKEproposed_change_verification_",
            "nameNOT LIKEpwd_",
            "nameNOT LIKEqb_",
            "nameNOT LIKEsc_cart_",
            "nameNOT LIKEsc_cat_",
            "nameNOT LIKEsc_catalog_",
            "nameNOT LIKEsc_category_",
            "nameNOT LIKEsc_item_",
            "nameNOT LIKEsc_layout_",
            "nameNOT LIKEsc_service_",
            "nameNOT LIKEsc_wizard_",
            "nameNOT LIKEscan_log_",
            "nameNOT LIKEscan_mute_",
            "nameNOT LIKEsla_repair_",
            "nameNOT LIKEstagemgmt_",
            "nameNOT LIKEsysevent",
            "nameNOT LIKEsyslog",
        ]

        # Combine with OR operator logic if needed, but here we need AND logic (exclusion)
        # In ServiceNow query syntax, separating with ^ acts as AND.

        # 'sys_update_nameISNOTEMPTY' ensures the table is a tracked system object (excludes some temp tables)
        base_query = "sys_update_nameISNOTEMPTY"

        query = f"{base_query}^{'^'.join(exclusions)}"

        url = f"{self.base_url}/api/now/table/sys_db_object"
        params = {
            "sysparm_query": query,
            "sysparm_fields": "name,label",
            "sysparm_limit": 5000,  # Safety limit
            "sysparm_exclude_reference_link": "true",
        }

        try:
            response = requests.get(
                url,
                auth=self.auth,
                headers=self._get_headers(),
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            results = response.json().get("result", [])

            # Sort by Label for UX
            return sorted(results, key=lambda x: x.get("label", ""))

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch tables: {e}")
            raise

    def get_table_columns(self, table_name: str) -> list[dict]:
        """
        Fetches columns for a table AND its parents (e.g., incident -> task).
        Recursively walks up the sys_db_object inheritance tree.
        """
        columns_map = {}  # Use a dict to handle overrides (child hides parent)
        current_table = table_name

        while current_table:
            # 1. Fetch fields for the current level
            self._fetch_fields_for_single_table(current_table, columns_map)

            # 2. Find the parent table
            parent_table = self._get_parent_table(current_table)

            # 3. Move up or stop
            if (
                parent_table
                and parent_table != "sys_metadata"
                and parent_table != "cmdb"
            ):
                current_table = parent_table
            else:
                current_table = None

        # Convert back to list and sort
        return sorted(columns_map.values(), key=lambda x: x["label"])

    def _get_parent_table(self, table_name: str) -> str | None:
        """Helper to find the super_class (parent) of a table."""
        url = f"{self.base_url}/api/now/table/sys_db_object"
        params = {
            "sysparm_query": f"name={table_name}",
            "sysparm_fields": "super_class",
            "sysparm_limit": 1,
        }
        try:
            resp = requests.get(
                url, auth=self.auth, headers=self._get_headers(), params=params
            )
            resp.raise_for_status()
            result = resp.json().get("result", [])
            if result and result[0].get("super_class"):
                # super_class returns a link object: {"link": "...", "value": "sys_id"}
                # We need to fetch the name of that parent, but the API gives us a link.
                # Optimization: It's often faster to just query sys_db_object by sys_id
                # or rely on a known cache, but let's do the robust lookup.

                parent_id = result[0]["super_class"]["value"]
                return self._get_table_name_by_id(parent_id)
            return None
        except Exception:
            return None

    def _get_table_name_by_id(self, sys_id: str) -> str | None:
        """Resolves a table sys_id to its name (e.g., 'task')."""
        url = f"{self.base_url}/api/now/table/sys_db_object/{sys_id}"
        params = {"sysparm_fields": "name"}
        try:
            resp = requests.get(
                url, auth=self.auth, headers=self._get_headers(), params=params
            )
            if resp.status_code == 200:
                return resp.json().get("result", {}).get("name")
        except Exception:
            logger.warning("Failed to resolve table name for sys_id", sys_id=sys_id)
            return None
        return None

    def _fetch_fields_for_single_table(self, table_name: str, columns_map: dict):
        """Fetches fields for one table and merges them into the map (child wins)."""
        url = f"{self.base_url}/api/now/table/sys_dictionary"
        query = f"name={table_name}^active=true^elementISNOTEMPTY"
        params = {
            "sysparm_query": query,
            "sysparm_fields": "element,column_label,internal_type,read_only,reference",
            "sysparm_exclude_reference_link": "true",
        }

        try:
            response = requests.get(
                url,
                auth=self.auth,
                headers=self._get_headers(),
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            results = response.json().get("result", [])

            for r in results:
                col_name = r.get("element")
                # Only add if not already present (Child fields processed first take precedence)
                if col_name not in columns_map:
                    columns_map[col_name] = {
                        "name": col_name,
                        "label": r.get("column_label"),
                        "type": r.get("internal_type"),
                        "readonly": r.get("read_only") == "true",
                        "reference": r.get("reference"),
                    }
        except Exception as e:
            logger.error(f"Failed to fetch columns for {table_name}: {e}")

    def get_field_choices(self, table_name: str, field_name: str) -> list[dict]:
        """
        Fetches choice values by walking up the table hierarchy.
        Example: If asking for 'incident.priority', it checks 'incident', then 'task'.
        """
        current_table = table_name

        # Prevent infinite loops or deep dives into abstract system tables
        # 'cmdb' and 'sys_metadata' are good stopping points for ITSM/GRC
        while current_table and current_table not in ["sys_metadata", "cmdb"]:
            choices = self._fetch_choices_for_single_table(current_table, field_name)

            # If we found choices at this level, return them immediately.
            # ServiceNow logic: A child table's choice list overrides the parent's entirely.
            if choices:
                return choices

            # Not found? Move up to the parent (e.g., incident -> task)
            current_table = self._get_parent_table(current_table)

        return []

    def _fetch_choices_for_single_table(
        self, table_name: str, field_name: str
    ) -> list[dict]:
        """Helper to hit the API for a specific table/field combination."""
        url = f"{self.base_url}/api/now/table/sys_choice"
        # inactive=false ensures we don't get deprecated options
        query = f"name={table_name}^element={field_name}^inactive=false"

        params = {
            "sysparm_query": query,
            "sysparm_fields": "value,label,sequence",
            "sysparm_order": "sequence",
            "sysparm_exclude_reference_link": "true",
        }

        try:
            response = requests.get(
                url,
                auth=self.auth,
                headers=self._get_headers(),
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            results = response.json().get("result", [])

            return [{"value": r["value"], "label": r["label"]} for r in results]

        except Exception as e:
            logger.warning(f"Error fetching choices for {table_name}.{field_name}: {e}")
            return []

    def test_connection(self) -> bool:
        try:
            # Just try to fetch 1 record to validate auth and table existence
            url = f"{self.base_url}/api/now/table/{self.table}"
            params = {"sysparm_limit": 1}
            response = requests.get(
                url,
                auth=self.auth,
                headers=self._get_headers(),
                params=params,
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"ServiceNow connection test failed: {e}")
            return False
