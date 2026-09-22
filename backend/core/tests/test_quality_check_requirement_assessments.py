"""Quality rules that judge a single requirement assessment.

The audit-level check composes these same rules, so every test here asserts on
`ComplianceAssessment.quality_check()` unless it is specifically about the
per-requirement surface.
"""

from datetime import date, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory, force_authenticate

from core.views import RequirementAssessmentViewSet
from iam.models import User

from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Evidence,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder


@pytest.fixture
def requirement_assessment():
    """A one-requirement audit, so each test builds exactly the graph its rule
    is about."""
    root_folder = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root_folder, name="ra rules")
    perimeter = Perimeter.objects.create(name="ra rules", folder=folder)
    framework = Framework.objects.create(
        name="RA Rules Framework",
        urn="urn:test:ra-rules-framework",
        folder=root_folder,
    )
    RequirementNode.objects.create(
        framework=framework,
        urn="urn:test:ra-rules-framework:req0",
        ref_id="REQ-0",
        name="Requirement 0",
        assessable=True,
        folder=root_folder,
    )
    compliance_assessment = ComplianceAssessment.objects.create(
        name="RA rules audit",
        framework=framework,
        perimeter=perimeter,
        folder=folder,
    )
    compliance_assessment.create_requirement_assessments()
    return compliance_assessment, compliance_assessment.requirement_assessments.first()


def _msgids(findings, bucket=None):
    buckets = [bucket] if bucket else ["errors", "warnings", "info"]
    return {f["msgid"] for b in buckets for f in findings[b]}


def _findings_for(compliance_assessment, requirement_assessment):
    findings = compliance_assessment.quality_check()
    return [
        f
        for bucket in ("errors", "warnings", "info")
        for f in findings[bucket]
        if f["object"]["id"] == requirement_assessment.id
    ]


@pytest.mark.django_db
def test_compliant_with_no_active_control(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="Planned control",
            folder=compliance_assessment.folder,
            status=AppliedControl.Status.TO_DO,
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    assert "requirementAssessmentCompliantNoActiveControl" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "control_status",
    [AppliedControl.Status.DEPRECATED, AppliedControl.Status.DEGRADED],
)
def test_deprecated_or_degraded_control(requirement_assessment, control_status):
    compliance_assessment, ra = requirement_assessment
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="Unhealthy control",
            folder=compliance_assessment.folder,
            status=control_status,
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    assert "requirementAssessmentControlDeprecatedOrDegraded" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


@pytest.mark.django_db
def test_partially_compliant_with_nothing_started(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="Not started",
            folder=compliance_assessment.folder,
            status=AppliedControl.Status.TO_DO,
        )
    )
    ra.result = RequirementAssessment.Result.PARTIALLY_COMPLIANT
    ra.save()

    assert "requirementAssessmentPartialNoStartedControl" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


@pytest.mark.django_db
def test_expired_control_is_an_error(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="Lapsed control",
            folder=compliance_assessment.folder,
            status=AppliedControl.Status.ACTIVE,
            expiry_date=date.today() - timedelta(days=1),
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    assert "requirementAssessmentControlExpired" in _msgids(
        compliance_assessment.quality_check(), "errors"
    )


@pytest.mark.django_db
def test_control_eta_missed(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="Late control",
            folder=compliance_assessment.folder,
            status=AppliedControl.Status.IN_PROGRESS,
            eta=date.today() - timedelta(days=3),
        )
    )

    assert "requirementAssessmentControlEtaMissed" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


