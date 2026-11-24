import hashlib
import re
import threading
import time
from typing import Any

import requests
from structlog import get_logger

from core.net_safety import check_integration_url
from integrations.base import BaseIntegrationClient
from integrations.models import SyncMapping
from integrations.settings_access import get_model_settings

from .mapper import GLPIFieldMapper

logger = get_logger(__name__)

# The high-level API is versioned in the path. v2 shipped with GLPI 11 and is
# still served by GLPI 12 (whose default is v3), so pinning it keeps both
# releases on the same contract.
API_ROOT = "/api.php"
API_PREFIX = f"{API_ROOT}/v2"

# Item types a local object can sync with, per local model, and their display
# label. The key is both the schema name in the OpenAPI document and the last
# segment of the collection path.
ASSISTANCE_TYPES: dict[str, str] = {
    "Ticket": "Tickets",
    "Change": "Changes",
    "Problem": "Problems",
}
ASSET_TYPES: dict[str, str] = {
    "Computer": "Computers",
    "Monitor": "Monitors",
    "NetworkEquipment": "Network equipment",
    "Peripheral": "Peripherals",
    "Phone": "Phones",
    "Printer": "Printers",
    "Software": "Software",
    "SoftwareLicense": "Software licenses",
    "Certificate": "Certificates",
    "Appliance": "Appliances",
    "Rack": "Racks",
    "Enclosure": "Enclosures",
    "PDU": "PDUs",
}
MODEL_ITEM_TYPES: dict[str, dict[str, str]] = {
    "applied_control": ASSISTANCE_TYPES,
    "asset": ASSET_TYPES,
}
ITEM_TYPES: dict[str, str] = {**ASSISTANCE_TYPES, **ASSET_TYPES}
# First path segment of each item type's collection.
_API_SECTIONS: dict[str, str] = {
    **{item_type: "Assistance" for item_type in ASSISTANCE_TYPES},
    **{item_type: "Assets" for item_type in ASSET_TYPES},
}
DEFAULT_ITEM_TYPE = "Ticket"
# Applied controls sync with tickets unless told otherwise. Assets only sync
# once an item type is chosen.
_DEFAULT_ITEM_TYPES: dict[str, str] = {"applied_control": DEFAULT_ITEM_TYPE}

# Properties every synced item type must expose: the picker searches by name
# and leaves out items in the trash.
_REQUIRED_PROPERTIES = {"name", "is_deleted"}


def item_type_for(settings: dict | None, model_key: str) -> str | None:
    """Item type a model syncs with under these settings, None when unset."""
    chosen = get_model_settings(settings or {}, model_key).get("table_name")
    return chosen or _DEFAULT_ITEM_TYPES.get(model_key)


def qualify(item_type: str, item_id: Any) -> str:
    """Remote id as stored on a link. A GLPI id is only unique within its item
    type, and one configuration can sync several, so the type goes with it."""
    return f"{item_type}:{item_id}"


def split_remote_id(remote_id: Any) -> tuple[str | None, str]:
    """``(item type, id)`` of a stored remote id. The type is None for a bare
    id, as given when linking through the API."""
    item_type, sep, item_id = str(remote_id).strip().rpartition(":")
    return (item_type if sep else None), item_id


# Each hydration id is user-supplied; the picker only hydrates selected
# values, so a handful is plenty.
MAX_HYDRATION_IDS = 20

# Ceiling on total rows scanned per list call while paging past
# already-mapped items that get filtered out of the results.
MAX_LIST_FETCH = 500

# Rows requested per page while scanning.
LIST_PAGE_SIZE = 100

# Newest first.
LIST_ORDERING = "id:desc"

# Refresh a cached token this long before GLPI expires it.
TOKEN_EXPIRY_MARGIN = 60

# Access tokens live for an hour by default. Clients are rebuilt for every
# request and task, so tokens are shared per process to avoid a password grant
# (and a new token row in GLPI) on each call. Keyed by a digest of the
# credentials: a changed secret never reuses a token issued for the old one.
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}
_TOKEN_LOCK = threading.Lock()

_ENUM_LINE = re.compile(r"^- (\S+): (.+)$", re.MULTILINE)


def _label(name: str) -> str:
    return name.replace("_", " ").capitalize()


