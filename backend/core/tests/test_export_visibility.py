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
