"""The archive entry and the index.html link must both carry the real name."""

import io
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from iam.models import Folder, User, UserGroup
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Framework,
    Perimeter,
    RequirementAssessment,
    StoredLibrary,
)

ACCENTED_NAME = "Procédure de gestion.pdf"

SAMPLE_FRAMEWORK_YAML = """
urn: urn:intuitem:test:library:audit-archive-export
locale: en
ref_id: AUDIT-ARCHIVE
name: Sample Framework for Audit Archive Export
description: Minimal framework for testing the archive export endpoint
copyright: Test
version: 1
publication_date: 2025-01-01
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:audit-archive-export
    ref_id: AUDIT-ARCHIVE
    name: Audit Archive Export Test Framework
    description: Minimal framework for archive export regression testing
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:audit-archive:cat-1
      assessable: false
      depth: 1
      ref_id: CAT-1
      name: Category 1
    - urn: urn:intuitem:test:req_node:audit-archive:req-1.1
      assessable: true
      depth: 2
      ref_id: REQ-1.1
      parent_urn: urn:intuitem:test:req_node:audit-archive:cat-1
      name: Requirement 1.1
    - urn: urn:intuitem:test:req_node:audit-archive:req-1.2
      assessable: true
      depth: 2
      ref_id: REQ-1.2
      parent_urn: urn:intuitem:test:req_node:audit-archive:cat-1
      name: Requirement 1.2
""".lstrip()


@pytest.fixture
def app_config():
    startup(sender=None)


