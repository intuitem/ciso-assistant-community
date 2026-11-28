"""Exports list only the linked objects the requester may view."""

import csv
import io
from pathlib import Path

import pandas as pd
import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    Framework,
    Perimeter,
    RequirementAssessment,
    StoredLibrary,
    TaskTemplate,
)
from core.startup import startup
from iam.models import Folder, Role, RoleAssignment, User, UserGroup

FIXTURE = Path(__file__).parent / "fixtures" / "test-splash-assessable.yaml"


def _domain(name):
    return Folder.objects.create(
        name=name,
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


@pytest.fixture
def setup(db):
    startup(sender=None, **{})
    stored, err = StoredLibrary.store_library_content(FIXTURE.read_bytes())
    assert err is None
    assert stored.load() is None
    framework = Framework.objects.get(
        urn="urn:intuitem:test:framework:splash-assessable"
    )
    visible, hidden = _domain("ExportVisible"), _domain("ExportHidden")
    ca = ComplianceAssessment.objects.create(
        name="Audit",
        framework=framework,
        perimeter=Perimeter.objects.create(name="P", folder=visible),
        folder=visible,
    )
    ca.create_requirement_assessments()
    ra = RequirementAssessment.objects.filter(
        compliance_assessment=ca, requirement__assessable=True
    ).first()

    control = AppliedControl.objects.create(name="seen-control", folder=visible)
    control.evidences.add(
        Evidence.objects.create(name="seen-evidence", folder=visible),
        Evidence.objects.create(name="hidden-evidence", folder=hidden),
    )
    hidden_control = AppliedControl.objects.create(name="hidden-control", folder=hidden)
    ra.applied_controls.add(control, hidden_control)
    for name, folder in (("seen-task", visible), ("hidden-task", hidden)):
        TaskTemplate.objects.create(name=name, folder=folder).applied_controls.add(
            control
        )

    user = User.objects.create_user("reader@export-visibility.test")
    role = Role.objects.create(name="ExportReader", folder=visible)
    role.permissions.set(
        Permission.objects.filter(
            codename__in=[
                "view_folder",
                "view_complianceassessment",
                "view_compliance_assessment_full",
                "view_requirementassessment",
                "view_appliedcontrol",
                "view_evidence",
                "view_tasktemplate",
                "view_entity",
            ]
        )
    )
    group = UserGroup.objects.create(name="ExportReaders", folder=visible)
    group.user_set.add(user)
    RoleAssignment.objects.create(
        user_group=group, role=role, folder=visible, is_recursive=True
    ).perimeter_folders.add(visible)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, ca


@pytest.mark.django_db
def test_action_plan_xlsx_drops_hidden_controls_evidences_and_tasks(setup):
    client, ca = setup
    response = client.get(f"/api/compliance-assessments/{ca.id}/action_plan_xlsx/")
    assert response.status_code == 200
    rows = pd.read_excel(io.BytesIO(response.content)).fillna("")

    assert list(rows["name"]) == ["seen-control"]
    assert rows["associated_evidences"][0] == "seen-evidence"
    assert rows["tasks"][0] == "seen-task"


@pytest.mark.django_db
def test_action_plan_exports_write_readable_status(setup):
    client, ca = setup
    AppliedControl.objects.filter(name="seen-control").update(
        status=AppliedControl.Status.IN_PROGRESS
    )
    xlsx = client.get(f"/api/compliance-assessments/{ca.id}/action_plan_xlsx/")
    assert pd.read_excel(io.BytesIO(xlsx.content))["status"][0] == "In progress"
    csv_text = b"".join(
        client.get(f"/api/compliance-assessments/{ca.id}/action_plan_csv/")
    ).decode()
    assert "In progress" in csv_text
    assert "in_progress" not in csv_text


@pytest.mark.django_db
def test_list_export_drops_hidden_evidences(setup):
    client, _ = setup
    response = client.get("/api/applied-controls/export_csv/")
    assert response.status_code == 200
    rows = list(
        csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";")
    )

    assert [row["name"] for row in rows] == ["seen-control"]
    assert rows[0]["evidences"] == "seen-evidence"


@pytest.mark.django_db
def test_people_stay_listed_for_domain_readers(setup):
    from core.models import Actor
    from iam.utils import ViewableFilter

    owner = User.objects.create_user("owner@export-visibility.test")
    reader = User.objects.get(email="reader@export-visibility.test")

    assert ViewableFilter(reader).allows(Actor.objects.get(user=owner))


