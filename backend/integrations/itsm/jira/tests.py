import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from jira import JIRAError
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
    # REST v2 expects a plain-string description (not ADF).
    assert jira_issue_dict["description"] == "Test Description"
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

    assert "name" not in local_data  # Name is not pulled on update

    assert local_data["description"] == "Remote Description"  # Pulled on update

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


def test_description_is_plain_string_for_custom_field(dynamic_mapper):
    """A description mapped to a custom field is sent as a plain string."""
    applied_control = AppliedControl(folder_id=None, description="Hello world")

    remote = dynamic_mapper.to_remote(applied_control)

    assert remote["customfield_10100"] == "Hello world"
    assert "description" not in remote


def test_native_description_is_plain_string(configuration):
    """Native ``description`` is a plain string, not ADF (REST v2 rejects ADF)."""
    mapper = JiraFieldMapper(configuration)
    applied_control = AppliedControl(folder_id=None, description="Hello world")

    remote = mapper.to_remote(applied_control)

    assert remote["description"] == "Hello world"


def test_undefined_status_is_not_pushed(configuration):
    """The ``--`` (UNDEFINED) status sentinel is dropped instead of pushed."""
    mapper = JiraFieldMapper(configuration)
    applied_control = AppliedControl(
        folder_id=None, name="No status control", status="--"
    )

    remote = mapper.to_remote(applied_control)

    assert "status" not in remote


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_filters_by_issue_type(mock_jira, mock_sync, configuration):
    """Listing linkable issues is scoped to the configured project AND issue type."""
    mock_jira.return_value.search_issues.return_value = []
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    client.list_remote_objects()

    jql = mock_jira.return_value.search_issues.call_args[0][0]
    assert "project = PROJ" in jql
    assert 'issuetype = "Task"' in jql


def test_degraded_status_round_trips(configuration):
    """The ``degraded`` status maps to/from Jira via the default value map."""
    mapper = JiraFieldMapper(configuration)

    applied_control = AppliedControl(folder_id=None, status="degraded")
    remote = mapper.to_remote(applied_control)
    assert remote["status"] == "Degraded"

    local = mapper.to_local({"fields": {"status": {"name": "Degraded"}}})
    assert local["status"] == "degraded"


@patch("integrations.itsm.jira.client.JIRA")
def test_create_jira_issue_skips_blank_status(mock_jira, configuration):
    """Creating an issue with an undefined status performs no status transition."""
    mock_issue = MagicMock()
    mock_issue.key = "PROJ-200"
    mock_jira.return_value.create_issue.return_value = mock_issue

    client = JiraClient(configuration)
    applied_control = AppliedControl(
        folder_id=None, name="No status control", status="--"
    )

    issue_key = client.create_remote_object(applied_control)

    assert issue_key == "PROJ-200"
    mock_jira.return_value.transitions.assert_not_called()
    mock_jira.return_value.transition_issue.assert_not_called()


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