@pytest.fixture
def admin_client(app_config):
    admin = User.objects.create_superuser("admin@audit-archive-export-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def audit(app_config, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)

    stored, error = StoredLibrary.store_library_content(
        SAMPLE_FRAMEWORK_YAML.encode("utf-8")
    )
    assert error is None, f"store_library_content failed: {error}"
    assert stored.load() is None
    framework = Framework.objects.get(
        urn="urn:intuitem:test:framework:audit-archive-export"
    )

    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    folder = Folder.objects.create(name="folder-audit-archive", parent_folder=root)
    perimeter = Perimeter.objects.create(name="perimeter-audit-archive", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Audit Archive Export",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
    )
    ca.create_requirement_assessments()
    return ca


def _attach(folder, evidence_name, upload_name):
    """Uploaded the way the view does it."""
    evidence = Evidence.objects.create(name=evidence_name, folder=folder)
    revision = evidence.revisions.order_by("-version").first() or (
        EvidenceRevision.objects.create(evidence=evidence, folder=folder)
    )
    revision.attachment = SimpleUploadedFile(
        upload_name, b"%PDF-1.4 fake", content_type="application/pdf"
    )
    revision.full_clean()
    revision.save()
    return evidence


def _archive(admin_client, audit):
    url = reverse("compliance-assessments-export", kwargs={"pk": str(audit.pk)})
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    body = b"".join(response.streaming_content)
    return zipfile.ZipFile(io.BytesIO(body))


@pytest.mark.django_db
class TestAuditArchiveExport:
    def test_accented_filename_survives_into_the_archive(self, admin_client, audit):
        evidence = _attach(audit.folder, "Procédure", ACCENTED_NAME)
        ra = RequirementAssessment.objects.filter(
            compliance_assessment=audit, requirement__assessable=True
        ).first()
        ra.evidences.add(evidence)

        with _archive(admin_client, audit) as archive:
            assert f"evidences/{ACCENTED_NAME}" in archive.namelist()
            index = archive.read("index.html").decode("utf-8")

        assert "evidences/Proc%C3%A9dure%20de%20gestion.pdf" in index

    def test_two_evidences_sharing_a_filename_both_land(self, admin_client, audit):
        requirements = list(
            RequirementAssessment.objects.filter(
                compliance_assessment=audit, requirement__assessable=True
            )
        )
        for index, ra in enumerate(requirements[:2]):
            ra.evidences.add(_attach(audit.folder, f"Preuve {index}", ACCENTED_NAME))

        with _archive(admin_client, audit) as archive:
            entries = [n for n in archive.namelist() if n.startswith("evidences/")]

        assert set(entries) == {
            f"evidences/{ACCENTED_NAME}",
            "evidences/Procédure de gestion (2).pdf",
        }

    def test_a_hostile_original_filename_cannot_escape_the_archive(
        self, admin_client, audit
    ):
        """Set directly, as promote_to_evidence does, from external input."""
        evidence = _attach(audit.folder, "Promue", "rapport.pdf")
        revision = evidence.last_revision
        revision.original_filename = "../../etc/passwd.pdf"
        revision.save()

        revision.refresh_from_db()
        assert revision.original_filename == "passwd.pdf"

        ra = RequirementAssessment.objects.filter(
            compliance_assessment=audit, requirement__assessable=True
        ).first()
        ra.evidences.add(evidence)

        with _archive(admin_client, audit) as archive:
            entries = [n for n in archive.namelist() if n.startswith("evidences/")]

        assert entries == ["evidences/passwd.pdf"]

    def test_export_omits_a_file_rather_than_failing_on_a_missing_name(
        self, admin_client, audit, monkeypatch
    ):
        """A desynchronised pass costs one file, not the whole archive."""
        import core.views

        evidence = _attach(audit.folder, "Preuve", "rapport.pdf")
        ra = RequirementAssessment.objects.filter(
            compliance_assessment=audit, requirement__assessable=True
        ).first()
        ra.evidences.add(evidence)

        monkeypatch.setattr(core.views, "build_evidence_archive_names", lambda ev: {})

        with _archive(admin_client, audit) as archive:
            assert archive.namelist() == ["index.html"]


def _index(admin_client: APIClient, audit: ComplianceAssessment) -> str:
    with _archive(admin_client, audit) as archive:
        return archive.read("index.html").decode("utf-8")


def _control_blocks(index: str) -> dict[str, str]:
    """Map each applied control name to the HTML from its block up to the next
    control's; the last one runs to the end of the document."""
    chunks = index.split("data-applied-control=")[1:]
    return {chunk.split('"')[1]: chunk for chunk in chunks}


def _first_requirement(audit: ComplianceAssessment) -> RequirementAssessment:
    return RequirementAssessment.objects.filter(
        compliance_assessment=audit, requirement__assessable=True
    ).first()


@pytest.mark.django_db
class TestAuditArchiveReportReadability:
    def test_each_evidence_is_listed_under_its_own_applied_control(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        policy = AppliedControl.objects.create(
            name="Password policy", folder=audit.folder, status="active"
        )
        policy.evidences.add(
            _attach(audit.folder, "Policy v3", "policy-v3.pdf"),
            Evidence.objects.create(name="Oral approval", folder=audit.folder),
        )
        review = AppliedControl.objects.create(
            name="Account review", folder=audit.folder, status="in_progress"
        )
        review.evidences.add(_attach(audit.folder, "Q3 review", "q3-review.pdf"))
        training = AppliedControl.objects.create(
            name="Awareness training", folder=audit.folder, status="to_do"
        )
        _first_requirement(audit).applied_controls.add(policy, review, training)

        blocks = _control_blocks(_index(admin_client, audit))

        assert "Policy v3" in blocks["Password policy"]
        assert "Oral approval" in blocks["Password policy"]
        assert "Q3 review" not in blocks["Password policy"]
        assert "Q3 review" in blocks["Account review"]
        assert "Policy v3" not in blocks["Account review"]
        assert "No evidence" in blocks["Awareness training"]

    def test_applied_control_shows_its_status(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        control = AppliedControl.objects.create(
            name="Account review", folder=audit.folder, status="in_progress"
        )
        _first_requirement(audit).applied_controls.add(control)

        blocks = _control_blocks(_index(admin_client, audit))

        assert "In progress" in blocks["Account review"]

    def test_evidence_without_a_file_is_flagged_as_such(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        ra = _first_requirement(audit)
        ra.evidences.add(Evidence.objects.create(name="Interview", folder=audit.folder))
        control = AppliedControl.objects.create(name="Policy", folder=audit.folder)
        control.evidences.add(
            Evidence.objects.create(name="Oral approval", folder=audit.folder)
        )
        ra.applied_controls.add(control)

        index = _index(admin_client, audit)

        assert index.count("No file attached") == 2

    def test_evidences_of_a_control_are_listed_by_name(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        control = AppliedControl.objects.create(name="Policy", folder=audit.folder)
        for name in ["Charlie", "Alpha", "Bravo"]:
            control.evidences.add(
                Evidence.objects.create(name=name, folder=audit.folder)
            )
        _first_requirement(audit).applied_controls.add(control)

        block = _control_blocks(_index(admin_client, audit))["Policy"]

        assert block.index("Alpha") < block.index("Bravo") < block.index("Charlie")

    def test_observation_and_control_description_are_rendered_as_markdown(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        ra = _first_requirement(audit)
        ra.observation = "## Finding\n\nPolicy is **formalised**:\n\n- GPO enforced"
        ra.save()
        control = AppliedControl.objects.create(
            name="Policy", folder=audit.folder, description="Reviewed *yearly*"
        )
        ra.applied_controls.add(control)

        index = _index(admin_client, audit)

        assert "<h2>Finding</h2>" in index
        assert "<strong>formalised</strong>" in index
        assert "<li>GPO enforced</li>" in index
        assert "<em>yearly</em>" in index
        assert "**formalised**" not in index

    def test_requirement_description_is_rendered_as_markdown(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        requirement = _first_requirement(audit).requirement
        requirement.description = "1. Risk analysis\n2. Security objectives"
        requirement.save()

        index = _index(admin_client, audit)

        assert (
            "<ol>\n<li>Risk analysis</li>\n<li>Security objectives</li>\n</ol>" in index
        )

    def test_markdown_cannot_inject_html_scripts_or_remote_content(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        ra = _first_requirement(audit)
        ra.observation = (
            "<script>alert(1)</script>\n\n"
            "[click](javascript:alert(2)) [docs](https://example.com/guide)\n\n"
            "![pixel](https://tracker.example/p.png)"
        )
        ra.save()

        index = _index(admin_client, audit)

        assert "<script>alert(1)</script>" not in index
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in index
        assert "javascript:alert(2)" not in index
        assert (
            '<a href="https://example.com/guide" rel="noopener noreferrer" '
            'target="_blank">docs</a>'
        ) in index
        assert "tracker.example" not in index
        assert "pixel" in index

    def test_a_malformed_link_does_not_break_the_export(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        ra = _first_requirement(audit)
        ra.observation = "Exposed: <http://[IP]/admin>, see [admin](http://[IP]/admin)"
        ra.save()

        index = _index(admin_client, audit)

        assert "admin" in index

    def test_an_image_nested_in_a_rejected_link_is_not_loaded(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        ra = _first_requirement(audit)
        ra.observation = "[![pixel](https://tracker.example/p.png) more](javascript:x)"
        ra.save()

        index = _index(admin_client, audit)

        assert "tracker.example" not in index
        assert "javascript:x" not in index

    def test_markdown_follows_commonmark_like_the_app(
        self, admin_client: APIClient, audit: ComplianceAssessment
    ) -> None:
        ra = _first_requirement(audit)
        ra.observation = (
            "#CONFIG_DEBUG is not set\n\n"
            "Findings:\n- first\n- second\n\n"
            "| Host | Port |\n|---|---|\n| srv | 22 |"
        )
        ra.save()

        index = _index(admin_client, audit)

        assert "<h1>CONFIG_DEBUG" not in index
        assert "#CONFIG_DEBUG is not set" in index
        assert "<li>first</li>" in index
        assert "<td>srv</td>" in index
