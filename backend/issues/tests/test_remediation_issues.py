"""Phase-1 Remediation Issues tests (issues-engagements.md §10, §16.1).

Covers the commitment/acceptance lifecycle, representative gating, the
Allow self-validation setting, closure invariants, reopening, terminal
freeze, model immutability, and the Comment parent extension.

Domain gating (representative membership) is independent from IAM
visibility, so tests authenticate superusers to keep fixtures focused on
the domain logic; IAM breadth is exercised by the permission-seed sync.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import AppliedControl, Comment
from global_settings.models import GlobalSettings
from iam.models import Folder, User
from issues.models import CommitmentVersion, RemediationIssue
from issues.views import RemediationIssueViewSet

factory = APIRequestFactory()


def _action(name, issue, user, data=None):
    view = RemediationIssueViewSet.as_view({"post": name})
    req = factory.post(
        f"/api/remediation-issues/{issue.id}/{name}/", data or {}, format="json"
    )
    force_authenticate(req, user=user)
    return view(req, pk=str(issue.id))


def _patch(issue, user, data):
    view = RemediationIssueViewSet.as_view({"patch": "partial_update"})
    req = factory.patch(
        f"/api/remediation-issues/{issue.id}/", data, format="json"
    )
    force_authenticate(req, user=user)
    return view(req, pk=str(issue.id))


@pytest.fixture
def domain(db):
    return Folder.objects.create(
        name="issues-tests",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


@pytest.fixture
def lead(db):
    return User.objects.create_superuser(email="issue-lead@tests.local")


@pytest.fixture
def respondent(db):
    return User.objects.create_superuser(email="issue-respondent@tests.local")


@pytest.fixture
def outsider(db):
    return User.objects.create_superuser(email="issue-outsider@tests.local")


@pytest.fixture
def general_settings(db):
    settings_row, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.GENERAL, defaults={"value": {}}
    )
    settings_row.value = {"allow_self_validation": False}
    settings_row.save()
    return settings_row


@pytest.fixture
def issue(domain, lead, respondent, general_settings):
    issue = RemediationIssue.objects.create(
        name="MFA rollout",
        description="Deploy MFA on all admin accounts",
        folder=domain,
    )
    issue.lead_representatives.add(lead.actor)
    issue.respondent_representatives.add(respondent.actor)
    return issue


def _accept_both(issue, lead, respondent):
    version = issue.current_commitment
    if version is None:
        response = _action(
            "propose_commitment",
            issue,
            respondent,
            {"text": "Deploy MFA by Q3", "based_on_version_id": None},
        )
        assert response.status_code == 201, response.data
    assert _action("set_acceptance", issue, lead, {"state": "accepted"}).status_code == 200
    assert (
        _action("set_acceptance", issue, respondent, {"state": "accepted"}).status_code
        == 200
    )


# ── participation and proposal ────────────────────────────────────────────────


def test_propose_requires_representative(issue, outsider):
    response = _action("propose_commitment", issue, outsider, {"text": "x"})
    assert response.status_code == 403
    assert response.data["error"] == "notARepresentative"


def test_propose_and_bilateral_acceptance(issue, lead, respondent):
    response = _action(
        "propose_commitment",
        issue,
        respondent,
        {"text": "Deploy MFA by Q3", "based_on_version_id": None},
    )
    assert response.status_code == 201, response.data
    assert response.data["author_side"] == "respondent"
    issue.refresh_from_db()
    assert issue.acceptance_state == "pending_lead"

    assert _action("set_acceptance", issue, lead, {"state": "accepted"}).status_code == 200
    assert issue.acceptance_state == "pending_respondent"
    assert (
        _action("set_acceptance", issue, respondent, {"state": "accepted"}).status_code
        == 200
    )
    assert issue.acceptance_state == "accepted"


def test_changes_requested_dominates(issue, lead, respondent):
    _action("propose_commitment", issue, respondent, {"text": "v1"})
    _action("set_acceptance", issue, lead, {"state": "accepted"})
    _action("set_acceptance", issue, respondent, {"state": "changes_requested"})
    assert issue.acceptance_state == "changes_requested"
    # the same side may revise its decision on the same version
    _action("set_acceptance", issue, respondent, {"state": "accepted"})
    assert issue.acceptance_state == "accepted"


def test_optimistic_concurrency_conflict(issue, lead, respondent):
    assert (
        _action("propose_commitment", issue, respondent, {"text": "v1"}).status_code
        == 201
    )
    stale = _action(
        "propose_commitment", issue, lead, {"text": "v2", "based_on_version_id": None}
    )
    assert stale.status_code == 409
    assert stale.data["error"] == "commitmentVersionConflict"
    current_id = str(issue.current_commitment.id)
    fresh = _action(
        "propose_commitment",
        issue,
        lead,
        {"text": "v2", "based_on_version_id": current_id},
    )
    assert fresh.status_code == 201
    assert issue.current_commitment.version_number == 2


def test_new_version_resets_acceptance(issue, lead, respondent):
    _accept_both(issue, lead, respondent)
    v1_id = str(issue.current_commitment.id)
    _action(
        "propose_commitment",
        issue,
        lead,
        {"text": "tighter deadline", "based_on_version_id": v1_id},
    )
    issue.refresh_from_db()
    assert issue.current_commitment.version_number == 2
    assert issue.acceptance_state == "pending_lead"


# ── self-validation setting ───────────────────────────────────────────────────


def test_self_validation_blocked_across_sides(issue, lead, general_settings):
    # lead also represents the respondent side
    issue.respondent_representatives.add(lead.actor)
    assert (
        _action(
            "propose_commitment", issue, lead, {"text": "v1", "side": "lead"}
        ).status_code
        == 201
    )
    blocked = _action(
        "set_acceptance", issue, lead, {"state": "accepted", "side": "respondent"}
    )
    assert blocked.status_code == 400
    assert blocked.data["error"] == "selfValidationNotAllowed"

    general_settings.value = {"allow_self_validation": True}
    general_settings.save()
    allowed = _action(
        "set_acceptance", issue, lead, {"state": "accepted", "side": "respondent"}
    )
    assert allowed.status_code == 200


def test_same_side_actions_never_self_validation(issue, lead, respondent):
    # acting twice for one side is not cross-side validation
    _action("propose_commitment", issue, lead, {"text": "v1"})
    response = _action("set_acceptance", issue, lead, {"state": "accepted"})
    assert response.status_code == 200


# ── transitions ───────────────────────────────────────────────────────────────


def test_submit_review_is_respondent_gated(issue, lead, respondent):
    forbidden = _action("submit_review", issue, lead)
    assert forbidden.status_code == 403
    assert forbidden.data["error"] == "onlyRespondentRepresentative"
    ok = _action("submit_review", issue, respondent)
    assert ok.status_code == 200
    issue.refresh_from_db()
    assert issue.status == RemediationIssue.Status.IN_REVIEW


def test_close_requires_accepted_commitment_and_fields(issue, lead, respondent):
    no_commitment = _action(
        "close",
        issue,
        lead,
        {"resolution": "remediated", "closure_justification": "verified"},
    )
    assert no_commitment.status_code == 400
    assert no_commitment.data["error"] == "commitmentNotAccepted"

    _accept_both(issue, lead, respondent)
    missing_justification = _action("close", issue, lead, {"resolution": "remediated"})
    assert missing_justification.data["error"] == "closureJustificationRequired"
    missing_resolution = _action(
        "close", issue, lead, {"closure_justification": "verified"}
    )
    assert missing_resolution.data["error"] == "resolutionRequired"

    respondent_close = _action(
        "close",
        issue,
        respondent,
        {"resolution": "remediated", "closure_justification": "verified"},
    )
    assert respondent_close.status_code == 403

    done = _action(
        "close",
        issue,
        lead,
        {"resolution": "remediated", "closure_justification": "MFA verified on all accounts"},
    )
    assert done.status_code == 200
    issue.refresh_from_db()
    assert issue.status == RemediationIssue.Status.DONE
    assert issue.closed_at is not None
    assert issue.resolution == "remediated"


def test_cancel_is_lead_gated_and_needs_reason(issue, lead, respondent):
    assert _action("cancel", issue, respondent, {"cancellation_reason": "duplicate"}).status_code == 403
    missing = _action("cancel", issue, lead, {})
    assert missing.data["error"] == "cancellationReasonRequired"
    ok = _action("cancel", issue, lead, {"cancellation_reason": "duplicate"})
    assert ok.status_code == 200
    issue.refresh_from_db()
    assert issue.status == RemediationIssue.Status.CANCELLED


def test_reopen_only_done_by_lead_to_non_terminal(issue, lead, respondent):
    assert _action("reopen", issue, lead, {"status": "in_remediation"}).data["error"] == (
        "onlyDoneIssuesCanBeReopened"
    )
    _accept_both(issue, lead, respondent)
    _action(
        "close",
        issue,
        lead,
        {"resolution": "remediated", "closure_justification": "verified"},
    )
    assert _action("reopen", issue, respondent, {"status": "in_remediation"}).status_code == 403
    bad_target = _action("reopen", issue, lead, {"status": "cancelled"})
    assert bad_target.data["error"] == "invalidReopenStatus"
    ok = _action("reopen", issue, lead, {"status": "in_remediation"})
    assert ok.status_code == 200
    issue.refresh_from_db()
    assert issue.status == RemediationIssue.Status.IN_REMEDIATION
    assert issue.closed_at is None
    assert issue.resolution == ""
    assert issue.closure_justification == ""


def test_terminal_freeze_on_generic_write(issue, lead, respondent):
    _accept_both(issue, lead, respondent)
    _action(
        "close",
        issue,
        lead,
        {"resolution": "remediated", "closure_justification": "verified"},
    )
    response = _patch(issue, lead, {"name": "renamed"})
    assert response.status_code == 400
    # commitment actions are also blocked while done
    blocked = _action("propose_commitment", issue, lead, {"text": "v2"})
    assert blocked.data["error"] == "issueClosedReopenFirst"


def test_status_patch_cannot_reach_terminal(issue, lead):
    response = _patch(issue, lead, {"status": "done"})
    assert response.status_code == 400


# ── links and comments ────────────────────────────────────────────────────────


def test_links_are_plain_m2m(issue, domain):
    control = AppliedControl.objects.create(name="MFA control", folder=domain)
    issue.applied_controls.add(control)
    assert control.remediation_issues.count() == 1
    control.delete()
    issue.refresh_from_db()
    assert issue.applied_controls.count() == 0


def test_comment_on_issue(issue, lead):
    comment = Comment.objects.create(remediation_issue=issue, body="hello", author=lead)
    assert comment.folder_id == issue.folder_id
    assert comment.parent_object == issue


def test_comment_exactly_one_parent(issue, domain, lead):
    control = AppliedControl.objects.create(name="c", folder=domain)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Comment.objects.create(
                remediation_issue=issue,
                applied_control=control,
                body="two parents",
                author=lead,
            )


# ── model invariants ──────────────────────────────────────────────────────────


def test_commitment_content_immutable(issue, lead, respondent):
    _action("propose_commitment", issue, respondent, {"text": "v1"})
    version = issue.current_commitment
    version.text = "edited"
    with pytest.raises(ValidationError):
        version.save()


def test_superseded_version_fully_immutable(issue, lead, respondent):
    _action("propose_commitment", issue, respondent, {"text": "v1"})
    v1 = issue.current_commitment
    _action(
        "propose_commitment",
        issue,
        lead,
        {"text": "v2", "based_on_version_id": str(v1.id)},
    )
    v1.refresh_from_db()
    v1.lead_acceptance = RemediationIssue.AcceptanceState.ACCEPTED
    with pytest.raises(ValidationError):
        v1.save()
