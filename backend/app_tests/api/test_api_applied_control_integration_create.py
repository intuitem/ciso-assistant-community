"""Selecting an integration provider when creating an applied control queues
exactly one remote object creation, whether or not the model's save() already
pushes to that integration."""

from unittest.mock import MagicMock, patch

import pytest

from iam.models import Folder
from integrations.models import IntegrationConfiguration, IntegrationProvider

URL = "/api/applied-controls/"


def _jira_config(settings):
    provider, _ = IntegrationProvider.objects.get_or_create(
        name="jira", defaults={"provider_type": "itsm", "is_active": True}
    )
    return IntegrationConfiguration.objects.create(
        provider=provider,
        folder=Folder.get_root_folder(),
        is_active=True,
        credentials={
            "server_url": "https://example.atlassian.net",
            "email": "u@example.com",
            "api_token": "t",
        },
        settings={"enable_outgoing_sync": True, **settings},
    )


def _create(client, config, captured):
    task = MagicMock()
    with (
        patch("core.views.sync_object_to_integrations", task),
        patch("integrations.tasks.sync_object_to_integrations", task),
        captured(execute=True),
    ):
        resp = client.post(
            URL,
            {
                "name": "Control",
                "folder": str(Folder.get_root_folder().id),
                "integration_config": str(config.id),
            },
            format="json",
        )
    assert resp.status_code == 201, resp.content
    return task


@pytest.mark.django_db
def test_no_duplicate_when_save_already_syncs(
    authenticated_client, django_capture_on_commit_callbacks
):
    config = _jira_config({"project_key": "CA"})

    task = _create(authenticated_client, config, django_capture_on_commit_callbacks)

    task.schedule.assert_called_once()
    assert task.schedule.call_args.kwargs["args"][2] == [config.id]


@pytest.mark.django_db
def test_explicit_creation_when_save_does_not_sync(
    authenticated_client, django_capture_on_commit_callbacks
):
    config = _jira_config({})

    task = _create(authenticated_client, config, django_capture_on_commit_callbacks)

    task.schedule.assert_called_once()
    assert task.schedule.call_args.kwargs["args"][2] == [config.id]
