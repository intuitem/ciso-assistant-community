import pytest
from types import SimpleNamespace
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
        folder_id=None,
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
        folder_id=None,
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
        folder_id=None,
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

    applied_control = AppliedControl(
        folder_id=None, name="Original Name", status="in_progress"
    )

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


# Dynamic mapping (settings.field_map / value_map) tests


@pytest.fixture
def dynamic_configuration():
    """Configuration that overrides the legacy hardcoded defaults via settings."""
    mock_config = MagicMock(spec=IntegrationConfiguration)
    mock_config.credentials = {
        "server_url": "https://your-jira-instance.atlassian.net",
        "email": "user@example.com",
        "api_token": "your-api-token",
    }
    mock_config.settings = {
        "table_name": "PROJ:Task",
        "field_map": {
            "name": "summary",
            "description": "customfield_10100",
            "status": "status",
            "priority": "priority",
            "eta": "duedate",
            "ref_id": "customfield_10001",
        },
        "value_map": {
            "status": {
                "to_do": "Backlog",
                "in_progress": "Doing",
                "active": "Doing",
                "on_hold": "Blocked",
                "deprecated": "Done",
            },
            "priority": {
                "1": "Highest",
                "2": "High",
                "3": "Medium",
                "4": "Lowest",
            },
        },
    }
    return mock_config


@pytest.fixture
def dynamic_mapper(dynamic_configuration):
    return JiraFieldMapper(dynamic_configuration)


def test_dynamic_field_and_value_maps_drive_remote_payload(dynamic_mapper):
    """User-configured maps take precedence over the legacy hardcoded defaults."""
    applied_control = AppliedControl(
        folder_id=None,
        name="Custom Control",
        description="Long form description",
        status="in_progress",
        priority=4,
        ref_id="AC-42",
    )

    remote = dynamic_mapper.to_remote(applied_control)

    assert remote["summary"] == "Custom Control"
    # description maps to a non-Atlassian-document custom field; stays a plain string
    assert remote["customfield_10100"] == "Long form description"
    # status is popped by the client and used for a workflow transition
    assert remote["status"] == "Doing"
    # priority remains wrapped because the remote field is Jira's system priority
    assert remote["priority"] == {"name": "Lowest"}
    assert remote["customfield_10001"] == "AC-42"


def test_dynamic_to_local_uses_reverse_value_map(dynamic_mapper):
    """Pulling honors the user's value mapping, including non-default status names."""
    remote_data = {
        "fields": {
            "summary": "Custom Control",
            "status": {"name": "Blocked"},
            "priority": {"name": "High"},
        }
    }

    local = dynamic_mapper.to_local(remote_data)

    assert local["status"] == "on_hold"
    assert local["priority"] == 2


def test_dynamic_partial_update_drops_disallowed_fields(dynamic_mapper):
    """Push-update respects FIELD_MAPPINGS_OPERATIONS even with custom field_map."""
    applied_control = AppliedControl(folder_id=None, name="Renamed", status="active")

    remote = dynamic_mapper.to_remote_partial(applied_control, ["name", "status"])

    # 'name' is push-update allowed, so summary is updated
    assert remote["summary"] == "Renamed"
    # 'active' maps to 'Doing' per the dynamic value map
    assert remote["status"] == "Doing"


def test_legacy_fallback_when_settings_have_no_maps(configuration):
    """Existing configs without field_map/value_map keep the legacy behavior."""
    mapper = JiraFieldMapper(configuration)

    assert mapper.field_map == JiraFieldMapper._DEFAULT_FIELD_MAP
    assert "status" in mapper.value_map_to_remote
    # Reverse map should be derivable
    assert mapper.value_map_to_local["status"]["In Progress"] == "in_progress"


