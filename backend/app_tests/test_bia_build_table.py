import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Asset, Perimeter, RiskMatrix, StoredLibrary, Terminology
from iam.models import Folder
from resilience.models import (
    AssetAssessment,
    BusinessImpactAnalysis,
    EscalationThreshold,
)

DAY = 86400


@pytest.mark.django_db
def test_build_table_splits_rows_per_qualification():
    folder = Folder.get_root_folder()
    perimeter = Perimeter.objects.create(name="p", folder=folder)
    StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm"
    ).load()
    matrix = RiskMatrix.objects.get(
        urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
    )
    bia = BusinessImpactAnalysis.objects.create(
        name="bia", perimeter=perimeter, folder=folder, risk_matrix=matrix
    )
    reputation, financial = (
        Terminology.objects.get(
            name=name, field_path=Terminology.FieldPath.QUALIFICATIONS
        )
        for name in ("reputation", "financial")
    )

    def threshold(aa, days, impact, *qualifications):
        th = EscalationThreshold.objects.create(
            asset_assessment=aa,
            point_in_time=days * DAY,
            quali_impact=impact,
            folder=folder,
        )
        th.qualifications.set(qualifications)

    a1 = AssetAssessment.objects.create(
        bia=bia, asset=Asset.objects.create(name="a1", folder=folder), folder=folder
    )
    threshold(a1, 14, 0, reputation)
    threshold(a1, 30, 2, reputation)
    threshold(a1, 35, 0, financial)
    threshold(a1, 60, 1, financial, reputation)
    a2 = AssetAssessment.objects.create(
        bia=bia, asset=Asset.objects.create(name="a2", folder=folder), folder=folder
    )
    threshold(a2, 21, 1)
    AssetAssessment.objects.create(
        bia=bia, asset=Asset.objects.create(name="a3", folder=folder), folder=folder
    )

    with CaptureQueriesContext(connection) as queries:
        table = bia.build_table()
    assert len(queries) <= 6

    rows = {(r["asset"], r["qualification"]): r["data"] for r in table}
    assert list(rows) == [
        ("a1", "financial"),
        ("a1", "reputation"),
        ("a2", None),
        ("a3", None),
    ]
    assert list(rows[("a1", "financial")]) == [
        0,
        14 * DAY,
        21 * DAY,
        30 * DAY,
        35 * DAY,
        60 * DAY,
    ]
    assert [p["value"] for p in rows[("a1", "reputation")].values()] == [
        -1,
        0,
        0,
        2,
        2,
        1,
    ]
    assert [p["value"] for p in rows[("a1", "financial")].values()] == [
        -1,
        -1,
        -1,
        -1,
        0,
        1,
    ]
    assert [p["value"] for p in rows[("a2", None)].values()] == [
        -1,
        -1,
        1,
        1,
        1,
        1,
    ]
    assert all(p["value"] == -1 for p in rows[("a3", None)].values())
