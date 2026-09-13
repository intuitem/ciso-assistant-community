import pytest
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from core.views import FolderViewSet
from iam.models import Folder, User


@pytest.fixture
def audit_with_shared_control():
    """Audit whose requirements all point at the same applied control."""
    root_folder = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root_folder, name="quality check")
    perimeter = Perimeter.objects.create(name="quality check", folder=folder)
    framework = Framework.objects.create(
        name="Quality Check Framework",
        urn="urn:test:quality-check-framework",
        folder=root_folder,
    )
    for index in range(3):
        RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:quality-check-framework:req{index}",
            ref_id=f"REQ-{index}",
            name=f"Requirement {index}",
            assessable=True,
            folder=root_folder,
        )
    compliance_assessment = ComplianceAssessment.objects.create(
        name="Quality check audit",
        framework=framework,
        perimeter=perimeter,
        folder=folder,
    )
    compliance_assessment.create_requirement_assessments()
    control = AppliedControl.objects.create(name="Shared control", folder=folder)
    for ra in compliance_assessment.requirement_assessments.all():
        ra.applied_controls.add(control)
    return compliance_assessment, control


@pytest.mark.django_db
def test_shared_control_is_reported_once(audit_with_shared_control):
    compliance_assessment, control = audit_with_shared_control

    findings = compliance_assessment.quality_check()

    reported = [
        f for f in findings["info"] if f["msgid"] == "appliedControlNoReferenceControl"
    ]
    assert len(reported) == 1
    assert reported[0]["link"] == f"applied-controls/{control.id}"


@pytest.mark.django_db
def test_query_count_does_not_grow_with_requirements(audit_with_shared_control):
    compliance_assessment, _ = audit_with_shared_control

    with CaptureQueriesContext(connection) as baseline:
        compliance_assessment.quality_check()

    framework = compliance_assessment.framework
    for index in range(3, 20):
        RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:quality-check-framework:req{index}",
            ref_id=f"REQ-{index}",
            name=f"Requirement {index}",
            assessable=True,
            folder=Folder.get_root_folder(),
        )
    compliance_assessment.create_requirement_assessments()
    assert (
        RequirementAssessment.objects.filter(
            compliance_assessment=compliance_assessment
        ).count()
        > 3
    )

    with CaptureQueriesContext(connection) as grown:
        compliance_assessment.quality_check()

    assert len(grown) == len(baseline)


@pytest.mark.django_db
def test_folders_without_findings_are_left_out(audit_with_shared_control):
    compliance_assessment, _ = audit_with_shared_control
    quiet_folder = Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="quiet domain",
        content_type=Folder.ContentType.DOMAIN,
    )
    user = User.objects.create_superuser("quality-check@tests.com")

    request = APIRequestFactory().get("/api/folders/quality_check/")
    force_authenticate(request, user=user)
    response = FolderViewSet.as_view({"get": "quality_check"})(request)

    assert response.status_code == 200
    results = response.data["results"]
    assert str(compliance_assessment.folder_id) in results
    assert str(quiet_folder.id) not in results
    assert all(FolderViewSet._has_findings(entry) for entry in results.values())