def test_status_case_insensitive_fallback(configuration):
    """Legacy lowercase Jira status payloads still resolve via fallback."""
    mapper = JiraFieldMapper(configuration)

    # Jira sometimes returns names with different casing depending on the workflow
    assert (
        mapper._transform_value_to_local("status", {"name": "in progress"})
        == "in_progress"
    )


def test_description_adf_only_when_mapped_to_description_field(dynamic_mapper):
    """ADF wrapping is reserved for Jira's native description field."""
    applied_control = AppliedControl(folder_id=None, description="Hello world")

    remote = dynamic_mapper.to_remote(applied_control)

    # Mapped to a custom field, so we keep it as a plain string
    assert remote["customfield_10100"] == "Hello world"
    assert "description" not in remote


# Choice scoping tests (status/priority must come from the selected project only)


@patch("integrations.itsm.jira.client.JIRA")
def test_status_choices_scoped_to_project_issue_type(mock_jira, configuration):
    """Status choices come from the selected project + issue type, not the whole instance."""
    mock_jira.return_value.issue_types_for_project.return_value = [
        SimpleNamespace(
            name="Task",
            statuses=[
                SimpleNamespace(name="To Do"),
                SimpleNamespace(name="In Progress"),
            ],
        ),
        SimpleNamespace(
            name="Bug",
            statuses=[SimpleNamespace(name="Triage")],
        ),
    ]

    client = JiraClient(configuration)
    choices = client.get_field_choices("PROJ:Task", "status")

    assert [c["value"] for c in choices] == ["In Progress", "To Do"]
    mock_jira.return_value.issue_types_for_project.assert_called_once_with("PROJ")
    # The instance-wide endpoint must NOT be used.
    mock_jira.return_value.statuses.assert_not_called()


@patch("integrations.itsm.jira.client.JIRA")
def test_status_choices_union_across_issue_types_when_unspecified(
    mock_jira, configuration
):
    """With no issue type pinned, statuses from every issue type are returned (deduped)."""
    mock_jira.return_value.issue_types_for_project.return_value = [
        SimpleNamespace(name="Task", statuses=[SimpleNamespace(name="To Do")]),
        SimpleNamespace(
            name="Bug",
            statuses=[SimpleNamespace(name="To Do"), SimpleNamespace(name="Triage")],
        ),
    ]

    client = JiraClient(configuration)
    choices = client.get_field_choices("PROJ", "status")

    assert [c["value"] for c in choices] == ["To Do", "Triage"]


@patch("integrations.itsm.jira.client.JIRA")
def test_priority_choices_scoped_via_createmeta(mock_jira, configuration):
    """Priority choices respect the project's priority scheme via createmeta allowedValues."""
    mock_jira.return_value.createmeta.return_value = {
        "projects": [
            {
                "issuetypes": [
                    {
                        "name": "Task",
                        "fields": {
                            "priority": {
                                "allowedValues": [
                                    {"name": "High"},
                                    {"name": "Low"},
                                ]
                            }
                        },
                    }
                ]
            }
        ]
    }

    client = JiraClient(configuration)
    choices = client.get_field_choices("PROJ:Task", "priority")

    assert [c["value"] for c in choices] == ["High", "Low"]
    # Instance-wide priorities endpoint must NOT be used when the project scopes them.
    mock_jira.return_value.priorities.assert_not_called()


@patch("integrations.itsm.jira.client.JIRA")
def test_priority_choices_fall_back_to_instance_when_createmeta_empty(
    mock_jira, configuration
):
    """If createmeta omits priority (not on create screen), fall back to instance priorities."""
    mock_jira.return_value.createmeta.return_value = {"projects": []}
    mock_jira.return_value.priorities.return_value = [
        SimpleNamespace(name="Highest"),
        SimpleNamespace(name="Medium"),
    ]

    client = JiraClient(configuration)
    choices = client.get_field_choices("PROJ:Task", "priority")

    assert [c["value"] for c in choices] == ["Highest", "Medium"]
    mock_jira.return_value.priorities.assert_called_once()
