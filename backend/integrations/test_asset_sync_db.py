"""DB-backed tests for Asset sync wiring (model routing, skip_sync, no-create)."""

from unittest.mock import MagicMock, patch

import pytest

from core.models import Asset
from iam.models import Folder
from integrations.itsm.servicenow.integration import ServiceNowOrchestrator
from integrations.models import (
    IntegrationConfiguration,
    IntegrationProvider,
    SyncMapping,
)


@pytest.fixture
def root_folder(db):
    folder, _ = Folder.objects.get_or_create(
        content_type=Folder.ContentType.ROOT, defaults={"name": "Global"}
    )
    return folder


@pytest.fixture
def servicenow_provider(db):
    provider, _ = IntegrationProvider.objects.get_or_create(
        name="servicenow", provider_type="itsm"
    )
    return provider


def _config(provider, models_settings):
    return IntegrationConfiguration.objects.create(
        provider=provider,
        credentials={
            "instance_url": "https://example.service-now.com",
            "username": "u",
            "password": "p",
        },
        settings={
            "enable_outgoing_sync": True,
            "enable_incoming_sync": True,
            "models": models_settings,
        },
        webhook_secret="secret",
    )


def _mock_client():
    client = MagicMock()
    client.create_remote_object.return_value = "SYS-1"
    client.get_remote_object.return_value = {"key": "SYS-1", "fields": {}}
    return client


def test_asset_save_accepts_skip_sync(root_folder):
    asset = Asset.objects.create(name="DB Server", folder=root_folder, type="PR")
    # The inbound pull path saves with skip_sync=True; must not raise.
    asset.name = "DB Server 2"
    asset.save(skip_sync=True)
    asset.refresh_from_db()
    assert asset.name == "DB Server 2"


def test_push_routes_to_asset_mapper_and_table(root_folder, servicenow_provider):
    config = _config(
        servicenow_provider,
        {"asset": {"table_name": "cmdb_ci", "field_map": {"name": "u_name"}}},
    )
    asset = Asset.objects.create(name="DB Server", folder=root_folder, type="PR")
    client = _mock_client()

    with patch.object(ServiceNowOrchestrator, "_get_client", return_value=client):
        orchestrator = ServiceNowOrchestrator(config)
        result = orchestrator.push_changes(asset, ["name"])

    assert result is True
    client.create_remote_object.assert_called_once_with(asset)
    mapping = SyncMapping.objects.get(configuration=config)
    assert mapping.remote_id == "SYS-1"
    assert mapping.content_type.model == "asset"


def test_push_skips_when_model_not_configured(root_folder, servicenow_provider):
    # Config mapped only for applied_control: an Asset push must be skipped.
    config = _config(
        servicenow_provider,
        {"applied_control": {"table_name": "incident", "field_map": {"name": "x"}}},
    )
    asset = Asset.objects.create(name="DB Server", folder=root_folder, type="PR")
    client = _mock_client()

    with patch.object(ServiceNowOrchestrator, "_get_client", return_value=client):
        orchestrator = ServiceNowOrchestrator(config)
        result = orchestrator.push_changes(asset, ["name"])

    assert result is False
    client.create_remote_object.assert_not_called()
    assert not SyncMapping.objects.filter(configuration=config).exists()


def test_pull_for_unlinked_remote_creates_no_asset(root_folder, servicenow_provider):
    config = _config(
        servicenow_provider,
        {"asset": {"table_name": "cmdb_ci", "field_map": {"name": "u_name"}}},
    )
    before = Asset.objects.count()
    client = _mock_client()

    with patch.object(ServiceNowOrchestrator, "_get_client", return_value=client):
        orchestrator = ServiceNowOrchestrator(config)
        result = orchestrator.pull_changes(
            "UNKNOWN-SYS-ID", {"fields": {"u_name": "X"}}
        )

    assert result is False
    assert Asset.objects.count() == before


def test_pull_updates_linked_asset(root_folder, servicenow_provider):
    from django.contrib.contenttypes.models import ContentType

    config = _config(
        servicenow_provider,
        {"asset": {"table_name": "cmdb_ci", "field_map": {"name": "u_name"}}},
    )
    asset = Asset.objects.create(name="Old name", folder=root_folder, type="PR")
    SyncMapping.objects.create(
        configuration=config,
        content_type=ContentType.objects.get_for_model(Asset),
        local_object_id=asset.id,
        remote_id="SYS-9",
        sync_status=SyncMapping.SyncStatus.SYNCED,
    )
    client = _mock_client()

    with patch.object(ServiceNowOrchestrator, "_get_client", return_value=client):
        orchestrator = ServiceNowOrchestrator(config)
        result = orchestrator.pull_changes("SYS-9", {"fields": {"u_name": "New name"}})

    assert result is True
    asset.refresh_from_db()
    assert asset.name == "New name"
