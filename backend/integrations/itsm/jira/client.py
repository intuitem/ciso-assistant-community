import re
from typing import Any, Dict

from integrations.models import SyncMapping
from jira import JIRA, JIRAError
from structlog import get_logger

from core.models import AppliedControl
from core.net_safety import check_integration_url
from integrations.base import BaseIntegrationClient

from .mapper import JiraFieldMapper

logger = get_logger(__name__)

# Separator used in the composite ``table_name`` setting that encodes a
# Jira project key and issue type name together (e.g. ``"PROJ:Task"``).
# Project keys are uppercase alphanumeric so ``":"`` cannot appear in them.
TABLE_NAME_SEPARATOR = ":"

# Fields that depend on workflow / instance config rather than createmeta and
# must be surfaced manually to the field mapper.
SYNTHETIC_FIELDS = ({"name": "status", "label": "Status", "readonly": False},)

# Search terms shaped like an issue key ("CISO-40") also get a ``key =``
# clause in the picker JQL.
ISSUE_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*-\d+$")

# Numeric issue ids are the other id form Jira accepts besides keys.
ISSUE_ID_PATTERN = re.compile(r"^\d+$")

# Each hydration id costs one remote call; cap the client-supplied list. The
# picker only hydrates selected values, so a handful is plenty.
MAX_HYDRATION_IDS = 20

# Ceiling on total rows scanned per list call while paging past
# already-mapped issues that get filtered out of the results.
MAX_LIST_FETCH = 500

# Rows requested per page while scanning; Jira Cloud caps search/jql pages
# at 100 rows anyway.
LIST_PAGE_SIZE = 100

# Lucene-reserved characters inside a ``~`` text query: unescaped they make
# Jira reject the JQL with a 400, and the text index strips punctuation
# anyway, so search terms have them replaced with spaces.
LUCENE_SPECIALS = re.compile(r'[+\-&|!(){}\[\]^~*?:\\"/]')


