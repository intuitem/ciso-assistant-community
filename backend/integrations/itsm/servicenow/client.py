import re
from typing import Any, Dict, List
import requests
from django.core.exceptions import ObjectDoesNotExist
from structlog import get_logger
from integrations.models import SyncMapping
from core.models import AppliedControl
from core.net_safety import check_integration_url
from integrations.base import BaseIntegrationClient
from .mapper import ServiceNowFieldMapper

logger = get_logger(__name__)

# ServiceNow sys_ids are 32-char hex GUIDs; accept alphanumeric only so no
# encoded-query metacharacter can pass through hydration.
SYS_ID_PATTERN = re.compile(r"[0-9a-zA-Z]{1,64}")

# Each hydration id is user-supplied; the picker only hydrates selected
# values, so a handful is plenty.
MAX_HYDRATION_IDS = 20

# Ceiling on total rows scanned per list call while paging past
# already-mapped records that get filtered out of the results.
MAX_LIST_FETCH = 500

# Rows requested per page while scanning.
LIST_PAGE_SIZE = 100

# Deterministic global ordering for offset pagination: newest first, with the
# immutable sys_id as tiebreaker (sys_updated_on would reshuffle pages when a
# record is touched mid-scan). ORDERBY tokens apply to the whole encoded
# query wherever they appear, ^NQ branches included; an ORDERBY an admin put
# in base_query simply becomes the primary sort with these as tiebreakers.
LIST_ORDERING = "ORDERBYDESCsys_created_on^ORDERBYsys_id"

# Rows requested per page when listing sys_db_object.
TABLES_PAGE_SIZE = 1000

# Ceiling on sys_db_object rows scanned when listing tables. Large instances
# carry several thousand tables; this only guards against a runaway loop.
MAX_TABLES_FETCH = 50000

# Table name prefixes hidden from the table picker as noise:
# sys_ (metadata), ts_ (text search), v_ (views), imp_ (import sets),
# var_ (catalog variables), wf_ (workflow contexts), pa_ (performance
# analytics), ecc_ (queue), metric_ (metric definitions), and so on.
# sn_ is deliberately absent: it is the namespace of every scoped Store app
# (Customer Service, Security Incident Response, GRC/IRM, HR...).
EXCLUDED_TABLE_PREFIXES = (
    "sys_",
    "sysevent",
    "syslog",
    "ts_",
    "v_",
    "imp_",
    "var_",
    "wf_",
    "pa_",
    "ecc_",
    "metric_",
    "ais_",
    "protected_",
    "ml_",
    "expert_panel",
    "ua_",
    "usageanalytics_",
    "automation_pipeline_",
    "cdc_",
    "cmn_",
    "cxs_",
    "discovery_",
    "hermes_",
    "ip_",
    "license_",
    "licensing_",
    "nlq_",
    "nlu_",
    "oauth_",
    "oidc_",
    "open_nlu_predict_",
    "par_",
    "proactive_analytics_",
    "promin_",
    "proposed_change_verification_",
    "pwd_",
    "qb_",
    "sc_cart_",
    "sc_cat_",
    "sc_catalog_",
    "sc_category_",
    "sc_item_",
    "sc_layout_",
    "sc_service_",
    "sc_wizard_",
    "scan_log_",
    "scan_mute_",
    "sla_repair_",
    "stagemgmt_",
)


def is_excluded_table(name: str) -> bool:
    # Link tables come as both m2m_* and *_m2m*.
    return name.startswith(EXCLUDED_TABLE_PREFIXES) or "m2m" in name