@pytest.mark.django_db
def test_entity_owner_follows_entity_visibility(setup):
    from core.models import Actor
    from iam.utils import ViewableFilter
    from tprm.models import Entity

    reader = User.objects.get(email="reader@export-visibility.test")
    hidden = Folder.objects.get(name="ExportHidden")
    supplier = Entity.objects.create(name="hidden-supplier", folder=hidden)

    assert not ViewableFilter(reader).allows(Actor.objects.get(entity=supplier))


@pytest.mark.django_db
def test_task_export_drops_hidden_linked_controls(setup):
    client, _ = setup
    task = TaskTemplate.objects.get(name="seen-task")
    task.applied_controls.add(AppliedControl.objects.get(name="hidden-control"))

    response = client.get("/api/task-templates/export_csv/")
    assert response.status_code == 200
    rows = {
        row["name"]: row
        for row in csv.DictReader(
            io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"
        )
    }

    assert set(rows) == {"seen-task"}
    assert rows["seen-task"]["applied_controls"] == "seen-control"


@pytest.mark.django_db
def test_ecosystem_export_drops_hidden_parent_entity(setup):
    from tprm.models import Entity

    client, _ = setup
    parent = Entity.objects.create(
        name="hidden-parent",
        ref_id="HP-1",
        folder=Folder.objects.get(name="ExportHidden"),
    )
    Entity.objects.create(
        name="seen-child",
        parent_entity=parent,
        folder=Folder.objects.get(name="ExportVisible"),
    )

    response = client.get("/api/entities/export_ecosystem/")
    assert response.status_code == 200
    rows = pd.read_excel(io.BytesIO(response.content), sheet_name="Entities").fillna("")

    assert rows["name"].tolist() == ["seen-child"]
    assert rows["parent_entity_ref_id"].tolist() == [""]


@pytest.fixture
def findings(setup):
    from core.models import Asset, Finding, FindingsAssessment

    client, ca = setup
    visible = ca.folder
    hidden = Folder.objects.get(name="ExportHidden")
    Role.objects.get(name="ExportReader").permissions.add(
        *Permission.objects.filter(
            codename__in=["view_finding", "view_findingsassessment", "view_asset"]
        )
    )
    binder = FindingsAssessment.objects.create(name="Binder", folder=visible)
    seen = Finding.objects.create(
        name="seen-finding",
        findings_assessment=binder,
        folder=visible,
        observation="weak cipher suites",
        asset=Asset.objects.create(name="hidden-asset", folder=hidden),
    )
    seen.applied_controls.add(
        AppliedControl.objects.get(name="seen-control"),
        AppliedControl.objects.get(name="hidden-control"),
    )
    Finding.objects.create(
        name="other-finding", findings_assessment=binder, folder=visible
    )
    return client


@pytest.mark.django_db
def test_findings_export_drops_hidden_asset_and_controls(findings):
    response = findings.get("/api/findings/export_csv/?search=cipher")
    assert response.status_code == 200
    rows = list(
        csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";")
    )

    assert [row["name"] for row in rows] == ["seen-finding"]
    assert rows[0]["findings_assessment"] == "Binder"
    assert rows[0]["asset"] == ""
    assert rows[0]["applied_controls"] == "seen-control"


@pytest.mark.django_db
@pytest.mark.parametrize("fmt", ["csv", "xlsx"])
def test_asset_export_drops_hidden_parent_and_child_assets(findings, fmt):
    from core.models import Asset

    visible = Folder.objects.get(name="ExportVisible")
    seen = Asset.objects.create(name="seen-asset", folder=visible)
    seen.parent_assets.add(
        Asset.objects.create(name="seen-parent", folder=visible),
        Asset.objects.get(name="hidden-asset"),
    )
    hidden_child = Asset.objects.create(
        name="hidden-child", folder=Folder.objects.get(name="ExportHidden")
    )
    seen_child = Asset.objects.create(name="seen-child", folder=visible)
    for child in (hidden_child, seen_child):
        child.parent_assets.add(seen)

    response = findings.get(f"/api/assets/export_{fmt}/")
    assert response.status_code == 200
    if fmt == "csv":
        rows = list(
            csv.DictReader(
                io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"
            )
        )
    else:
        rows = pd.read_excel(io.BytesIO(response.content)).fillna("").to_dict("records")
    row = next(r for r in rows if r["name"] == "seen-asset")

    assert "hidden-asset" not in {r["name"] for r in rows}
    assert row["parent_assets"] == "seen-parent"
    assert row["child_assets"] == "seen-child"