class JiraClient(BaseIntegrationClient):
    def __init__(self, configuration, model_key="applied_control"):
        super().__init__(configuration, model_key)
        server_url = self.credentials["server_url"]
        try:
            check_integration_url(server_url, "Jira server_url")
        except ValueError:
            logger.error("Jira server_url blocked by SSRF guard", exc_info=True)
            raise
        self.jira = JIRA(
            server=server_url,
            basic_auth=(self.credentials["email"], self.credentials["api_token"]),
            timeout=30,
            max_retries=3,
        )
        self.jira._session.max_redirects = 0
        self.mapper = JiraFieldMapper(configuration, model_key)

    # Settings helpers

    def _resolve_target(self) -> tuple[str, str]:
        """Return ``(project_key, issue_type_name)`` from settings.

        Prefer the composite ``table_name`` (set by the FieldMapper UI); fall
        back to the legacy split ``project_key`` / ``issue_type`` settings.
        """
        project_key, issue_type = self._parse_table_name(
            self.model_settings.get("table_name")
        )
        if not project_key:
            project_key = self.model_settings.get("project_key", "")
        if not issue_type:
            issue_type = self.model_settings.get("issue_type", "Task")
        return project_key, issue_type

    @staticmethod
    def _parse_table_name(table_name: str | None) -> tuple[str, str]:
        if not table_name:
            return "", ""
        if TABLE_NAME_SEPARATOR not in table_name:
            return table_name, ""
        project_key, issue_type = table_name.split(TABLE_NAME_SEPARATOR, 1)
        return project_key.strip(), issue_type.strip()

    # CRUD

    def create_remote_object(self, local_object: AppliedControl):
        project_key, issue_type = self._resolve_target()
        if not project_key:
            raise ValueError("Jira project_key/table_name is not configured")

        issue_dict = self.mapper.to_remote(local_object)
        issue_dict["project"] = {"key": project_key}
        issue_dict["issuetype"] = {"name": issue_type or "Task"}

        target_status_name = issue_dict.pop("status", None)

        issue = self.jira.create_issue(fields=issue_dict)

        # Handle the status transition separately
        if target_status_name:
            self._transition_issue_to_status(issue.key, target_status_name)

        logger.info(f"Created Jira issue {issue.key}")
        return issue.key

    def update_remote_object(self, remote_id: str, changes: dict[str, Any]) -> bool:
        try:
            # Status must be handled as a transition, not an edit.
            target_status_name = None
            if "status" in changes:
                target_status_name = changes.pop("status", None)

            # Update all other fields (if any remain)
            if changes:
                issue = self.jira.issue(remote_id)
                issue.update(fields=changes)
                logger.info(
                    f"Updated standard fields for Jira issue {remote_id}: {list(changes.keys())}"
                )

            # Handle the status transition separately
            if target_status_name:
                self._transition_issue_to_status(remote_id, target_status_name)

            return True

        except Exception as e:
            logger.error(f"Failed to update Jira issue {remote_id}: {e}")
            raise  # Re-raise the exception to be caught by the orchestrator

    def _transition_issue_to_status(
        self, remote_id: str, target_status_name: str
    ) -> None:
        """
        Helper function to find and execute the correct workflow transition
        to move an issue to a target status.
        """
        # A blank target (e.g. an unmapped or undefined status) has no workflow
        # path; skip silently instead of raising on a "--"/"" transition.
        if not target_status_name or not target_status_name.strip():
            return

        try:
            transitions = self.jira.transitions(remote_id)

            transition_id = None
            available_statuses = []
            for t in transitions:
                available_statuses.append(t["to"]["name"])
                if t["to"]["name"].lower() == target_status_name.lower():
                    transition_id = t["id"]
                    break

            if transition_id:
                self.jira.transition_issue(remote_id, transition_id)
                logger.info(
                    f"Transitioned Jira issue {remote_id} to status '{target_status_name}'"
                )
            else:
                logger.error(
                    f"No available transition for issue {remote_id} to status '{target_status_name}'. "
                    f"Available transitions are for: {available_statuses}"
                )
                raise Exception(
                    f"Invalid status transition: No workflow path to '{target_status_name}'. "
                    f"Available targets: {available_statuses}"
                )

        except Exception as e:
            logger.error(f"Failed to transition Jira issue {remote_id}: {e}")
            raise

    def get_remote_object(self, remote_id: str) -> Dict[str, Any]:
        try:
            issue = self.jira.issue(remote_id)
            return {
                "key": issue.key,
                "fields": issue.raw["fields"],
                "updated": issue.fields.updated,
            }
        except Exception as e:
            logger.error(f"Failed to fetch Jira issue {remote_id}: {e}")
            raise

    def test_connection(self) -> bool:
        try:
            self.jira.myself()
            return True
        except Exception as e:
            logger.error(f"Jira connection test failed: {e}")
            return False

    @staticmethod
    def _escape_jql_string(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    @classmethod
    def _sanitize_search_term(cls, value: str) -> str:
        """Prepare a free-text term for use inside ``summary ~ "..."``.

        Lucene-reserved characters make Jira 400 unescaped, and escaped they
        never match anyway because the text analyzer strips punctuation from
        the index. Replace them with spaces so the remaining words search
        naturally. May return an empty string (nothing searchable).
        """
        words = LUCENE_SPECIALS.sub(" ", value)
        return cls._escape_jql_string(" ".join(words.split()))

    def _build_list_jql(
        self, project_key: str, issue_type: str, search: str = ""
    ) -> tuple[str | None, str | None]:
        """Return ``(jql, key_jql)`` for the remote object picker.

        ``jql`` filters on summaries; ``key_jql`` additionally matches the
        issue key when the search term looks like one. It is a separate
        query because JQL referencing a nonexistent issue key fails with a
        400 instead of returning an empty result, so the caller falls back
        to ``jql`` when it errors. ``(None, None)`` means the search term
        has no searchable content and cannot match anything.
        """
        prefix = f"project = {project_key}"
        if issue_type:
            # Scope to the configured issue type so the link picker doesn't
            # surface issues of other types (e.g. Epics when Task is the
            # target). Quote the name as it may contain spaces ("User Story").
            prefix += f' AND issuetype = "{self._escape_jql_string(issue_type)}"'

        if not search:
            return prefix, None

        term = self._sanitize_search_term(search.strip())
        if not term:
            return None, None
        jql = f'{prefix} AND summary ~ "{term}*"'

        candidate_key = None
        if ISSUE_KEY_PATTERN.match(search.strip()):
            candidate_key = search.strip().upper()
        elif search.strip().isdigit():
            candidate_key = f"{project_key}-{search.strip()}"
        key_jql = None
        if candidate_key:
            key_jql = f'{prefix} AND (summary ~ "{term}*" OR key = "{candidate_key}")'
        return jql, key_jql

    def list_remote_objects(
        self, query_params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """List issues from the configured Jira project.

        ``query_params`` supports ``search`` (matched against issue summaries
        and, when it looks like one, an issue key), ``limit`` and ``id`` (a
        comma-separated list of issue keys to hydrate).
        """
        if not self.jira:
            raise ConnectionError("Jira client not initialized.")
        if query_params is None:
            query_params = {}

        project_key, issue_type = self._resolve_target()
        if not project_key:
            raise ValueError("Jira project_key/table_name is not configured")

        used_issues = set(
            SyncMapping.objects.filter(configuration=self.configuration).values_list(
                "remote_id", flat=True
            )
        )

        ids = query_params.get("id", "")
        if ids:
            # Only key- or numeric-shaped ids may reach jira.issue(): the id
            # is formatted into the REST path, so anything else could steer
            # the request elsewhere on the API.
            id_list = [
                i.strip()
                for i in ids.split(",")
                if i.strip()
                and (
                    ISSUE_KEY_PATTERN.match(i.strip())
                    or ISSUE_ID_PATTERN.match(i.strip())
                )
            ][:MAX_HYDRATION_IDS]
            results_list = []
            for remote_id in id_list:
                try:
                    issue = self.jira.issue(
                        remote_id, fields="summary,project,issuetype"
                    )
                    fields = issue.raw["fields"]
                    # Keep hydration inside the picker's scope: the
                    # integration's credentials may see other projects, the
                    # caller must not.
                    if fields["project"]["key"].upper() != project_key.upper():
                        continue
                    if (
                        issue_type
                        and fields["issuetype"]["name"].lower() != issue_type.lower()
                    ):
                        continue
                    entry = {
                        "key": issue.key,
                        "id": issue.id,
                        "summary": fields["summary"],
                    }
                except Exception:
                    logger.warning("Failed to hydrate Jira issue", remote_id=remote_id)
                    continue
                results_list.append(entry)
            return results_list

        search = str(query_params.get("search", "") or "")
        limit = query_params.get("limit", 50)
        summary_jql, key_jql = self._build_list_jql(project_key, issue_type, search)
        if summary_jql is None:
            # The term sanitized down to nothing (pure punctuation): nothing
            # can match it, and an empty ~ clause would match everything.
            return []

        jql_query = f"{key_jql or summary_jql} ORDER BY created DESC"

        logger.info(f"Searching Jira with JQL: {jql_query}, limit: {limit}")

        try:
            try:
                results_list = self._collect_unmapped(jql_query, limit, used_issues)
            except JIRAError as e:
                if not key_jql or e.status_code != 400:
                    raise
                # The key clause 400s when the issue doesn't exist; retry on
                # summaries only. Anything else (429, 5xx, auth) is a real
                # error, not a missing key, and must propagate.
                jql_query = f"{summary_jql} ORDER BY created DESC"
                results_list = self._collect_unmapped(jql_query, limit, used_issues)

            logger.info(
                f"Fetched {len(results_list)} Jira issues for project {project_key}."
            )
            return results_list

        except Exception as e:
            logger.error(f"Failed to search Jira issues: JQL='{jql_query}', Error={e}")
            raise

    def _collect_unmapped(
        self, jql: str, limit: int, used_issues: set
    ) -> list[dict[str, Any]]:
        """Collect up to ``limit`` issues not already linked by a SyncMapping.

        Mapped issues are filtered out client-side, so a single over-fetch
        cannot tell "few matches" from "page full of mapped issues" — the
        latter would return a short page and silently flip the picker's
        lazy/eager probe to eager on a truncated list. Instead, keep paging
        until the page fills or the source (or the MAX_LIST_FETCH scan
        budget) runs out.
        """
        results: list[dict[str, Any]] = []
        # Issues created mid-scan shift the created DESC pages, so a key can
        # show up on two consecutive pages.
        seen: set[str] = set()
        scanned = 0
        for page in self._iter_search_pages(jql):
            for issue in page:
                scanned += 1
                key = issue.raw["key"]
                if key in used_issues or key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "key": key,
                        "id": issue.raw["id"],
                        "summary": issue.raw["fields"]["summary"],
                    }
                )
                if len(results) >= limit:
                    return results
            if scanned >= MAX_LIST_FETCH:
                logger.warning(
                    "Jira picker scan budget exhausted before the page filled",
                    scanned=scanned,
                    collected=len(results),
                )
                break
        return results

    def _iter_search_pages(self, jql: str):
        """Yield pages of issues matching ``jql`` until the source runs out.

        Jira Cloud only pages the ``search/jql`` endpoint with a page token
        (``search_issues`` raises on any non-zero ``startAt`` there); Data
        Center still pages the classic search API by offset.
        """
        if self.jira._is_cloud:
            token = None
            while True:
                page = self.jira.enhanced_search_issues(
                    jql,
                    nextPageToken=token,
                    maxResults=LIST_PAGE_SIZE,
                    fields="summary",
                )
                yield page
                token = getattr(page, "nextPageToken", None)
                if not token or not len(page):
                    return
        else:
            start_at = 0
            while True:
                page = self.jira.search_issues(
                    jql,
                    startAt=start_at,
                    maxResults=LIST_PAGE_SIZE,
                    fields="summary",
                )
                yield page
                if len(page) < LIST_PAGE_SIZE:
                    return
                start_at += len(page)

    # Discovery (powers the FieldMapper RPC actions)

    def get_available_tables(self) -> list[dict]:
        """Return every ``(project, issue type)`` pair as a flat table list.

        Each entry's ``name`` is the composite ``"<PROJECT_KEY>:<Issue Type>"``
        string the FieldMapper UI will write back to ``settings.table_name``.
        """
        tables: list[dict] = []
        try:
            projects = self.jira.projects()
        except Exception:
            logger.error("Failed to list Jira projects", exc_info=True)
            raise

        for project in projects:
            project_key = getattr(project, "key", None)
            project_name = getattr(project, "name", project_key)
            if not project_key:
                continue
            issue_types = self._get_project_issue_types(project_key)
            for issue_type in issue_types:
                tables.append(
                    {
                        "name": f"{project_key}{TABLE_NAME_SEPARATOR}{issue_type}",
                        "label": f"{project_name} - {issue_type}",
                    }
                )

        tables.sort(key=lambda entry: entry["label"])
        return tables

    def _get_project_issue_types(self, project_key: str) -> list[str]:
        try:
            project = self.jira.project(project_key)
            return [
                it.name
                for it in getattr(project, "issueTypes", [])
                if getattr(it, "name", None)
            ]
        except Exception:
            logger.warning(
                "Failed to fetch issue types for project",
                project_key=project_key,
                exc_info=True,
            )
            return []

    def _legacy_createmeta_supported(self) -> bool:
        """Whether the single-call ``createmeta`` endpoint is available.

        Jira Server/DC dropped it in 9.0 (still present on Cloud and DC < 9.0).
        On the unsupported deployments the ``jira`` client raises before making
        any request, so we branch to the per-issue-type createmeta endpoints.
        """
        if getattr(self.jira, "_is_cloud", False):
            return True
        return getattr(self.jira, "_version", (0, 0, 0)) < (9, 0, 0)

    def _fetch_field_meta(self, project_key: str, issue_type: str) -> dict[str, dict]:
        """Return ``{field_id: field_def}`` for a project (+ optional issue type).

        Normalizes both createmeta APIs to the legacy field-definition shape
        (``name`` / ``schema`` / ``operations`` / ``allowedValues``) so callers
        stay agnostic to the Jira deployment version.
        """
        if self._legacy_createmeta_supported():
            return self._fetch_field_meta_legacy(project_key, issue_type)
        return self._fetch_field_meta_v2(project_key, issue_type)

    def _fetch_field_meta_legacy(
        self, project_key: str, issue_type: str
    ) -> dict[str, dict]:
        meta = self.jira.createmeta(
            projectKeys=project_key,
            issuetypeNames=issue_type or None,
            expand="projects.issuetypes.fields",
        )
        fields: dict[str, dict] = {}
        for project in meta.get("projects", []) or []:
            for it in project.get("issuetypes", []) or []:
                if issue_type and it.get("name") != issue_type:
                    continue
                fields.update(it.get("fields") or {})
        return fields

    def _fetch_field_meta_v2(
        self, project_key: str, issue_type: str
    ) -> dict[str, dict]:
        # Jira Server/DC >= 9.0: resolve the issue type name to its id, then
        # pull that issue type's fields from the per-issue-type createmeta
        # endpoints (createmeta/{project}/issuetypes[/{id}]). ``maxResults=False``
        # tells the client to page through every result rather than the first 50.
        fields: dict[str, dict] = {}
        issue_types = self.jira.project_issue_types(project_key, maxResults=False)
        for it in issue_types or []:
            it_id = getattr(it, "id", None)
            if not it_id:
                continue
            if issue_type and getattr(it, "name", None) != issue_type:
                continue
            for field in (
                self.jira.project_issue_fields(project_key, it_id, maxResults=False)
                or []
            ):
                raw = getattr(field, "raw", None) or {}
                field_id = raw.get("fieldId")
                if not field_id:
                    continue
                fields[field_id] = {
                    "name": raw.get("name"),
                    "schema": raw.get("schema", {}),
                    "operations": raw.get("operations"),
                    "allowedValues": raw.get("allowedValues"),
                }
        return fields

    def get_table_columns(self, table_name: str) -> list[dict]:
        """Return the fields available for a given project+issue type."""
        project_key, issue_type = self._parse_table_name(table_name)
        if not project_key:
            return []

        try:
            field_meta = self._fetch_field_meta(project_key, issue_type)
        except Exception:
            # Let the orchestrator's RPC view surface this as a real error
            # (502 with detail) instead of silently returning only the
            # synthetic status row, which the UI used to render as a
            # "1-row mapper" with no signal that the underlying API call
            # had failed (expired token, missing scope, unsupported version).
            logger.warning(
                "Failed to fetch field metadata for project",
                project_key=project_key,
                issue_type=issue_type,
                exc_info=True,
            )
            raise

        columns: dict[str, dict] = {}
        for field_id, field_def in field_meta.items():
            label = field_def.get("name") or field_id
            schema = field_def.get("schema", {}) or {}
            columns[field_id] = {
                "name": field_id,
                "label": label,
                "type": schema.get("type"),
                "readonly": not field_def.get("operations"),
            }

        # Status is workflow-driven and never appears in createmeta; surface it
        # so users can map CISO Assistant ``status`` to Jira's status field.
        for synthetic in SYNTHETIC_FIELDS:
            columns.setdefault(synthetic["name"], dict(synthetic))

        return sorted(columns.values(), key=lambda c: c["label"].lower())

    def get_field_choices(self, table_name: str, field_name: str) -> list[dict]:
        """Return the choices available for ``field_name`` on the given table."""
        project_key, issue_type = self._parse_table_name(table_name)
        if not project_key or not field_name:
            return []

        if field_name == "status":
            return self._get_status_choices(project_key, issue_type)
        if field_name == "priority":
            return self._get_priority_choices(project_key, issue_type)

        return self._get_allowed_values_from_createmeta(
            project_key, issue_type, field_name
        )

    def _get_status_choices(self, project_key: str, issue_type: str) -> list[dict]:
        # Scope to the selected project (and issue type) instead of the
        # instance-wide ``statuses()`` endpoint, which leaks every workflow's
        # statuses across all projects. ``issue_types_for_project`` hits
        # ``GET project/{key}/statuses`` and groups statuses by issue type, so
        # a user can only map to statuses that actually exist in this project's
        # workflow (otherwise the runtime transition has no valid path).
        try:
            issue_types = self.jira.issue_types_for_project(project_key)
        except Exception:
            logger.warning(
                "Failed to fetch Jira statuses for project",
                project_key=project_key,
                issue_type=issue_type,
                exc_info=True,
            )
            raise

        statuses: dict[str, str] = {}
        for it in issue_types or []:
            # When the table pins an issue type, only that issue type's
            # workflow statuses apply. Without one, union every issue type.
            if issue_type and getattr(it, "name", None) != issue_type:
                continue
            for status in getattr(it, "statuses", []) or []:
                name = getattr(status, "name", None)
                if name:
                    statuses[name] = name

        return [
            {"value": value, "label": label}
            for value, label in sorted(statuses.items(), key=lambda kv: kv[1].lower())
        ]

    def _get_priority_choices(self, project_key: str, issue_type: str) -> list[dict]:
        # Prefer the project-scoped allowed values from createmeta so we honor
        # the project's priority scheme rather than the instance-wide
        # ``priorities()`` list.
        scoped = self._get_allowed_values_from_createmeta(
            project_key, issue_type, "priority"
        )
        if scoped:
            return scoped

        # createmeta omits ``priority`` when it isn't on the project's create
        # screen; fall back to the instance-wide list so the row isn't empty.
        try:
            priorities = self.jira.priorities()
        except Exception:
            logger.warning("Failed to fetch Jira priorities", exc_info=True)
            raise
        result: list[dict] = []
        for p in priorities or []:
            name = getattr(p, "name", None)
            if name:
                result.append({"value": name, "label": name})
        return result

    def _get_allowed_values_from_createmeta(
        self, project_key: str, issue_type: str, field_name: str
    ) -> list[dict]:
        try:
            field_meta = self._fetch_field_meta(project_key, issue_type)
        except Exception:
            logger.warning(
                "Failed to fetch field metadata for choices",
                project_key=project_key,
                issue_type=issue_type,
                field_name=field_name,
                exc_info=True,
            )
            return []

        field_def = field_meta.get(field_name)
        if not field_def:
            return []

        results = []
        for entry in field_def.get("allowedValues") or []:
            value = entry.get("value") or entry.get("name") or entry.get("id")
            label = entry.get("name") or entry.get("value") or value
            if value is None:
                continue
            results.append({"value": value, "label": label})
        return results
