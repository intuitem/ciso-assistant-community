"""The audit evidences list collects evidences from every path attached to the
audit (global, requirement, applied control, task template), but only walks
through objects the caller is allowed to view."""

from pathlib import Path

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


def _list(client, ca):
    response = client.get(
        f"/api/compliance-assessments/{ca.id}/evidences-list/", {"limit": 100}
    )
    assert response.status_code == 200, response.content
    return {row["name"]: row for row in response.json()["results"]}


@pytest.fixture
def setup(db):
    startup(sender=None, **{})
    stored, err = StoredLibrary.store_library_content(FIXTURE.read_bytes())
    assert err is None
    assert stored.load() is None
    framework = Framework.objects.get(
        urn="urn:intuitem:test:framework:splash-assessable"
    )

    visible = _domain("EvidenceListVisible")
    hidden = _domain("EvidenceListHidden")
    perimeter = Perimeter.objects.create(name="P1", folder=visible)
    ca = ComplianceAssessment.objects.create(
        name="Audit", framework=framework, perimeter=perimeter, folder=visible
    )
    ca.create_requirement_assessments()
    ra = RequirementAssessment.objects.filter(
        compliance_assessment=ca, requirement__assessable=True
    ).first()

    def evidence(name, folder=visible):
        return Evidence.objects.create(name=name, folder=folder)

    ca.evidences.add(evidence("global"))
    ra.evidences.add(evidence("direct"), evidence("hidden-evidence", hidden))
    evidence("unlinked")

    ac = AppliedControl.objects.create(name="Visible control", folder=visible)
    ac.evidences.add(evidence("via-control"))
    ra.applied_controls.add(ac)

    hidden_ac = AppliedControl.objects.create(name="Hidden control", folder=hidden)
    hidden_ac.evidences.add(evidence("via-hidden-control"))
    ra.applied_controls.add(hidden_ac)

    tt = TaskTemplate.objects.create(name="Visible task", folder=visible)
    tt.evidences.add(evidence("via-task"))
    tt.requirement_assessments.add(ra)

    global_tt = TaskTemplate.objects.create(name="Audit task", folder=visible)
    global_tt.evidences.add(evidence("via-audit-task"))
    global_tt.compliance_assessments.add(ca)

    hidden_tt = TaskTemplate.objects.create(name="Hidden task", folder=hidden)
    hidden_tt.evidences.add(evidence("via-hidden-task"))
    hidden_tt.requirement_assessments.add(ra)

    # Reader on the visible domain only
    user = User.objects.create_user("reader@evidence-list-tests.com")
    role = Role.objects.create(name="EvidenceListReader", folder=visible)
    role.permissions.set(
        Permission.objects.filter(
            codename__in=[
                "view_folder",
                "view_complianceassessment",
                "view_requirementassessment",
                "view_evidence",
                "view_appliedcontrol",
                "view_tasktemplate",
            ]
        )
    )
    group = UserGroup.objects.create(name="EvidenceListReaders", folder=visible)
    group.user_set.add(user)
    assignment = RoleAssignment.objects.create(
        user_group=group, role=role, folder=visible, is_recursive=True
    )
    assignment.perimeter_folders.add(visible)

    client = APIClient()
    client.force_authenticate(user=user)
    return client, ca, ra


@pytest.mark.django_db
def test_lists_evidences_from_every_viewable_path(setup):
    client, ca, _ = setup

    assert set(_list(client, ca)) == {
        "global",
        "direct",
        "via-control",
        "via-task",
        "via-audit-task",
    }


@pytest.mark.django_db
def test_requirement_links_name_viewable_paths_only(setup):
    client, ca, ra = setup
    rows = _list(client, ca)

    assert rows["global"]["requirement_assessments"] == []
    assert [link["id"] for link in rows["direct"]["requirement_assessments"]] == [
        str(ra.id)
    ]
    assert (
        "via Visible control"
        in rows["via-control"]["requirement_assessments"][0]["str"]
    )
    assert "via Visible task" in rows["via-task"]["requirement_assessments"][0]["str"]

    all_links = str([row["requirement_assessments"] for row in rows.values()])
    assert "Hidden control" not in all_links
    assert "Hidden task" not in all_links


@pytest.mark.django_db
def test_denied_without_audit_access(setup):
    _, ca, _ = setup
    outsider = User.objects.create_user("outsider@evidence-list-tests.com")
    client = APIClient()
    client.force_authenticate(user=outsider)

    response = client.get(f"/api/compliance-assessments/{ca.id}/evidences-list/")
    assert response.status_code == 403