class ServiceNowClient(BaseIntegrationClient):
    def __init__(self, configuration, model_key="applied_control"):
        super().__init__(configuration, model_key)
        self.base_url = self.credentials.get("instance_url", "").rstrip("/")
        try:
            check_integration_url(self.base_url, "ServiceNow instance_url")
        except ValueError:
            logger.error("ServiceNow instance_url blocked by SSRF guard", exc_info=True)
            raise
        username = self.credentials.get("username", "")
        password = self.credentials.get("password", "")
        self.auth = (username, password)
        # Per-model target table (e.g. 'incident' for controls, a CMDB table for
        # assets). Defaults to 'incident' when unset.
        self.table = self.model_settings.get("table_name", "incident")
        self.mapper = ServiceNowFieldMapper(configuration, model_key)

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
                allow_redirects=False,
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
                allow_redirects=False,
            )
            response.raise_for_status()
            logger.info(
                "Updated ServiceNow record",
                remote_id=remote_id,
                changed_fields=list(changes.keys()),
            )
            return True
        except requests.exceptions.RequestException:
            logger.error(
                "Failed to update ServiceNow record",
                remote_id=remote_id,
                changed_fields=list(changes.keys()),
                exc_info=True,
            )
            raise

    def get_remote_object(self, remote_id: str) -> Dict[str, Any]:
        """Fetches a record by sys_id."""
        url = f"{self.base_url}/api/now/table/{self.table}/{remote_id}"

        try:
            response = requests.get(
                url,
                auth=self.auth,
                headers=self._get_headers(),
                timeout=30,
                allow_redirects=False,
            )
            response.raise_for_status()
            result = response.json().get("result", {})
            return {
                "key": result.get("sys_id"),  # internal ID
                "number": result.get("number"),  # human ID
                "fields": result,  # ServiceNow returns flat structure, unlike Jira's nested 'fields'
                "updated": result.get("sys_updated_on"),
            }
        except requests.exceptions.RequestException:
            logger.error(
                "Failed to fetch ServiceNow record", remote_id=remote_id, exc_info=True
            )
            raise

    # Candidate fields the picker searches when the user types. Matches the
    # display label sources in ``_display_label``; restricted per table by
    # ``_searchable_fields`` since not every table has all three.
    SEARCH_FIELDS = ("number", "short_description", "name")

    @staticmethod
    def _and_onto_branches(base_query: str, condition: str) -> str:
        """AND ``condition`` onto every top-level ``^NQ`` branch of ``base_query``.

        ``base_query`` is free-form admin config and may itself OR complete
        subqueries with ``^NQ`` (ServiceNow's own filter UI emits it), so
        appending the condition to the string as a whole would leave every
        branch but the last unconstrained, matching its entire scope.
        """
        branches = base_query.split("^NQ")
        return "^NQ".join(
            f"{branch}^{condition}" if branch else condition for branch in branches
        )

    def _searchable_fields(self) -> tuple[str, ...]:
        """``SEARCH_FIELDS`` restricted to columns of the configured table.

        A ``^NQ`` branch on a nonexistent field either matches everything
        (ServiceNow drops invalid conditions by default) or kills the whole
        query (strict mode), so only emit branches for real columns. Resolved
        against the DB-backed schema cache (warmed on startup and by the
        FieldMapper); when the table's columns aren't cached yet, keep all
        candidates, which is the previous behavior.
        """
        try:
            columns = self.configuration.schema_cache.columns.get(self.table)
        except ObjectDoesNotExist:
            return self.SEARCH_FIELDS
        if not columns:
            return self.SEARCH_FIELDS
        names = {c.get("name") for c in columns}
        return tuple(f for f in self.SEARCH_FIELDS if f in names)

    def list_remote_objects(
        self, query_params: dict[str, Any] | None = None
    ) -> List[dict[str, Any]]:
        """List records from the configured table.

        ``query_params`` supports ``search`` (matched against number,
        short_description and name), ``limit`` and ``id`` (comma-separated
        sys_ids to hydrate).
        """
        if query_params is None:
            query_params = {}

        # Build Encoded Query
        # Example: active=true^sys_updated_on>=2024-01-01
        base_query = self.model_settings.get("base_query", "active=true")
        sysparm_query = base_query

        ids = str(query_params.get("id", "") or "")
        search = str(query_params.get("search", "") or "")
        if ids:
            # sys_ids are alphanumeric; drop anything else so a crafted id
            # can't inject encoded-query branches (^, ^NQ, ...) past
            # base_query. Only the server-generated commas delimit the IN.
            id_list = [
                i.strip()
                for i in ids.split(",")
                if i.strip() and SYS_ID_PATTERN.fullmatch(i.strip())
            ][:MAX_HYDRATION_IDS]
            if not id_list:
                return []
            sysparm_query = self._and_onto_branches(
                base_query, f"sys_idIN{','.join(id_list)}"
            )
        elif search:
            # ^ and , are encoded-query metacharacters; LIKE has no escape
            # syntax so strip them from the term.
            term = search.strip().replace("^", "").replace(",", "")
            if not term:
                # The term sanitized down to nothing: it must match nothing,
                # not fall through to the unfiltered base query.
                return []
            search_fields = self._searchable_fields()
            if not search_fields:
                # No searchable column on this table: returning the base
                # query would present unrelated rows as search matches.
                return []
            # ^NQ ORs complete subqueries, so base_query is repeated in
            # each branch; a plain ^OR would escape the base_query AND
            # due to flat left-to-right precedence.
            sysparm_query = "^NQ".join(
                self._and_onto_branches(base_query, f"{field}LIKE{term}")
                for field in search_fields
            )

        used_ids = set(
            SyncMapping.objects.filter(configuration=self.configuration).values_list(
                "remote_id", flat=True
            )
        )

        limit = query_params.get("limit", 100)

        url = f"{self.base_url}/api/now/table/{self.table}"

        # Mapped records are filtered out client-side, so a single fetch
        # cannot tell "few matches" from "page full of mapped records" — the
        # latter would return a short page and silently flip the picker's
        # lazy/eager probe to eager on a truncated list. Keep paging until
        # the page fills or the source (or the MAX_LIST_FETCH scan budget)
        # runs out. Records are deduplicated by sys_id since a row can match
        # more than one ^NQ branch of the query.
        results = []
        seen = set()
        offset = 0
        try:
            while True:
                params = {
                    "sysparm_query": f"{sysparm_query}^{LIST_ORDERING}",
                    # Superset of common display fields so labels work across tables
                    # (incident uses number/short_description, CMDB/asset tables use name).
                    "sysparm_fields": "sys_id,number,name,short_description,sys_updated_on",
                    "sysparm_limit": LIST_PAGE_SIZE,
                    "sysparm_offset": offset,
                }
                response = requests.get(
                    url,
                    auth=self.auth,
                    headers=self._get_headers(),
                    params=params,
                    timeout=30,
                    allow_redirects=False,
                )
                response.raise_for_status()

                records = response.json().get("result", [])
                for record in records:
                    sys_id = record.get("sys_id")
                    if not sys_id or sys_id in seen:
                        continue
                    seen.add(sys_id)
                    # Hydration by id must return the record even when mapped.
                    if ids or sys_id not in used_ids:
                        results.append(
                            {
                                "key": sys_id,
                                "id": sys_id,
                                "summary": self._display_label(record, sys_id),
                            }
                        )
                        if len(results) >= limit:
                            return results

                offset += len(records)
                if len(records) < LIST_PAGE_SIZE:
                    return results
                if offset >= MAX_LIST_FETCH:
                    logger.warning(
                        "ServiceNow picker scan budget exhausted before the page filled",
                        scanned=offset,
                        collected=len(results),
                    )
                    return results

        except requests.exceptions.RequestException:
            logger.error("Failed to search ServiceNow", exc_info=True)
            raise

    @staticmethod
    def _display_label(record: dict[str, Any], sys_id: str) -> str:
        """Human-readable label for a remote row, working across table types.

        Prefers incident-style ``number - short_description``, falls back to a
        generic ``name`` (CMDB/asset tables), then the sys_id.
        """
        number = record.get("number")
        short_description = record.get("short_description")
        if number or short_description:
            return f"{number or ''} - {short_description or ''}".strip(" -")
        return record.get("name") or sys_id

    def get_available_tables(self) -> list[dict]:
        """
        Fetches 'user-facing' tables (Incidents, Controls, etc).
        Filters out system internals, import sets, and link tables.
        """
        # Prefixes are matched here rather than in the encoded query:
        # ServiceNow's NOT LIKE means "does not contain", so a server-side
        # "v_" or "ip_" also drops tables like cmdb_ci_hyper_v_server or
        # cmdb_ci_ip_router, and there is no "does not start with" operator.
        # 'sys_update_nameISNOTEMPTY' keeps tracked objects (drops some temp tables).
        url = f"{self.base_url}/api/now/table/sys_db_object"
        tables = []
        offset = 0
        try:
            while True:
                params = {
                    "sysparm_query": "sys_update_nameISNOTEMPTY^ORDERBYname",
                    "sysparm_fields": "name,label",
                    "sysparm_limit": TABLES_PAGE_SIZE,
                    "sysparm_offset": offset,
                    "sysparm_exclude_reference_link": "true",
                }
                response = requests.get(
                    url,
                    auth=self.auth,
                    headers=self._get_headers(),
                    params=params,
                    timeout=30,
                    allow_redirects=False,
                )
                response.raise_for_status()
                records = response.json().get("result", [])
                tables.extend(
                    t for t in records if not is_excluded_table(t.get("name", ""))
                )

                offset += len(records)
                if len(records) < TABLES_PAGE_SIZE:
                    break
                if offset >= MAX_TABLES_FETCH:
                    logger.warning(
                        "ServiceNow table scan budget exhausted", scanned=offset
                    )
                    break

        except requests.exceptions.RequestException:
            logger.error("Failed to fetch tables", exc_info=True)
            raise

        # Sort by Label for UX
        return sorted(tables, key=lambda x: x.get("label", ""))

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
                url,
                auth=self.auth,
                headers=self._get_headers(),
                params=params,
                timeout=10,
                allow_redirects=False,
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
                url,
                auth=self.auth,
                headers=self._get_headers(),
                params=params,
                timeout=10,
                allow_redirects=False,
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
                allow_redirects=False,
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
        except Exception:
            logger.error("Failed to fetch columns", table=table_name, exc_info=True)

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
                allow_redirects=False,
            )
            response.raise_for_status()
            results = response.json().get("result", [])

            return [{"value": r["value"], "label": r["label"]} for r in results]

        except Exception:
            logger.warning(
                "Error fetching choices",
                table=table_name,
                field=field_name,
                exc_info=True,
            )
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
                allow_redirects=False,
            )
            return response.status_code == 200
        except Exception:
            logger.error("ServiceNow connection test failed", exc_info=True)
            return False