def _enum_choices(prop: dict[str, Any]) -> list[dict[str, str]]:
    """Choices of an enum property, labelled from its description.

    GLPI documents enums as ``- <value>: <label>`` lines.
    """
    labels = dict(_ENUM_LINE.findall(prop.get("description") or ""))
    return [
        {"value": str(value), "label": labels.get(str(value), str(value)).strip()}
        for value in prop.get("enum") or []
    ]


def parse_schema(document: dict[str, Any]) -> tuple[list, dict, dict]:
    """Extract tables, columns and choices from GLPI's OpenAPI document.

    Returns ``(tables, columns, choices)`` in the shapes the schema cache and
    the FieldMapper expect. Only mappable properties are kept: scalars, plus
    dropdowns whose id is a documented enum (status).
    """
    schemas = document.get("components", {}).get("schemas", {})
    tables: list[dict[str, str]] = []
    columns: dict[str, list[dict[str, Any]]] = {}
    choices: dict[str, list[dict[str, str]]] = {}

    for table, label in ITEM_TYPES.items():
        schema = schemas.get(table)
        if not schema or not _REQUIRED_PROPERTIES <= set(
            schema.get("properties") or {}
        ):
            continue
        tables.append({"name": table, "label": label})
        table_columns = []
        for name, prop in (schema.get("properties") or {}).items():
            prop_type = prop.get("type")
            enum_prop = prop
            if prop_type == "object":
                enum_prop = (prop.get("properties") or {}).get("id") or {}
                if not enum_prop.get("enum"):
                    continue
            elif prop_type not in ("string", "integer", "number", "boolean"):
                continue
            if enum_prop.get("enum"):
                choices[f"{table}:{name}"] = _enum_choices(enum_prop)
            table_columns.append(
                {
                    "name": name,
                    "label": _label(name),
                    "type": prop.get("format") or prop_type,
                    "readonly": bool(prop.get("readOnly")),
                }
            )
        columns[table] = sorted(table_columns, key=lambda c: c["label"])

    return tables, columns, choices


class GLPIAuthenticationError(requests.exceptions.RequestException):
    """The token request failed. Kept apart from HTTPError so that its status
    is never read as the answer to the call that needed the token."""


