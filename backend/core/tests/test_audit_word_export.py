"""
Regression tests for the audit Word export endpoint.

Covers the ComplianceAssessmentViewSet.word_report() action, which streams
a DOCX executive report for a given compliance assessment.

Test coverage:
- Happy path: 200, correct Content-Type and Content-Disposition headers
- Response body is a structurally valid DOCX (ZIP with word/document.xml)
- All RequirementAssessment result types present (exercises all chart paths)
- Empty audit (no requirement assessments)
- Implementation groups filter set
- Unauthenticated request rejected with 401
- Non-existent audit PK returns 403 or 404
"""

import io
import uuid
import zipfile

import pytest
from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    StoredLibrary,
)
from iam.models import Folder, User, UserGroup

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

SAMPLE_FRAMEWORK_YAML = """
urn: urn:intuitem:test:library:audit-word-export-regression
locale: en
ref_id: AUDIT-WORD-REG
name: Sample Framework for Audit Word Export Regression
description: Minimal framework for testing the Word export endpoint
copyright: Test
version: 1
publication_date: 2025-01-01
provider: test-provider
packager: test-packager
objects:
  framework:
    urn: urn:intuitem:test:framework:audit-word-export-regression
    ref_id: AUDIT-WORD-REG
    name: Audit Word Export Test Framework
    description: Minimal framework for Word export regression testing
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:audit-word-reg:cat-1
      assessable: false
      depth: 1
      ref_id: CAT-1
      name: Category 1
      description: A sample category
    - urn: urn:intuitem:test:req_node:audit-word-reg:req-1.1
      assessable: true
      depth: 2
      ref_id: REQ-1.1
      parent_urn: urn:intuitem:test:req_node:audit-word-reg:cat-1
      name: Requirement 1.1
      description: First assessable requirement
    - urn: urn:intuitem:test:req_node:audit-word-reg:req-1.2
      assessable: true
      depth: 2
      ref_id: REQ-1.2
      parent_urn: urn:intuitem:test:req_node:audit-word-reg:cat-1
      name: Requirement 1.2
      description: Second assessable requirement
    - urn: urn:intuitem:test:req_node:audit-word-reg:req-1.3
      assessable: true
      depth: 2
      ref_id: REQ-1.3
      parent_urn: urn:intuitem:test:req_node:audit-word-reg:cat-1
      name: Requirement 1.3
      description: Third assessable requirement
    - urn: urn:intuitem:test:req_node:audit-word-reg:req-1.4
      assessable: true
      depth: 2
      ref_id: REQ-1.4
      parent_urn: urn:intuitem:test:req_node:audit-word-reg:cat-1
      name: Requirement 1.4
      description: Fourth assessable requirement
""".lstrip()


def _load_framework():
    stored, error = StoredLibrary.store_library_content(
        SAMPLE_FRAMEWORK_YAML.encode("utf-8")
    )
    assert error is None, f"store_library_content failed: {error}"
    load_error = stored.load()
    assert load_error is None, f"stored.load() failed: {load_error}"
    return Framework.objects.get(
        urn="urn:intuitem:test:framework:audit-word-export-regression"
    )


def _make_audit(framework, name="Audit Word Export Regression"):
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    folder = Folder.objects.create(name=f"folder-{name}", parent_folder=root)
    perimeter = Perimeter.objects.create(name=f"perimeter-{name}", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name=name,
        framework=framework,
        folder=folder,
        perimeter=perimeter,
    )
    return ca


def _read_streaming(response) -> bytes:
    return b"".join(response.streaming_content)


@pytest.fixture
def app_config():
    startup(sender=None, **{})


@pytest.fixture
def admin_client(app_config):
    admin = User.objects.create_superuser(
        "admin@audit-word-export-tests.com", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def audit(app_config):
    framework = _load_framework()
    ca = _make_audit(framework)
    ca.create_requirement_assessments()
    return ca


@pytest.mark.django_db
class TestAuditWordExport:
    """Regression tests for ComplianceAssessmentViewSet.word_report()."""

    def test_word_report_returns_200_with_docx_headers(self, admin_client, audit):
        url = reverse(
            "compliance-assessments-word-report", kwargs={"pk": str(audit.pk)}
        )
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK, (
            f"Expected 200, got {response.status_code}: {_read_streaming(response)[:200]}"
        )
        assert response["Content-Type"] == DOCX_MIME
        assert (
            response["Content-Disposition"] == "attachment; filename=exec_report.docx"
        )

    def test_word_report_body_is_valid_docx(self, admin_client, audit):
        url = reverse(
            "compliance-assessments-word-report", kwargs={"pk": str(audit.pk)}
        )
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        body = _read_streaming(response)
        assert len(body) > 0, "Response body is empty"
        assert zipfile.is_zipfile(io.BytesIO(body)), "Response is not a valid ZIP/DOCX"
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            assert "word/document.xml" in zf.namelist(), (
                "DOCX archive is missing word/document.xml"
            )

    def test_word_report_with_all_result_types(self, admin_client, audit):
        """Export must not crash when all result values are present (exercises all chart paths)."""
        reqs = list(RequirementAssessment.objects.filter(compliance_assessment=audit))
        assert len(reqs) >= 4, (
            f"Expected at least 4 requirement assessments, got {len(reqs)}"
        )

        assignments = [
            RequirementAssessment.Result.COMPLIANT,
            RequirementAssessment.Result.PARTIALLY_COMPLIANT,
            RequirementAssessment.Result.NON_COMPLIANT,
            RequirementAssessment.Result.NOT_APPLICABLE,
        ]
        for req, result in zip(reqs, assignments):
            req.result = result
            req.save()

        url = reverse(
            "compliance-assessments-word-report", kwargs={"pk": str(audit.pk)}
        )
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert zipfile.is_zipfile(io.BytesIO(_read_streaming(response)))

    def test_word_report_empty_audit(self, admin_client, audit):
        """Export must not crash when no requirement assessments exist."""
        ca = _make_audit(audit.framework, name="Empty Audit")

        url = reverse("compliance-assessments-word-report", kwargs={"pk": str(ca.pk)})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert zipfile.is_zipfile(io.BytesIO(_read_streaming(response)))

    def test_word_report_with_implementation_groups(self, admin_client, audit):
        """Filter by implementation groups must not crash the generator."""
        root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(name="impl-group-folder", parent_folder=root)
        perimeter = Perimeter.objects.create(name="impl-group-perimeter", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="Audit with Implementation Groups",
            framework=audit.framework,
            folder=folder,
            perimeter=perimeter,
            selected_implementation_groups=["group-1"],
        )
        ca.create_requirement_assessments()

        url = reverse("compliance-assessments-word-report", kwargs={"pk": str(ca.pk)})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert zipfile.is_zipfile(io.BytesIO(_read_streaming(response)))

    def test_word_report_unauthenticated(self, audit):
        url = reverse(
            "compliance-assessments-word-report", kwargs={"pk": str(audit.pk)}
        )
        response = APIClient().get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_word_report_nonexistent_audit(self, admin_client):
        url = reverse(
            "compliance-assessments-word-report", kwargs={"pk": str(uuid.uuid4())}
        )
        response = admin_client.get(url)
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )
