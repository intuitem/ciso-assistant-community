from core.models import AppliedControl
from integrations.base import BaseIntegrationClient
from .mapper import JiraFieldMapper
from jira import JIRA
from typing import Dict, Any
from structlog import get_logger
from icecream import ic

logger = get_logger(__name__)


class JiraClient(BaseIntegrationClient):
    def __init__(self, configuration):
        super().__init__(configuration)
        self.jira = JIRA(
            server=self.credentials["server_url"],
            basic_auth=(self.credentials["email"], self.credentials["api_token"]),
        )
        self.mapper = JiraFieldMapper(configuration)

    def create_remote_object(self, local_object: AppliedControl):
        issue_dict = self.mapper.to_remote(local_object)
        issue_dict["project"] = {"key": self.settings["project_key"]}
        issue_dict["issuetype"] = {"name": self.settings.get("issue_type", "Task")}

        issue = self.jira.create_issue(fields=issue_dict)
        logger.info(f"Created Jira issue {issue.key}")
        return issue.key

    def update_remote_object(self, remote_id, changes):
        try:
            issue = self.jira.issue(remote_id)
            issue.update(fields=changes)
            logger.info(f"Updated Jira issue {remote_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update Jira issue {remote_id}: {e}")
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

    def register_webhook(self, callback_url: str) -> Dict[str, Any]:
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
        try:
            self.jira.myself()
            return True
        except Exception as e:
            logger.error(f"Jira connection test failed: {e}")
            return False