def _fake_issue(key, issue_id, summary):
    issue = MagicMock()
    issue.raw = {"key": key, "id": issue_id, "fields": {"summary": summary}}
    return issue


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_passes_limit(mock_jira, mock_sync, configuration):
    """The picker limit caps the results; pages use a trimmed field set."""
    mock_jira.return_value.search_issues.return_value = [
        _fake_issue(f"PROJ-{i}", str(i), f"Issue {i}") for i in range(30)
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    results = client.list_remote_objects({"limit": 20})

    assert len(results) == 20
    kwargs = mock_jira.return_value.search_issues.call_args[1]
    assert kwargs["fields"] == "summary"


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_searches_summaries(mock_jira, mock_sync, configuration):
    """A free-text term becomes a summary clause, without any key clause."""
    mock_jira.return_value.search_issues.return_value = []
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    client.list_remote_objects({"search": "physical entry"})

    jql = mock_jira.return_value.search_issues.call_args[0][0]
    assert 'summary ~ "physical entry*"' in jql
    assert "key =" not in jql
    assert jql.endswith("ORDER BY created DESC")


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_search_matches_issue_key(
    mock_jira, mock_sync, configuration
):
    """A key-shaped term also matches on the issue key."""
    mock_jira.return_value.search_issues.return_value = []
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    client.list_remote_objects({"search": "ciso-40"})

    jql = mock_jira.return_value.search_issues.call_args[0][0]
    assert 'key = "CISO-40"' in jql
    # The hyphen is a Lucene special, replaced by a space in the summary clause.
    assert 'summary ~ "ciso 40*"' in jql


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_digit_search_targets_project_key(
    mock_jira, mock_sync, configuration
):
    """A digit-only term is completed with the configured project key."""
    mock_jira.return_value.search_issues.return_value = []
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    client.list_remote_objects({"search": "40"})

    jql = mock_jira.return_value.search_issues.call_args[0][0]
    assert 'key = "PROJ-40"' in jql


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_key_clause_falls_back_on_jql_error(
    mock_jira, mock_sync, configuration
):
    """Jira 400s on a nonexistent key in JQL; retry without the key clause."""
    mock_jira.return_value.search_issues.side_effect = [
        JIRAError(status_code=400, text="An issue with key 'PROJ-9999' does not exist"),
        [_fake_issue("PROJ-1", "1", "Something 9999")],
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    results = client.list_remote_objects({"search": "9999"})

    assert [r["key"] for r in results] == ["PROJ-1"]
    retry_jql = mock_jira.return_value.search_issues.call_args[0][0]
    assert "key =" not in retry_jql
    assert 'summary ~ "9999*"' in retry_jql


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_key_clause_propagates_non_jql_errors(
    mock_jira, mock_sync, configuration
):
    """A 429/timeout during the key search is a real error, not a missing
    key: it must not silently degrade to the summary-only fallback."""
    mock_jira.return_value.search_issues.side_effect = JIRAError(
        status_code=429, text="Rate limited"
    )
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    with pytest.raises(JIRAError):
        client.list_remote_objects({"search": "9999"})

    mock_jira.return_value.search_issues.assert_called_once()


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_sanitizes_jql_term(mock_jira, mock_sync, configuration):
    """Quotes and backslashes in the term cannot break out of the JQL string."""
    mock_jira.return_value.search_issues.return_value = []
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    client.list_remote_objects({"search": 'a"b\\c'})

    jql = mock_jira.return_value.search_issues.call_args[0][0]
    assert 'summary ~ "a b c*"' in jql


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_strips_lucene_specials(
    mock_jira, mock_sync, configuration
):
    """Lucene-reserved characters would 400 (and can never match: the text
    index drops punctuation), so they become spaces."""
    mock_jira.return_value.search_issues.return_value = []
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    client.list_remote_objects({"search": "A.7.1 (review)*?"})

    jql = mock_jira.return_value.search_issues.call_args[0][0]
    assert 'summary ~ "A.7.1 review*"' in jql


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_punctuation_only_search_returns_nothing(mock_jira, mock_sync, configuration):
    """A term that sanitizes to nothing matches nothing, not everything."""
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    results = client.list_remote_objects({"search": "*?("})

    assert results == []
    mock_jira.return_value.search_issues.assert_not_called()


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_excludes_mapped_issues(
    mock_jira, mock_sync, configuration
):
    """Issues already linked through a SyncMapping are not offered again."""
    mock_jira.return_value.search_issues.return_value = [
        _fake_issue("PROJ-1", "1", "Linked"),
        _fake_issue("PROJ-2", "2", "Free"),
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = ["PROJ-1"]
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    results = client.list_remote_objects()

    assert [r["key"] for r in results] == ["PROJ-2"]


def _fake_hydrated_issue(key, issue_id, summary, project="PROJ", issue_type="Task"):
    issue = MagicMock()
    issue.key = key
    issue.id = issue_id
    issue.raw = {
        "key": key,
        "id": issue_id,
        "fields": {
            "summary": summary,
            "project": {"key": project},
            "issuetype": {"name": issue_type},
        },
    }
    return issue


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_remote_objects_hydrates_ids(mock_jira, mock_sync, configuration):
    """The id param fetches the given issues directly instead of searching."""
    mock_jira.return_value.issue.return_value = _fake_hydrated_issue(
        "PROJ-7", "7", "Selected issue"
    )
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = JiraClient(configuration)
    results = client.list_remote_objects({"id": "PROJ-7"})

    assert results == [{"key": "PROJ-7", "id": "7", "summary": "Selected issue"}]
    mock_jira.return_value.issue.assert_called_once_with(
        "PROJ-7", fields="summary,project,issuetype"
    )
    mock_jira.return_value.search_issues.assert_not_called()


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_hydration_rejects_out_of_scope_issues(mock_jira, mock_sync, configuration):
    """Hydration must not leak issues outside the configured project/type."""
    mock_jira.return_value.issue.side_effect = [
        _fake_hydrated_issue("OTHER-1", "1", "Other project", project="OTHER"),
        _fake_hydrated_issue("PROJ-2", "2", "Wrong type", issue_type="Epic"),
        _fake_hydrated_issue("PROJ-3", "3", "In scope"),
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = JiraClient(configuration)
    results = client.list_remote_objects({"id": "OTHER-1,PROJ-2,PROJ-3"})

    assert [r["key"] for r in results] == ["PROJ-3"]


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_hydration_caps_id_list(mock_jira, mock_sync, configuration):
    """The client never makes more than MAX_HYDRATION_IDS remote calls."""
    mock_jira.return_value.issue.return_value = _fake_hydrated_issue("PROJ-1", "1", "x")
    mock_sync.objects.filter.return_value.values_list.return_value = []
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    client.list_remote_objects({"id": ",".join(f"PROJ-{i}" for i in range(500))})

    assert mock_jira.return_value.issue.call_count == 20


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_hydration_rejects_malformed_ids(mock_jira, mock_sync, configuration):
    """Ids reach the REST path verbatim, so only key/numeric shapes pass."""
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = JiraClient(configuration)
    results = client.list_remote_objects(
        {"id": "../serverInfo,PROJ-1?expand=x,%2e%2e,search"}
    )

    assert results == []
    mock_jira.return_value.issue.assert_not_called()


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_hydration_skips_malformed_payloads(mock_jira, mock_sync, configuration):
    """A response without the expected fields is skipped, not a 500."""
    broken = MagicMock()
    broken.raw = {"key": "PROJ-1", "id": "1", "fields": {}}
    mock_jira.return_value.issue.side_effect = [
        broken,
        _fake_hydrated_issue("PROJ-2", "2", "Fine"),
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = []

    client = JiraClient(configuration)
    results = client.list_remote_objects({"id": "PROJ-1,PROJ-2"})

    assert [r["key"] for r in results] == ["PROJ-2"]


class _FakePage(list):
    """Stand-in for python-jira's ResultList: a list with a nextPageToken."""

    def __init__(self, items, token=None):
        super().__init__(items)
        self.nextPageToken = token


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_paginates_past_mapped_issues(mock_jira, mock_sync, configuration):
    """A first page full of mapped issues must not shrink the result below
    the limit while more selectable issues exist: that would flip the
    picker's lazy/eager probe to eager on a truncated list. (Data Center
    pages by startAt.)"""
    mapped = [f"PROJ-{i}" for i in range(100)]
    mock_jira.return_value.search_issues.side_effect = [
        [_fake_issue(key, key.split("-")[1], "Mapped") for key in mapped],
        [_fake_issue(f"PROJ-{i}", str(i), f"Issue {i}") for i in range(100, 160)],
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = mapped
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    results = client.list_remote_objects({"limit": 51})

    assert len(results) == 51
    assert not set(mapped) & {r["key"] for r in results}
    second_call = mock_jira.return_value.search_issues.call_args_list[1]
    assert second_call[1]["startAt"] == 100


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_paginates_with_cloud_page_tokens(mock_jira, mock_sync, configuration):
    """Jira Cloud pages via enhanced_search_issues and its nextPageToken;
    search_issues raises there for any non-zero startAt."""
    mapped = [f"PROJ-{i}" for i in range(100)]
    mock_jira.return_value._is_cloud = True
    mock_jira.return_value.enhanced_search_issues.side_effect = [
        _FakePage(
            [_fake_issue(key, key.split("-")[1], "Mapped") for key in mapped],
            token="page2",
        ),
        _FakePage(
            [_fake_issue(f"PROJ-{i}", str(i), f"Issue {i}") for i in range(100, 160)]
        ),
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = mapped

    client = JiraClient(configuration)
    results = client.list_remote_objects({"limit": 51})

    assert len(results) == 51
    assert not set(mapped) & {r["key"] for r in results}
    second_call = mock_jira.return_value.enhanced_search_issues.call_args_list[1]
    assert second_call[1]["nextPageToken"] == "page2"
    mock_jira.return_value.search_issues.assert_not_called()


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_deduplicates_issues_across_pages(mock_jira, mock_sync, configuration):
    """Issues created mid-scan shift the created DESC pages, so a key can
    show up on two consecutive pages; it must be returned once."""
    mapped = [f"PROJ-{i}" for i in range(99)]
    boundary = _fake_issue("PROJ-99", "99", "On both pages")
    mock_jira.return_value.search_issues.side_effect = [
        [_fake_issue(key, key.split("-")[1], "Mapped") for key in mapped] + [boundary],
        [boundary]
        + [_fake_issue(f"PROJ-{i}", str(i), f"Issue {i}") for i in range(100, 160)],
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = mapped
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    results = client.list_remote_objects({"limit": 51})

    keys = [r["key"] for r in results]
    assert len(keys) == 51
    assert len(set(keys)) == 51
    assert keys.count("PROJ-99") == 1


@patch("integrations.itsm.jira.client.SyncMapping")
@patch("integrations.itsm.jira.client.JIRA")
def test_list_scan_budget_bounds_pagination(mock_jira, mock_sync, configuration):
    """Paging past mapped issues stops at MAX_LIST_FETCH scanned rows."""
    mapped = [f"PROJ-{i}" for i in range(1000)]
    mock_jira.return_value.search_issues.side_effect = [
        [
            _fake_issue(key, key.split("-")[1], "Mapped")
            for key in mapped[i * 100 : (i + 1) * 100]
        ]
        for i in range(10)
    ]
    mock_sync.objects.filter.return_value.values_list.return_value = mapped
    mock_jira.return_value._is_cloud = False

    client = JiraClient(configuration)
    results = client.list_remote_objects({"limit": 51})

    assert results == []
    assert mock_jira.return_value.search_issues.call_count == 5
