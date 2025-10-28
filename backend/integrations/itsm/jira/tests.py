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
        "server_url": "https://your-jira-instance.atlassian.net",
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
    assert jira_issue_dict["status"] == "In Progress"
    assert jira_issue_dict["priority"]["name"] == "High"


@patch("integrations.itsm.jira.client.JIRA")
def test_create_jira_issue(mock_jira, configuration):
    mock_issue = MagicMock()
    mock_issue.key = "PROJ-123"
    mock_jira.return_value.create_issue.return_value = mock_issue
    mock_jira.return_value.transitions.return_value = [
        {"id": "1", "to": {"name": "To Do"}},
        {"id": "2", "to": {"name": "In Progress"}},
    ]

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
    mock_jira.return_value.transition_issue.assert_called_with("PROJ-123", "2")


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








def test_to_remote_create_respects_operations(mapper):


    """Ensure `to_remote` for creation only includes fields for push-create."""


    applied_control = AppliedControl(


        name="New Control",


        description="Full description",


        status="to_do",


        priority=1,


        eta="2025-12-31",


    )





    # Modify operations to exclude description on create


    mapper.FIELD_MAPPINGS_OPERATIONS["description"]["push"].remove("create")





    remote_data = mapper.to_remote(applied_control)





    assert "summary" in remote_data  # Name is allowed


    assert "description" not in remote_data  # Description is disallowed


    assert "status" in remote_data


    assert "priority" in remote_data


    assert "duedate" in remote_data





    # Restore for other tests


    mapper.FIELD_MAPPINGS_OPERATIONS["description"]["push"].add("create")








def test_to_remote_partial_update_respects_operations(mapper):


    """Ensure `to_remote_partial` for updates only includes allowed fields."""


    applied_control = AppliedControl(name="Original Name", status="in_progress")


    changed_fields = ["name", "status"]





    # Disallow updating name via push


    mapper.FIELD_MAPPINGS_OPERATIONS["name"]["push"].remove("update")





    remote_data = mapper.to_remote_partial(applied_control, changed_fields)





    assert "summary" not in remote_data  # Name update should be excluded


    assert "status" in remote_data  # Status update is allowed





    # Restore for other tests


    mapper.FIELD_MAPPINGS_OPERATIONS["name"]["push"].add("update")





def test_to_local_pull_update_respects_operations(mapper):


    """Ensure `to_local` for pull updates only includes allowed fields."""


    remote_data = {


        "fields": {


            "summary": "Remote Name",


            "description": "Remote Description",


            "status": {"name": "In Progress"},


            "priority": {"name": "High"},


        }


    }





    local_data = mapper.to_local(remote_data)





    assert "name" not in local_data


    assert "description" not in local_data


    assert "status" in local_data  # Status is allowed


    assert "priority" in local_data  # Priority is allowed












