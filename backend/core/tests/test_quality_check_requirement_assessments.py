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
    EvidenceRevision,
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
    # The per-requirement surface has to agree: it feeds the API endpoint and
    # the workflow computed value, which must not report what the audit hides.
    ra.refresh_from_db()
    assert ra.quality_check()["count"] == 0


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


def _evidence(folder, name, *, status=None, expiry=None, attached=True, updated=None):
    """An evidence in a named state. `attached` is the distinction a status
    cannot express: a record with nothing uploaded is a title."""
    evidence = Evidence.objects.create(
        name=name,
        folder=folder,
        status=status or Evidence.Status.APPROVED,
        expiry_date=expiry,
    )
    if attached:
        revision = EvidenceRevision.objects.create(
            evidence=evidence, version=1, link="https://example.test/file"
        )
        if updated is not None:
            # queryset.update() writes the column as given; save() would stamp
            # auto_now over it.
            EvidenceRevision.objects.filter(pk=revision.pk).update(updated_at=updated)
    return evidence


@pytest.mark.django_db
def test_partially_compliant_with_no_evidence(requirement_assessment):
    """The compliant case had a rule; the partial one claimed just as much and
    had none."""
    compliance_assessment, ra = requirement_assessment
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="A control", folder=compliance_assessment.folder, status="active"
        )
    )
    ra.result = RequirementAssessment.Result.PARTIALLY_COMPLIANT
    ra.save()

    msgids = _msgids(compliance_assessment.quality_check(), "warnings")
    assert "requirementAssessmentPartialNoEvidence" in msgids
    # The compliant rule stays about compliant.
    assert "requirementAssessmentCompliantNoEvidence" not in msgids