@pytest.mark.django_db
def test_evidence_expired_by_date_despite_a_stale_status(requirement_assessment):
    """mark_expired_evidences only runs under Huey, and applied controls are
    never marked expired at all (CA-1869), so the date is authoritative and the
    status is only a cache of it."""
    compliance_assessment, ra = requirement_assessment
    ra.evidences.add(
        Evidence.objects.create(
            name="Lapsed evidence",
            folder=compliance_assessment.folder,
            status=Evidence.Status.APPROVED,
            expiry_date=date.today() - timedelta(days=1),
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    assert "requirementAssessmentEvidenceExpired" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


@pytest.mark.django_db
def test_rejected_evidence_reached_through_a_control(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    control = AppliedControl.objects.create(
        name="Control with evidence",
        folder=compliance_assessment.folder,
        status=AppliedControl.Status.ACTIVE,
    )
    control.evidences.add(
        Evidence.objects.create(
            name="Rejected evidence",
            folder=compliance_assessment.folder,
            status=Evidence.Status.REJECTED,
        )
    )
    ra.applied_controls.add(control)
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    assert "requirementAssessmentEvidenceRejected" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


@pytest.mark.django_db
def test_not_applicable_without_justification(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    ra.result = RequirementAssessment.Result.NOT_APPLICABLE
    ra.observation = "   "
    ra.save()

    assert "requirementAssessmentNotApplicableNoJustification" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )

    ra.observation = "Out of scope: no card data is processed."
    ra.save()

    assert "requirementAssessmentNotApplicableNoJustification" not in _msgids(
        compliance_assessment.quality_check()
    )


@pytest.mark.django_db
def test_done_without_a_result(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    ra.status = RequirementAssessment.Status.DONE
    ra.result = RequirementAssessment.Result.NOT_ASSESSED
    ra.save()

    assert "requirementAssessmentDoneNotAssessed" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


@pytest.mark.django_db
def test_hidden_fields_silence_their_rules(requirement_assessment):
    """An audit that hides a field cannot be judged on it, or every requirement
    would be reported for something nobody is asked to fill in."""
    compliance_assessment, ra = requirement_assessment
    ra.status = RequirementAssessment.Status.DONE
    ra.result = RequirementAssessment.Result.NOT_ASSESSED
    ra.save()
    assert "requirementAssessmentDoneNotAssessed" in _msgids(
        compliance_assessment.quality_check()
    )

    compliance_assessment.field_visibility = {
        "status": {"auditor": "hidden", "respondent": "hidden"}
    }
    compliance_assessment.save()

    assert "requirementAssessmentDoneNotAssessed" not in _msgids(
        compliance_assessment.quality_check()
    )


@pytest.mark.django_db
def test_requirement_check_matches_the_audit_check(requirement_assessment):
    """The audit composes the requirement rules, so a finding cannot differ
    between the two surfaces."""
    compliance_assessment, ra = requirement_assessment
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="Planned control",
            folder=compliance_assessment.folder,
            status=AppliedControl.Status.TO_DO,
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    audit_findings = compliance_assessment.quality_check()
    own = ra.quality_check()

    for bucket in ("errors", "warnings", "info"):
        from_audit = [f for f in audit_findings[bucket] if f["object"]["id"] == ra.id]
        assert from_audit == own[bucket]
    assert own["count"] == sum(len(own[b]) for b in ("errors", "warnings", "info"))
    assert own["count"] > 0


@pytest.mark.django_db
def test_non_assessable_requirements_are_not_judged(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()
    assert _findings_for(compliance_assessment, ra)

    ra.requirement.assessable = False
    ra.requirement.save()

    assert ra.quality_check()["count"] == 0
    assert not _findings_for(compliance_assessment, ra)


@pytest.mark.django_db
def test_requirements_outside_selected_implementation_groups_are_skipped(
    requirement_assessment,
):
    compliance_assessment, ra = requirement_assessment
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()
    assert _findings_for(compliance_assessment, ra)

    ra.requirement.implementation_groups = ["advanced"]
    ra.requirement.save()
    compliance_assessment.selected_implementation_groups = ["basic"]
    compliance_assessment.save()

    assert not _findings_for(compliance_assessment, ra)


@pytest.mark.django_db
def test_quality_check_endpoint_returns_the_findings(requirement_assessment):
    """The per-requirement surface the workflow engine and the UI will read."""
    compliance_assessment, ra = requirement_assessment
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="Planned control",
            folder=compliance_assessment.folder,
            status=AppliedControl.Status.TO_DO,
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()
    user = User.objects.create_superuser("ra-quality-check@tests.com")

    request = APIRequestFactory().get(
        f"/api/requirement-assessments/{ra.id}/quality_check/"
    )
    force_authenticate(request, user=user)
    response = RequirementAssessmentViewSet.as_view({"get": "quality_check_detail"})(
        request, pk=str(ra.id)
    )

    assert response.status_code == 200
    assert set(response.data) == {"errors", "warnings", "info", "count"}
    assert response.data["count"] == ra.quality_check()["count"] > 0


@pytest.mark.django_db
def test_rules_do_not_query_per_requirement(requirement_assessment):
    """The rules read pre-resolved maps; adding requirements must not add
    queries. Guarding this is the whole reason the context is built in bulk."""
    compliance_assessment, ra = requirement_assessment
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="Shared control",
            folder=compliance_assessment.folder,
            status=AppliedControl.Status.TO_DO,
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    with CaptureQueriesContext(connection) as baseline:
        compliance_assessment.quality_check()

    framework = compliance_assessment.framework
    for index in range(1, 20):
        requirement = RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:ra-rules-framework:req{index}",
            ref_id=f"REQ-{index}",
            name=f"Requirement {index}",
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        extra = RequirementAssessment.objects.create(
            compliance_assessment=compliance_assessment,
            requirement=requirement,
            folder=compliance_assessment.folder,
            result=RequirementAssessment.Result.COMPLIANT,
        )
        extra.applied_controls.add(
            AppliedControl.objects.create(
                name=f"Control {index}",
                folder=compliance_assessment.folder,
                status=AppliedControl.Status.TO_DO,
            )
        )

    with CaptureQueriesContext(connection) as grown:
        findings = compliance_assessment.quality_check()

    assert len(grown) == len(baseline)
    assert (
        len(
            [
                f
                for f in findings["warnings"]
                if f["msgid"] == "requirementAssessmentCompliantNoActiveControl"
            ]
        )
        == 20
    )
