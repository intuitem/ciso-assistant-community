from typing import Any, Dict
from icecream import ic

from integrations.models import SyncMapping
from jira import JIRA
from structlog import get_logger

from core.models import AppliedControl
from integrations.base import BaseIntegrationClient

from .mapper import JiraFieldMapper

logger = get_logger(__name__)


class JiraClient(BaseIntegrationClient):
    def __init__(self, configuration):
        """
        Initialize the JiraClient using the provided integration configuration.
        
        Parameters:
            configuration: Integration configuration object containing settings and credentials.
                Must include credentials with keys "server_url", "email", and "api_token"; used to create the Jira API client and to instantiate the JiraFieldMapper.
        """
        super().__init__(configuration)
        self.jira = JIRA(
            server=self.credentials["server_url"],
            basic_auth=(self.credentials["email"], self.credentials["api_token"]),
        )
        self.mapper = JiraFieldMapper(configuration)

    def create_remote_object(self, local_object: AppliedControl):
        """
        Create a Jira issue from a local AppliedControl and apply an optional status transition.
        
        The local object is mapped to Jira fields, the configured project key and issue type are applied, and a Jira issue is created. If the mapped data includes a `status` value, the newly created issue will be transitioned to that status.
        
        Parameters:
            local_object (AppliedControl): The local object to be converted into a Jira issue.
        
        Returns:
            str: The key of the created Jira issue (e.g., "PROJ-123").
        """
        issue_dict = self.mapper.to_remote(local_object)
        issue_dict["project"] = {"key": self.settings["project_key"]}
        issue_dict["issuetype"] = {"name": self.settings.get("issue_type", "Task")}

        target_status_name = issue_dict.pop("status")

        issue = self.jira.create_issue(fields=issue_dict)

        # Handle the status transition separately
        if target_status_name:
            self._transition_issue_to_status(issue.key, target_status_name)

        logger.info(f"Created Jira issue {issue.key}")
        return issue.key

    def update_remote_object(self, remote_id: str, changes: dict[str, Any]) -> bool:
        """
        Update a Jira issue's fields and, if provided, transition the issue to a target status.
        
        Parameters:
            remote_id (str): The Jira issue identifier (e.g., "PROJ-123").
            changes (dict[str, Any]): Mapping of Jira field keys to new values. If the mapping contains a key "status", its value is treated as the target status name and will be applied via a workflow transition rather than a direct field update; all other keys are applied as normal field updates.
        
        Returns:
            bool: `True` if the update (and any status transition) completed successfully.
        """
        try:
            # Status must be handled as a transition, not an edit.
            target_status_name = None
            if "status" in changes:
                # 1. Pop the status from the changes dict
                target_status_name = changes.pop("status")

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
        Transition the Jira issue to a specified workflow status.
        
        If a workflow transition exists whose destination status name matches the provided
        target status name (case-insensitive), execute that transition on the issue.
        If no matching transition is available or the transition fails, an exception is
        raised and the issue is left unchanged.
        
        Parameters:
            remote_id (str): The Jira issue identifier or key.
            target_status_name (str): Desired destination status name to transition the issue to.
        
        Raises:
            Exception: If no matching transition is found or if executing the transition fails.
        """
        try:
            # Get all available transitions for the issue
            transitions = self.jira.transitions(remote_id)

            # Find the transition ID that leads to the target status
            transition_id = None
            available_statuses = []
            for t in transitions:
                # t['to']['name'] is the name of the status this transition moves to
                available_statuses.append(t["to"]["name"])
                if t["to"]["name"].lower() == target_status_name.lower():
                    transition_id = t["id"]
                    break  # Found it

            if transition_id:
                # Execute the transition
                self.jira.transition_issue(remote_id, transition_id)
                logger.info(
                    f"Transitioned Jira issue {remote_id} to status '{target_status_name}'"
                )
            else:
                # No transition found
                logger.error(
                    f"No available transition for issue {remote_id} to status '{target_status_name}'. "
                    f"Available transitions are for: {available_statuses}"
                )
                # Raise an exception so the sync fails and logs the error
                raise Exception(
                    f"Invalid status transition: No workflow path to '{target_status_name}'. "
                    f"Available targets: {available_statuses}"
                )

        except Exception as e:
            logger.error(f"Failed to transition Jira issue {remote_id}: {e}")
            raise  # Re-raise the exception

    def get_remote_object(self, remote_id: str) -> Dict[str, Any]:
        """
        Retrieve a Jira issue and return its identifying key, raw fields, and last-updated timestamp.
        
        Parameters:
            remote_id (str): Jira issue identifier (key or ID) to fetch.
        
        Returns:
            dict: A mapping containing:
                - "key" (str): the issue key.
                - "fields" (dict): the raw fields object returned by Jira.
                - "updated": the issue's updated timestamp as provided by Jira.
        """
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

    def register_webhook(self, callback_url: str) -> Dict[str, Any]:
        """
        Register a Jira webhook for issue-created, issue-updated, and issue-deleted events scoped to the configured project.
        
        Parameters:
            callback_url (str): The HTTP(S) URL that Jira will call when webhook events occur.
        
        Returns:
            Dict[str, Any]: The created webhook representation returned by Jira (parsed JSON).
        
        Raises:
            requests.HTTPError: If the Jira API responds with an error status.
        """
        webhook_data = {
            "name": "Django Integration Webhook",
            "url": callback_url,
            "events": [
                "jira:issue_created",
                "jira:issue_updated",
                "jira:issue_deleted",
            ],
            "filters": {
                "issue-related-events-section": f"project = {self.settings['project_key']}"
            },
        }

        response = self.jira._session.post(
            f"{self.credentials['server_url']}/rest/webhooks/1.0/webhook",
            json=webhook_data,
        )
        response.raise_for_status()

        webhook = response.json()
        logger.info(f"Registered Jira webhook: {webhook.get('self')}")
        return webhook

    def unregister_webhook(self, webhook_id: str) -> bool:
        """
        Unregister the Jira webhook identified by `webhook_id` from the configured Jira instance.
        
        Parameters:
            webhook_id (str): The identifier of the webhook to remove.
        
        Returns:
            bool: `True` if the webhook was successfully unregistered, `False` otherwise.
        """
        try:
            response = self.jira._session.delete(
                f"{self.credentials['server_url']}/rest/webhooks/1.0/webhook/{webhook_id}"
            )
            response.raise_for_status()
            logger.info(f"Unregistered Jira webhook: {webhook_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister Jira webhook {webhook_id}: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Check whether the configured Jira client can successfully reach the Jira server.
        
        Attempts to retrieve Jira context via the client's "myself" endpoint to verify connectivity.
        
        Returns:
            bool: `True` if connection is successful, `False` otherwise.
        """
        try:
            self.jira.myself()
            return True
        except Exception as e:
            logger.error(f"Jira connection test failed: {e}")
            return False

    def list_remote_objects(
        self, query_params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Return a list of Jira issues for the configured project.
        
        Parameters:
            query_params (dict[str, Any] | None): Optional query options. Recognized keys:
                - start_at (int): Zero-based index of first item in the returned batch (default 0).
                - max_results (int): Maximum number of issues to retrieve (default 10000).
        
        Returns:
            list[dict[str, Any]]: A list of issue dictionaries with keys:
                - "key": issue key (str)
                - "id": issue id (str)
                - "summary": issue summary (str)
        
        Raises:
            ConnectionError: If the Jira client has not been initialized.
            ValueError: If a project_key is not configured in settings.
            Exception: Re-raises any exception encountered while querying Jira.
        """
        if not self.jira:
            raise ConnectionError("Jira client not initialized.")
        if query_params is None:
            query_params = {}

        # Base JQL: Always filter by the project key from settings
        project_key = self.settings.get("project_key")
        if not project_key:
            raise ValueError("Jira project_key is not configured in settings.")

        jql_query = f"project = {project_key}"

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
                # startAt=start_at,
                # maxResults=max_results,
                expand="fields",  # Important to get field data
            )

            # Format the results as a list of dictionaries (using the raw data)
            results_list = [
                {
                    "key": issue.raw["key"],
                    "id": issue.raw["id"],
                    "summary": issue.raw["fields"]["summary"],
                }
                for issue in issues
                if issue.raw["key"] not in used_issues  # Filter out already used issues
            ]
            logger.info(
                f"Fetched {len(results_list)} Jira issues for project {project_key} (batch starting at {start_at})."
            )
            return results_list

        except Exception as e:
            logger.error(f"Failed to search Jira issues: JQL='{jql_query}', Error={e}")
            raise