class GLPIClient(BaseIntegrationClient):
    """Client for the GLPI high-level REST API (GLPI 11 and later)."""

    def __init__(self, configuration, model_key="applied_control"):
        super().__init__(configuration, model_key)
        self.base_url = (self.credentials.get("instance_url") or "").rstrip("/")
        try:
            check_integration_url(self.base_url, "GLPI instance_url")
        except ValueError:
            logger.error("GLPI instance_url blocked by SSRF guard", exc_info=True)
            raise
        self.table = item_type_for(configuration.settings, model_key)
        self.mapper = GLPIFieldMapper(configuration, model_key)
        self._schema: tuple[list, dict, dict] | None = None

    # --- HTTP ---------------------------------------------------------------

    def _token_cache_key(self) -> str:
        parts = (
            self.base_url,
            *(
                str(self.credentials.get(key) or "")
                for key in ("client_id", "client_secret", "username", "password")
            ),
        )
        return hashlib.sha256("\x00".join(parts).encode()).hexdigest()

    def _get_token(self, force: bool = False) -> str:
        key = self._token_cache_key()
        with _TOKEN_LOCK:
            cached = _TOKEN_CACHE.get(key)
            if cached and not force and cached[1] > time.monotonic():
                return cached[0]

        response = requests.post(
            f"{self.base_url}{API_ROOT}/token",
            data={
                "grant_type": "password",
                "client_id": self.credentials.get("client_id", ""),
                "client_secret": self.credentials.get("client_secret", ""),
                "username": self.credentials.get("username", ""),
                "password": self.credentials.get("password", ""),
                "scope": "api",
            },
            headers={"Accept": "application/json"},
            timeout=30,
            allow_redirects=False,
        )
        try:
            self._raise_for_status(response)
        except requests.exceptions.HTTPError as error:
            raise GLPIAuthenticationError(
                f"GLPI refused the token request ({response.status_code})",
                response=response,
            ) from error
        body = response.json()
        token = body["access_token"]
        lifetime = max(int(body.get("expires_in") or 0) - TOKEN_EXPIRY_MARGIN, 0)
        with _TOKEN_LOCK:
            _TOKEN_CACHE[key] = (token, time.monotonic() + lifetime)
        return token

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Authenticated call. A 401 re-authenticates once: a cached token can
        be revoked on the GLPI side before its expiry."""
        url = f"{self.base_url}{API_PREFIX}{path}"
        kwargs.setdefault("timeout", 30)
        for attempt in (0, 1):
            response = requests.request(
                method,
                url,
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._get_token(force=attempt == 1)}",
                },
                allow_redirects=False,
                **kwargs,
            )
            if response.status_code != 401 or attempt == 1:
                break
        self._raise_for_status(response)
        return response

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        # Redirects are not followed, and raise_for_status() lets them pass: a
        # write answered with one (an http URL sent to https, a proxy) was not
        # applied and must not count as done.
        if 300 <= response.status_code < 400:
            raise requests.exceptions.HTTPError(
                f"GLPI answered with a redirect ({response.status_code}); "
                "check the instance URL",
                response=response,
            )
        response.raise_for_status()

    def _collection_path(self) -> str:
        if self.table not in MODEL_ITEM_TYPES.get(self.model_key, {}):
            raise ValueError(
                f"Unsupported GLPI item type for {self.model_key}: {self.table}"
            )
        return f"/{_API_SECTIONS[self.table]}/{self.table}"

    def _item_id(self, remote_id: str) -> str:
        """Numeric id of an item of the configured type."""
        item_type, item_id = split_remote_id(remote_id)
        if item_type is not None and item_type != self.table:
            raise ValueError(
                f"{remote_id} is not a GLPI {self.table}: the configuration "
                "syncs another item type"
            )
        # Ids are numeric; anything else would alter the request path.
        if not item_id.isdigit():
            raise ValueError(f"Invalid GLPI item id: {remote_id}")
        return item_id

    def _item_path(self, remote_id: str) -> str:
        return f"{self._collection_path()}/{self._item_id(remote_id)}"

    # --- Sync ---------------------------------------------------------------

    def test_connection(self) -> bool:
        try:
            # Proves both the OAuth client and the user's API access.
            return self._request("GET", "/Session", timeout=10).status_code == 200
        except Exception:
            logger.error("GLPI connection test failed", exc_info=True)
            return False

    def create_remote_object(self, local_object) -> str:
        payload = self.mapper.to_remote(local_object)
        if not payload:
            # GLPI would create an empty item.
            raise ValueError(
                f"No mapped field of this object has a value to create a GLPI "
                f"{self.table} from"
            )
        try:
            response = self._request("POST", self._collection_path(), json=payload)
        except requests.exceptions.RequestException:
            logger.error("Failed to create GLPI item", table=self.table, exc_info=True)
            raise
        remote_id = qualify(self.table, response.json()["id"])
        logger.info("Created GLPI item", table=self.table, remote_id=remote_id)
        return remote_id

    def update_remote_object(self, remote_id: str, changes: dict[str, Any]) -> bool:
        if not changes:
            return False
        try:
            self._request("PATCH", self._item_path(remote_id), json=changes)
        except requests.exceptions.RequestException:
            logger.error(
                "Failed to update GLPI item",
                table=self.table,
                remote_id=remote_id,
                changed_fields=list(changes.keys()),
                exc_info=True,
            )
            raise
        logger.info(
            "Updated GLPI item",
            table=self.table,
            remote_id=remote_id,
            changed_fields=list(changes.keys()),
        )
        return True

    def get_remote_object(self, remote_id: str) -> dict[str, Any]:
        try:
            item = self._request("GET", self._item_path(remote_id)).json()
        except requests.exceptions.RequestException:
            logger.error(
                "Failed to fetch GLPI item",
                table=self.table,
                remote_id=remote_id,
                exc_info=True,
            )
            raise
        return self.normalize_item(item)

    def read_item(self, remote_id: str) -> dict[str, Any] | None:
        """Current state of an item, None once GLPI no longer has it. Other
        failures are raised."""
        try:
            item = self._request("GET", self._item_path(remote_id)).json()
        except requests.exceptions.HTTPError as error:
            if error.response is not None and error.response.status_code == 404:
                return None
            raise
        return self.normalize_item(item)

    @staticmethod
    def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
        """Shape shared by API reads and webhook payloads, so the cached
        ``remote_data`` compares equal whichever side it came from."""
        return {
            "key": str(item.get("id")),
            "fields": item,
            "updated": item.get("date_mod"),
        }

    def list_remote_objects(
        self, query_params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """List items of the configured type.

        ``query_params`` supports ``search`` (matched against the name, and
        the id when numeric), ``limit`` and ``id`` (comma-separated ids to
        hydrate, as stored on links or bare).
        """
        query_params = query_params or {}
        if not self.table:
            # No item type chosen for this model yet: nothing to offer.
            return []
        ids = str(query_params.get("id", "") or "")
        search = str(query_params.get("search", "") or "")
        limit = query_params.get("limit", 100)

        if ids:
            # Digits only, so no RSQL operator can ride in on an id. An id
            # of another item type is not one of this configuration's items.
            id_list = [
                item_id
                for item_type, item_id in map(split_remote_id, ids.split(","))
                if item_id.isdigit() and item_type in (None, self.table)
            ]
            id_list = id_list[:MAX_HYDRATION_IDS]
            if not id_list:
                return []
            # Hydration returns the item even when mapped or in the trash.
            rsql = f"id=in=({','.join(id_list)})"
        else:
            # Items in the trash are not valid link targets.
            rsql = "is_deleted==false"
            if search:
                # The term goes in a quoted RSQL string; drop the characters
                # that would close it or act as wildcards.
                term = re.sub(r'["\\*]', "", search).strip()
                if not term:
                    return []
                match = f'name=ilike="*{term}*"'
                if term.isdigit():
                    match = f"({match},id=={term})"
                rsql = f"{rsql};{match}"

        used_ids = {
            qualify(item_type or self.table, item_id)
            for item_type, item_id in map(
                split_remote_id,
                SyncMapping.objects.filter(
                    configuration=self.configuration
                ).values_list("remote_id", flat=True),
            )
        }

        # Mapped items are filtered out client-side, so keep paging until the
        # page fills or the source (or the scan budget) runs out.
        results = []
        seen: set[str] = set()
        start = 0
        try:
            while True:
                records = self._request(
                    "GET",
                    self._collection_path(),
                    params={
                        "filter": rsql,
                        "sort": LIST_ORDERING,
                        "start": start,
                        "limit": LIST_PAGE_SIZE,
                    },
                ).json()
                for record in records:
                    remote_id = qualify(self.table, record.get("id"))
                    # An item created during the scan shifts the offsets, so
                    # the next page can start with one already returned.
                    if remote_id in seen:
                        continue
                    seen.add(remote_id)
                    if ids or remote_id not in used_ids:
                        results.append(
                            {
                                "key": remote_id,
                                "id": remote_id,
                                "summary": f"#{record.get('id')} - {record.get('name') or ''}",
                            }
                        )
                        if len(results) >= limit:
                            return results

                start += LIST_PAGE_SIZE
                if len(records) < LIST_PAGE_SIZE:
                    return results
                if start >= MAX_LIST_FETCH:
                    logger.warning(
                        "GLPI picker scan budget exhausted before the page filled",
                        scanned=start,
                        collected=len(results),
                    )
                    return results
        except requests.exceptions.RequestException:
            logger.error("Failed to list GLPI items", table=self.table, exc_info=True)
            raise

    # --- Schema -------------------------------------------------------------

    def fetch_schema(self) -> tuple[list, dict, dict]:
        """Tables, columns and choices from the instance's OpenAPI document.

        The document describes what this instance actually exposes, so the
        mapping UI follows the GLPI version in place. It is several megabytes:
        callers cache the result.
        """
        if self._schema is None:
            # The document is public. It is requested without the token: GLPI
            # 11.0.0 and 11.0.1 answer 500 when one comes with it.
            response = requests.get(
                f"{self.base_url}{API_PREFIX}/doc.json",
                headers={"Accept": "application/json"},
                timeout=60,
                allow_redirects=False,
            )
            self._raise_for_status(response)
            self._schema = parse_schema(response.json())
        return self._schema

    def get_available_tables(self) -> list[dict]:
        return self.fetch_schema()[0]

    def get_table_columns(self, table_name: str) -> list[dict]:
        return self.fetch_schema()[1].get(table_name, [])

    def get_field_choices(self, table_name: str, field_name: str) -> list[dict]:
        return self.fetch_schema()[2].get(f"{table_name}:{field_name}", [])
