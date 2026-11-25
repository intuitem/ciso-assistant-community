"""Creating an applied control only touches the integration provider selected
in the form: a new remote object is created there, or the given remote object
is linked. Other configured integrations are left alone."""

from unittest.mock import MagicMock, patch

import pytest

from iam.models import Folder
from integrations.models import (
    IntegrationConfiguration,
    IntegrationProvider,
    SyncMapping,
)

URL = "/api/applied-controls/"


def _config(provider_name, settings):
    provider, _ = IntegrationProvider.objects.get_or_create(
        name=provider_name, defaults={"provider_type": "itsm", "is_active": True}
    )
    return IntegrationConfiguration.objects.create(
        provider=provider,
        folder=Folder.get_root_folder(),
        is_active=True,
        credentials={},
        settings={"enable_outgoing_sync": True, **settings},
    )


def _create(client, captured, **extra):
    task = MagicMock()
    with (
        patch("core.views.sync_object_to_integrations", task),
        patch("integrations.tasks.sync_object_to_integrations", task),
        captured(execute=True),
    ):
        resp = client.post(
            URL,
            {"name": "Control", "folder": str(Folder.get_root_folder().id), **extra},
            format="json",
        )
    assert resp.status_code == 201, resp.content
    return task, resp.json()["id"]


@pytest.mark.django_db
def test_creates_remote_object_in_selected_provider_only(
    authenticated_client, django_capture_on_commit_callbacks
):
    jira = _config("jira", {"project_key": "CA"})
    _config("servicenow", {"table_name": "incident"})

    task, _ = _create(
        authenticated_client,
        django_capture_on_commit_callbacks,
        integration_config=str(jira.id),
    )

    task.schedule.assert_called_once()
    assert task.schedule.call_args.kwargs["args"][2] == [jira.id]


@pytest.mark.django_db
def test_no_remote_object_without_selected_provider(
    authenticated_client, django_capture_on_commit_callbacks
):
    _config("jira", {"project_key": "CA"})

    task, _ = _create(authenticated_client, django_capture_on_commit_callbacks)

    task.schedule.assert_not_called()


@pytest.mark.django_db
def test_remote_object_id_links_existing_object(
    authenticated_client, django_capture_on_commit_callbacks
):
    jira = _config("jira", {"project_key": "CA"})

    task, control_id = _create(
        authenticated_client,
        django_capture_on_commit_callbacks,
        integration_config=str(jira.id),
        remote_object_id="CA-1",
    )

    mapping = SyncMapping.objects.get(local_object_id=control_id)
    assert mapping.configuration == jira
    assert mapping.remote_id == "CA-1"
    task.schedule.assert_called_once()
    assert task.schedule.call_args.kwargs["args"][2] == [jira.id]
