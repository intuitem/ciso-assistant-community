from typing import Any, Dict

from integrations.models import SyncMapping
from jira import JIRA
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


class JiraClient(BaseIntegrationClient):
    def __init__(self, configuration):
        super().__init__(configuration)
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
        self.mapper = JiraFieldMapper(configuration)

    # Settings helpers

    def _resolve_target(self) -> tuple[str, str]:
        """Return ``(project_key, issue_type_name)`` from settings.

        Prefer the composite ``table_name`` (set by the FieldMapper UI); fall
        back to the legacy split ``project_key`` / ``issue_type`` settings.
        """
        project_key, issue_type = self._parse_table_name(
            self.settings.get("table_name")
        )
        if not project_key:
            project_key = self.settings.get("project_key", "")
        if not issue_type:
            issue_type = self.settings.get("issue_type", "Task")
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

    def list_remote_objects(
        self, query_params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """List issues from the configured Jira project."""
        if not self.jira:
            raise ConnectionError("Jira client not initialized.")
        if query_params is None:
            query_params = {}

        project_key, issue_type = self._resolve_target()
        if not project_key:
            raise ValueError("Jira project_key/table_name is not configured")

        jql_query = f"project = {project_key}"
        if issue_type:
            # Scope to the configured issue type so the link picker doesn't
            # surface issues of other types (e.g. Epics when Task is the
            # target). Quote the name as it may contain spaces ("User Story").
            escaped = issue_type.replace('"', '\\"')
            jql_query += f' AND issuetype = "{escaped}"'

        start_at = query_params.get("start_at", 0)
        max_results = query_params.get("max_results", 10000)

        logger.info(
            f"Searching Jira with JQL: {jql_query}, startAt: {start_at}, maxResults: {max_results}"
        )

        try:
            used_issues = SyncMapping.objects.filter(
                configuration=self.configuration
            ).values_list("remote_id", flat=True)
            issues = self.jira.search_issues(
                jql_query,
                expand="fields",
            )

            results_list = [
                {
                    "key": issue.raw["key"],
                    "id": issue.raw["id"],
                    "summary": issue.raw["fields"]["summary"],
                }
                for issue in issues
                if issue.raw["key"] not in used_issues
            ]
            logger.info(
                f"Fetched {len(results_list)} Jira issues for project {project_key} (batch starting at {start_at})."
            )
            return results_list

        except Exception as e:
            logger.error(f"Failed to search Jira issues: JQL='{jql_query}', Error={e}")
            raise

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

    def get_table_columns(self, table_name: str) -> list[dict]:
        """Return the fields available for a given project+issue type."""
        project_key, issue_type = self._parse_table_name(table_name)
        if not project_key:
            return []

        columns: dict[str, dict] = {}
        try:
            meta = self.jira.createmeta(
                projectKeys=project_key,
                issuetypeNames=issue_type or None,
                expand="projects.issuetypes.fields",
            )
        except Exception:
            # Let the orchestrator's RPC view surface this as a real error
            # (502 with detail) instead of silently returning only the
            # synthetic status row — which the UI used to render as a
            # "1-row mapper" with no signal that the underlying API call
            # had failed (expired token, missing scope, etc.).
            logger.warning(
                "Failed to fetch createmeta for project",
                project_key=project_key,
                issue_type=issue_type,
                exc_info=True,
            )
            raise

        for project in meta.get("projects", []) or []:
            for it in project.get("issuetypes", []) or []:
                if issue_type and it.get("name") != issue_type:
                    continue
                for field_id, field_def in (it.get("fields") or {}).items():
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
            meta = self.jira.createmeta(
                projectKeys=project_key,
                issuetypeNames=issue_type or None,
                expand="projects.issuetypes.fields",
            )
        except Exception:
            logger.warning(
                "Failed to fetch createmeta for choices",
                project_key=project_key,
                issue_type=issue_type,
                field_name=field_name,
                exc_info=True,
            )
            return []

        for project in meta.get("projects", []) or []:
            for it in project.get("issuetypes", []) or []:
                if issue_type and it.get("name") != issue_type:
                    continue
                field_def = (it.get("fields") or {}).get(field_name)
                if not field_def:
                    continue
                allowed = field_def.get("allowedValues") or []
                results = []
                for entry in allowed:
                    value = entry.get("value") or entry.get("name") or entry.get("id")
                    label = entry.get("name") or entry.get("value") or value
                    if value is None:
                        continue
                    results.append({"value": value, "label": label})
                return results
        return []
