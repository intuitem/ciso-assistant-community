"""The framework report's evidence export only ships what the caller may see."""

import io
import zipfile
from pathlib import Path

import openpyxl
import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import (
    Actor,
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementAssignment,
    StoredLibrary,
)
from core.startup import startup
from iam.models import Folder, Role, RoleAssignment, User, UserGroup

FIXTURE = Path(__file__).parent / "fixtures" / "test-mixed-scoring.yaml"
HIDDEN = {"auditor": "hidden", "respondent": "hidden"}


def _domain(name):
    domain = Folder.objects.create(
        name=name,
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(domain)
    return domain


def _evidence(name, folder):
    evidence = Evidence.objects.create(name=name, folder=folder)
    EvidenceRevision.objects.create(
        evidence=evidence, folder=folder, version=1, link=f"https://example.com/{name}"
    )
    return evidence


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _reader(domain):
    """Auditor-side reader of `domain` only."""
    user = User.objects.create_user(f"reader@{domain.name.lower()}.test")
    role = Role.objects.create(name=f"Reader-{domain.name}", folder=domain)
    role.permissions.set(
        Permission.objects.filter(
            codename__in=[
                "view_folder",
                "view_framework",
                "view_complianceassessment",
                "view_compliance_assessment_full",
                "view_requirementassessment",
                "view_appliedcontrol",
                "view_evidence",
            ]
        )
    )
    group = UserGroup.objects.create(name=f"Readers-{domain.name}", folder=domain)
    group.user_set.add(user)
    RoleAssignment.objects.create(
        user_group=group, role=role, folder=domain, is_recursive=True
    ).perimeter_folders.add(domain)
    return user


def _exported(client, framework, ras):
    """Evidence names listed in the index of the zip, or None on 204."""
    response = client.post(
        reverse("frameworks-requirement-evidences", kwargs={"pk": str(framework.pk)}),
        {"requirement_assessments": [str(ra.id) for ra in ras]},
        format="json",
    )
    if response.status_code == 204:
        return None
    assert response.status_code == 200, response.content
    archive = zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))
    sheet = openpyxl.load_workbook(io.BytesIO(archive.read("index.xlsx"))).active
    return {row[3] for row in sheet.iter_rows(min_row=2, values_only=True)}


@pytest.fixture
def setup(db):
    startup(sender=None, **{})
    stored, err = StoredLibrary.store_library_content(FIXTURE.read_bytes())
    assert err is None
    assert stored.load() is None
    framework = Framework.objects.get(urn="urn:intuitem:test:framework:mixed-scoring")
    domain, other = _domain("ExportDomain"), _domain("OtherDomain")
    audit = ComplianceAssessment.objects.create(
        name="Audit",
        framework=framework,
        perimeter=Perimeter.objects.create(name="P", folder=domain),
        folder=domain,
        status="in_progress",
    )
    audit.create_requirement_assessments()
    first, second = RequirementAssessment.objects.filter(
        compliance_assessment=audit, requirement__assessable=True
    ).order_by("requirement__urn")[:2]
    first.evidences.add(_evidence("first-direct", domain))
    second.evidences.add(_evidence("second-direct", domain))
    control = AppliedControl.objects.create(name="control", folder=domain)
    control.evidences.add(_evidence("via-control", domain))
    first.applied_controls.add(control)
    return framework, domain, other, audit, first, second


@pytest.mark.django_db
def test_respondent_gets_only_assigned_requirements(setup):
    framework, domain, _other, audit, first, second = setup
    auditee = User.objects.create_user("auditee@evidence-export.test")
    UserGroup.objects.get(name="BI-UG-ADE", folder=domain).user_set.add(auditee)
    assignment = RequirementAssignment.objects.create(
        compliance_assessment=audit, folder=domain, status="in_progress"
    )
    assignment.actor.add(Actor.objects.get_or_create(user=auditee)[0])
    assignment.requirement_assessments.set([second])

    exported = _exported(_client(auditee), framework, [first, second])

    assert exported == {"second-direct"}


@pytest.mark.django_db
def test_respondent_without_assignment_gets_nothing(setup):
    framework, domain, _other, _audit, first, second = setup
    auditee = User.objects.create_user("idle@evidence-export.test")
    UserGroup.objects.get(name="BI-UG-ADE", folder=domain).user_set.add(auditee)

    assert _exported(_client(auditee), framework, [first, second]) is None


@pytest.mark.django_db
def test_hidden_evidences_field_exports_nothing(setup):
    framework, domain, _other, audit, first, second = setup
    audit.field_visibility = {"evidences": HIDDEN}
    audit.save(update_fields=["field_visibility"])

    assert _exported(_client(_reader(domain)), framework, [first, second]) is None


@pytest.mark.django_db
def test_hidden_applied_controls_field_drops_control_evidences(setup):
    framework, domain, _other, audit, first, second = setup
    audit.field_visibility = {"applied_controls": HIDDEN}
    audit.save(update_fields=["field_visibility"])

    exported = _exported(_client(_reader(domain)), framework, [first, second])

    assert exported == {"first-direct", "second-direct"}


@pytest.mark.django_db
def test_unreadable_controls_and_evidences_are_left_out(setup):
    framework, domain, other, _audit, first, second = setup
    hidden_control = AppliedControl.objects.create(name="hidden-control", folder=other)
    hidden_control.evidences.add(_evidence("via-hidden-control", domain))
    first.applied_controls.add(hidden_control)
    first.evidences.add(_evidence("hidden-direct", other))

    exported = _exported(_client(_reader(domain)), framework, [first, second])

    assert exported == {"first-direct", "second-direct", "via-control"}


@pytest.mark.django_db
def test_export_over_the_size_limit_is_refused(setup, settings):
    framework, domain, _other, _audit, first, second = setup
    evidence = Evidence.objects.create(name="big-file", folder=domain)
    revision = EvidenceRevision.objects.create(evidence=evidence, folder=domain)
    revision.attachment = SimpleUploadedFile(
        "big.pdf", b"x" * 2_000, content_type="application/pdf"
    )
    revision.save()
    first.evidences.add(evidence)
    settings.EVIDENCE_EXPORT_MAX_SIZE_MB = 0.001
    url = reverse("frameworks-requirement-evidences", kwargs={"pk": str(framework.pk)})
    body = {"requirement_assessments": [str(first.id), str(second.id)]}
    client = _client(_reader(domain))

    response = client.post(url, body, format="json")

    assert response.status_code == 413
    assert response.json()["error"] == "evidence_export_too_large"

    settings.EVIDENCE_EXPORT_MAX_SIZE_MB = 0
    assert client.post(url, body, format="json").status_code == 200
