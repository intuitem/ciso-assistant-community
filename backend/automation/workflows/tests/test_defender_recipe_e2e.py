import pytest
import yaml

from automation.workflows.engine import start_instance
from automation.workflows.import_export import import_workflow
from automation.workflows.models import WorkflowInstance
from automation.workflows.tests.helpers import publisher_user
from automation.workflows.tests.test_http_paging_oauth import (  # noqa: F401
    FakeResponse,
    tool,
)
from automation.workflows.tests.test_shipped_libraries import LIBRARY_DIR
from automation.workflows.tests.test_unreachable_tool import make_domain
from core.models import Asset


def defender_entry():
    path = LIBRARY_DIR / "workflow-operations-defender-device-inventory.yaml"
    entry = yaml.safe_load(path.read_text())["objects"]["workflows"][0]
    for variable in entry["graph"]["variables"]:
        variable["default_value"] = {"tenant_id": "contoso", "client_id": "app"}[
            variable["key"]
        ]
    return entry


def device(name, machine_id):
    return {
        "id": machine_id,
        "computerDnsName": name,
        "osPlatform": "Windows11",
        "version": "23H2",
        "exposureLevel": "Medium",
        "riskScore": "Low",
        "lastSeen": "2026-10-06T22:00:00Z",
    }


def machines(url):
    if "skiptoken" not in url:
        return FakeResponse(
            {
                "value": [device("laptop-1", "m1"), device("laptop-2", "m2")],
                "@odata.nextLink": url + "&$skiptoken=2",
            }
        )
    return FakeResponse({"value": [device("server-1", "m3")]})


@pytest.mark.django_db
def test_defender_recipe_keeps_one_asset_per_device(tool):  # noqa: F811
    tool["pages"]["handler"] = machines
    domain = make_domain("Defender")
    workflow, _ = import_workflow(
        defender_entry(),
        domain,
        user=publisher_user(),
        secrets={"defender_client_secret": "s3cret"},
    )
    version = workflow.draft_version
    version.run_as = publisher_user()
    version.save()

    for _ in range(2):
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED

    assets = Asset.objects.filter(folder=domain).order_by("name")
    assert [(a.name, a.ref_id, a.type) for a in assets] == [
        ("laptop-1", "m1", "SP"),
        ("laptop-2", "m2", "SP"),
        ("server-1", "m3", "SP"),
    ]
    assert "Windows11 23H2" in assets[0].description
    token_call = tool["tokens"][0]
    assert token_call["url"] == (
        "https://login.microsoftonline.com/contoso/oauth2/v2.0/token"
    )
    assert token_call["data"]["client_secret"] == "s3cret"
    assert token_call["data"]["scope"] == (
        "https://api.securitycenter.microsoft.com/.default"
    )
