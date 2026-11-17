import csv
from io import BytesIO, StringIO

import pytest
from openpyxl import load_workbook
from rest_framework.test import APIClient

from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from portals.models import FrameworkSnapshot, Portal

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def set_custom_portals(enabled: bool):
    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
    )
    gs.value = {**(gs.value or {}), "custom_portals": enabled}
    gs.save()
    clear_feature_flags_cache()


def export_url(token, query=""):
    return f"/api/public/snapshots/{token}/export/{query}"


@pytest.fixture
def snapshot(db):
    set_custom_portals(True)
    snap = FrameworkSnapshot.objects.create(
        name="ISO snapshot",
        framework_ref_id="ISO27001",
        content=[
            {
                "ref_id": "A.1",
                "name": "Parent",
                "result": "compliant",
                "score": 3,
                "children": [
                    {"ref_id": "A.1.1", "name": "Child", "result": "non_compliant"}
                ],
            }
        ],
    )
    # The export is only served while a published public portal shows the snapshot.
    Portal.objects.create(
        name="Trust center",
        is_public=True,
        status=Portal.Status.PUBLISHED,
        content={
            "sections": [
                {"items": [{"kind": "framework", "target": {"snapshot": str(snap.id)}}]}
            ]
        },
    )
    return snap


@pytest.mark.parametrize("query", ["", "?format=csv"])
def test_export_returns_csv(snapshot, query):
    response = APIClient().get(export_url(snapshot.public_token, query))

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert response["Content-Disposition"] == 'attachment; filename="ISO27001.csv"'
    rows = list(csv.reader(StringIO(response.content.decode())))
    assert rows[0] == ["ref_id", "name", "result", "score"]
    assert [row[0] for row in rows[1:]] == ["A.1", "A.1.1"]


def test_export_returns_xlsx(snapshot):
    """`format` is also DRF's renderer override, which used to 404 on `xlsx`."""
    response = APIClient().get(export_url(snapshot.public_token, "?format=xlsx"))

    assert response.status_code == 200
    assert response["Content-Type"] == XLSX_CONTENT_TYPE
    assert response["Content-Disposition"] == 'attachment; filename="ISO27001.xlsx"'
    rows = list(load_workbook(BytesIO(response.content)).active.values)
    assert rows[0] == ("Ref Id", "Name", "Result", "Score")
    assert [row[0] for row in rows[1:]] == ["A.1", "A.1.1"]


def test_export_rejects_unknown_token(snapshot):
    response = APIClient().get(export_url("unknown-token", "?format=xlsx"))

    assert response.status_code == 404


def test_export_rejects_snapshot_of_unpublished_portal(snapshot):
    Portal.objects.update(status=Portal.Status.DRAFT)

    response = APIClient().get(export_url(snapshot.public_token, "?format=xlsx"))

    assert response.status_code == 404


def test_export_is_unreachable_when_custom_portals_is_off(snapshot):
    set_custom_portals(False)

    response = APIClient().get(export_url(snapshot.public_token, "?format=xlsx"))

    assert response.status_code == 403
