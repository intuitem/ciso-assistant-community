import pytest
from unittest.mock import MagicMock, patch
from core.models import AppliedControl
from integrations.models import IntegrationConfiguration
from .client import JiraClient
from .mapper import JiraFieldMapper


@pytest.fixture
def configuration():
    mock_config = MagicMock(spec=IntegrationConfiguration)
    mock_config.credentials = {
        "server": "https://your-jira-instance.atlassian.net",
        "email": "user@example.com",
        "api_token": "your-api-token",
    }
    mock_config.settings = {"project_key": "PROJ", "issue_type": "Task"}
    return mock_config


@pytest.fixture
def mapper(configuration):
    return JiraFieldMapper(configuration)


@patch("integrations.itsm.jira.client.JIRA")
def test_applied_control_to_jira_issue(mock_jira, mapper):
    applied_control = AppliedControl(
        name="Test Control",
        description="Test Description",
        status="in_progress",
        priority=2,
    )

    jira_issue_dict = mapper.to_remote(applied_control)

    assert jira_issue_dict["summary"] == "Test Control"
    assert (
        jira_issue_dict["description"]["content"][0]["content"][0]["text"]
        == "Test Description"
    )
    assert jira_issue_dict["status"]["name"] == "In Progress"
    assert jira_issue_dict["priority"]["name"] == "High"


@patch("integrations.itsm.jira.client.JIRA")
def test_create_jira_issue(mock_jira, configuration):
    mock_issue = MagicMock()
    mock_issue.key = "PROJ-123"
    mock_jira.return_value.create_issue.return_value = mock_issue

    client = JiraClient(configuration)

    applied_control = AppliedControl(
        name="Test Control",
        description="Test Description",
        status="in_progress",
        priority=2,
    )

    issue_key = client.create_remote_object(applied_control)

    assert issue_key == "PROJ-123"
    mock_jira.return_value.create_issue.assert_called_once()


@patch("integrations.itsm.jira.client.JIRA")
def test_get_remote_object(mock_jira, configuration):
    mock_issue = MagicMock()
    mock_issue.key = "PROJ-123"
    mock_issue.raw = {"fields": {"summary": "Test Summary"}}
    mock_issue.fields.updated = "2025-10-21T10:00:00.000Z"
    mock_jira.return_value.issue.return_value = mock_issue

    client = JiraClient(configuration)
    issue = client.get_remote_object("PROJ-123")

    assert issue["key"] == "PROJ-123"
    assert issue["fields"]["summary"] == "Test Summary"


@patch("integrations.itsm.jira.client.JIRA")
def test_test_connection(mock_jira, configuration):
    mock_jira.return_value.myself.return_value = True

    client = JiraClient(configuration)
    assert client.test_connection() is True