@pytest.mark.django_db
def test_one_expired_and_one_empty_evidence_is_caught(requirement_assessment):
    """Neither narrower rule fires here — not every evidence has expired, and
    not every one is draft — so before this rule the requirement passed in
    silence with nothing usable behind it."""
    compliance_assessment, ra = requirement_assessment
    folder = compliance_assessment.folder
    ra.evidences.add(
        _evidence(folder, "Lapsed report", expiry=date.today() - timedelta(days=30)),
        _evidence(folder, "Empty record", status=Evidence.Status.DRAFT, attached=False),
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    msgids = _msgids(compliance_assessment.quality_check(), "warnings")
    assert "requirementAssessmentNoUsableEvidence" in msgids
    assert "requirementAssessmentEvidenceExpired" not in msgids
    assert "requirementAssessmentEvidenceAllDraft" not in msgids


@pytest.mark.django_db
def test_an_approved_evidence_with_nothing_uploaded_is_caught(requirement_assessment):
    """`evidenceNoFile` sees this, but it is reported against the evidence and
    never reaches the requirement that rests on it."""
    compliance_assessment, ra = requirement_assessment
    ra.evidences.add(
        _evidence(
            compliance_assessment.folder,
            "Access review — Q3",
            status=Evidence.Status.IN_REVIEW,
            attached=False,
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    assert "requirementAssessmentNoUsableEvidence" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "all_expired,expected",
    [(True, "requirementAssessmentEvidenceExpired"), (False, None)],
)
def test_the_narrower_rule_wins_when_it_applies(
    requirement_assessment, all_expired, expected
):
    """One problem is reported once: when every evidence has expired, that is
    the finding, not the general one as well."""
    compliance_assessment, ra = requirement_assessment
    folder = compliance_assessment.folder
    lapsed = date.today() - timedelta(days=30)
    ra.evidences.add(_evidence(folder, "Old one", expiry=lapsed))
    if not all_expired:
        ra.evidences.add(_evidence(folder, "Empty one", attached=False))
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    msgids = _msgids(compliance_assessment.quality_check(), "warnings")
    if expected:
        assert expected in msgids
        assert "requirementAssessmentNoUsableEvidence" not in msgids
    else:
        assert "requirementAssessmentNoUsableEvidence" in msgids


@pytest.mark.django_db
def test_evidence_nobody_has_touched_in_a_year(requirement_assessment):
    """Attached, unexpired, and last moved three years ago. Nothing about its
    status says so — only the revision's own date does."""
    from django.utils import timezone

    compliance_assessment, ra = requirement_assessment
    ra.evidences.add(
        _evidence(
            compliance_assessment.folder,
            "Configuration baseline",
            updated=timezone.now() - timedelta(days=1100),
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    msgids = _msgids(compliance_assessment.quality_check(), "warnings")
    assert "requirementAssessmentEvidenceStale" in msgids
    # It is current in every other sense, so nothing else should fire.
    assert "requirementAssessmentNoUsableEvidence" not in msgids
    assert "requirementAssessmentEvidenceExpired" not in msgids


@pytest.mark.django_db
def test_recent_evidence_is_not_stale(requirement_assessment):
    from django.utils import timezone

    compliance_assessment, ra = requirement_assessment
    ra.evidences.add(
        _evidence(
            compliance_assessment.folder,
            "Fresh export",
            updated=timezone.now() - timedelta(days=30),
        )
    )
    ra.result = RequirementAssessment.Result.COMPLIANT
    ra.save()

    assert "requirementAssessmentEvidenceStale" not in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


def _partial_with_a_control(compliance_assessment, ra, **control_fields):
    ra.applied_controls.add(
        AppliedControl.objects.create(
            name="A control",
            folder=compliance_assessment.folder,
            status=AppliedControl.Status.ACTIVE,
            **control_fields,
        )
    )
    ra.result = RequirementAssessment.Result.PARTIALLY_COMPLIANT
    ra.save()


@pytest.mark.django_db
def test_a_declared_gap_with_no_date_on_it(requirement_assessment):
    """ControlEtaMissed catches a date that passed. Nothing caught the absence
    of one, which is the more common way a gap goes unmanaged."""
    compliance_assessment, ra = requirement_assessment
    _partial_with_a_control(compliance_assessment, ra)

    assert "requirementAssessmentPartialNoPlan" in _msgids(
        compliance_assessment.quality_check(), "warnings"
    )


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["eta", "due_date"])
def test_a_date_on_the_assessment_itself_is_a_plan(requirement_assessment, field):
    """The gap may be tracked on the assessment rather than on any one control."""
    compliance_assessment, ra = requirement_assessment
    setattr(ra, field, date.today() + timedelta(days=60))
    _partial_with_a_control(compliance_assessment, ra)

    assert "requirementAssessmentPartialNoPlan" not in _msgids(
        compliance_assessment.quality_check()
    )


@pytest.mark.django_db
def test_a_date_on_one_control_is_a_plan(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    _partial_with_a_control(
        compliance_assessment, ra, eta=date.today() + timedelta(days=60)
    )

    assert "requirementAssessmentPartialNoPlan" not in _msgids(
        compliance_assessment.quality_check()
    )


@pytest.mark.django_db
def test_a_partial_assessment_with_nothing_attached_is_reported_once(
    requirement_assessment,
):
    """No control and no date is one problem, and NoAppliedControl is the rule
    that names it."""
    compliance_assessment, ra = requirement_assessment
    ra.result = RequirementAssessment.Result.PARTIALLY_COMPLIANT
    ra.save()

    msgids = _msgids(compliance_assessment.quality_check())
    assert "requirementAssessmentNoAppliedControl" in msgids
    assert "requirementAssessmentPartialNoPlan" not in msgids


@pytest.mark.django_db
def test_a_partial_claim_with_no_observation_is_a_warning(requirement_assessment):
    """The observation is where a declared deviation is described, so this
    belongs with NotApplicableNoJustification rather than below it."""
    compliance_assessment, ra = requirement_assessment
    _partial_with_a_control(compliance_assessment, ra)

    findings = compliance_assessment.quality_check()
    assert "requirementAssessmentPartialNoObservation" in _msgids(findings, "warnings")
    assert "requirementAssessmentPartialNoObservation" not in _msgids(findings, "info")


@pytest.mark.django_db
def test_an_observation_answers_it(requirement_assessment):
    compliance_assessment, ra = requirement_assessment
    ra.observation = "Rolled out to production; the two lab segments are pending."
    _partial_with_a_control(compliance_assessment, ra)

    assert "requirementAssessmentPartialNoObservation" not in _msgids(
        compliance_assessment.quality_check()
    )
