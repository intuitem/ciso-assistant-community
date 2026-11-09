"""The applicability toggle of score-only audits.

A score-only audit hides compliance from everyone, so N/A, which only compliance
can carry, is set through a toggle: a role that edits scores may write `result`
as "not applicable" or back to "not assessed", nothing else. Reads carry the
applicability and what an N/A answer counts for alongside the scores.
"""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    Actor,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementAssignment,
    RequirementNode,
)
from core.utils import (
    is_applicability_readable,
    is_applicability_write,
    respondent_progress_counts,
)
from iam.models import Folder, User, UserGroup

EDIT = {"auditor": "edit", "respondent": "edit"}
HIDDEN = {"auditor": "hidden", "respondent": "hidden"}
SCORE_ONLY = {
    "result": HIDDEN,
    "status": HIDDEN,
    "score": EDIT,
    "is_scored": EDIT,
}


@pytest.fixture
def setup(db):
    startup(sender=None)
    folder = Folder.objects.create(
        name="score only",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(folder)
    framework = Framework.objects.create(
        name="score only", folder=folder, min_score=1, max_score=5
    )
    node = RequirementNode.objects.create(
        framework=framework,
        urn="urn:test:risk:req_node:score-only:r1",
        ref_id="R1",
        assessable=True,
        folder=folder,
    )

    def audit(field_visibility):
        name = f"score only {ComplianceAssessment.objects.count()}"
        ca = ComplianceAssessment.objects.create(
            name=name,
            framework=framework,
            folder=folder,
            perimeter=Perimeter.objects.create(name=name, folder=folder),
            status="in_progress",
            field_visibility=field_visibility,
            anchor_na_to_target=True,
            target_score=3,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca, requirement=node, folder=folder
        )
        assignment = RequirementAssignment.objects.create(
            compliance_assessment=ca, folder=folder, status="in_progress"
        )
        assignment.actor.add(Actor.objects.get_or_create(user=respondent)[0])
        assignment.requirement_assessments.set([ra])
        return ra

    respondent = User.objects.create_user("respondent@score-only.com")
    UserGroup.objects.get(name="BI-UG-ADE", folder=folder).user_set.add(respondent)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=respondent)[1]}"
    )
    return client, audit


def _patch(client, ra, payload):
    response = client.patch(
        f"/api/requirement-assessments/{ra.id}/", payload, format="json"
    )
    assert response.status_code == 200, response.content
    ra.refresh_from_db()
    return ra


@pytest.mark.django_db
def test_respondent_switches_applicability(setup):
    client, audit = setup
    ra = audit(SCORE_ONLY)
    assert _patch(client, ra, {"result": "not_applicable"}).result == "not_applicable"
    assert _patch(client, ra, {"result": "not_assessed"}).result == "not_assessed"


@pytest.mark.django_db
def test_respondent_cannot_write_a_verdict(setup):
    client, audit = setup
    ra = audit(SCORE_ONLY)
    assert _patch(client, ra, {"result": "compliant"}).result == "not_assessed"


@pytest.mark.django_db
def test_no_toggle_where_auditors_see_compliance(setup):
    """Compliance visible to the auditor: a respondent must not overwrite it."""
    client, audit = setup
    ra = audit({**SCORE_ONLY, "result": {"auditor": "edit", "respondent": "hidden"}})
    assert _patch(client, ra, {"result": "not_applicable"}).result == "not_assessed"


@pytest.mark.django_db
def test_reads_carry_applicability_with_the_scores(setup):
    client, audit = setup
    ra = audit(SCORE_ONLY)
    ra.result = "not_applicable"
    ra.save()
    data = client.get(f"/api/requirement-assessments/{ra.id}/").json()
    assert "result" not in data
    assert data["not_applicable"] is True
    assert data["anchored_score"] == 3.0

    hidden_scores = audit({**SCORE_ONLY, "score": HIDDEN, "is_scored": HIDDEN})
    data = client.get(f"/api/requirement-assessments/{hidden_scores.id}/").json()
    assert "not_applicable" not in data
    assert "anchored_score" not in data


@pytest.mark.django_db
def test_reads_keep_a_hidden_verdict_hidden(setup):
    """Compliance the auditor reads but the respondent does not: N/A is part of
    that verdict, so the respondent's read leaves out the applicability."""
    client, audit = setup
    ra = audit({**SCORE_ONLY, "result": {"auditor": "edit", "respondent": "hidden"}})
    ra.result = "not_applicable"
    ra.save()
    assignment = ra.assignments.get()
    response = client.get(
        f"/api/requirement-assignments/{assignment.id}/requirements_list/"
    )
    assert response.status_code == 200, response.content
    [data] = response.json()["requirement_assessments"]
    assert data["score"] is None
    assert "result" not in data
    assert "not_applicable" not in data
    assert "anchored_score" not in data


@pytest.mark.django_db
def test_malformed_applicability_is_dropped(setup):
    """A non-string `result` is not an applicability switch: dropped like any
    field the respondent cannot write, not a server error."""
    client, audit = setup
    ra = audit(SCORE_ONLY)
    assert _patch(client, ra, {"result": ["not_applicable"]}).result == "not_assessed"
    assert _patch(client, ra, {"result": {"a": 1}}).result == "not_assessed"


@pytest.mark.django_db
def test_respondent_progress_follows_the_audit_rule(setup):
    """Without questions or alignment, a score-only requirement is done when N/A
    or scored above the minimum (1 here), as in the audit's own progress."""
    _, audit = setup
    ra = audit(SCORE_ONLY)

    def progress(**values):
        for name, value in values.items():
            setattr(ra, name, value)
        ra.save()
        return respondent_progress_counts(ra.compliance_assessment, [ra])

    assert progress() == (1, 0, 0)
    assert progress(score=1, is_scored=True) == (1, 0, 0)
    assert progress(score=2) == (1, 1, 1)
    assert progress(score=None, is_scored=False, result="not_applicable") == (1, 1, 1)


@pytest.mark.django_db
def test_respondent_progress_reads_compliance_where_shown(setup):
    _, audit = setup
    ra = audit({**SCORE_ONLY, "result": EDIT})
    ra.score = 4
    ra.is_scored = True
    ra.save()
    assert respondent_progress_counts(ra.compliance_assessment, [ra]) == (1, 0, 0)
    ra.result = "compliant"
    ra.save()
    assert respondent_progress_counts(ra.compliance_assessment, [ra]) == (1, 1, 1)


@pytest.mark.parametrize(
    "field_visibility, field, value, expected",
    [
        (SCORE_ONLY, "result", "not_applicable", True),
        (SCORE_ONLY, "result", "not_assessed", True),
        (SCORE_ONLY, "result", "compliant", False),
        (SCORE_ONLY, "status", "done", False),
        ({**SCORE_ONLY, "result": EDIT}, "result", "not_applicable", False),
        ({**SCORE_ONLY, "score": HIDDEN}, "result", "not_applicable", False),
        (SCORE_ONLY, "result", ["not_applicable"], False),
        (SCORE_ONLY, "result", {"not_applicable": 1}, False),
    ],
)
@pytest.mark.django_db
def test_is_applicability_write(field_visibility, field, value, expected):
    audit = ComplianceAssessment(field_visibility=field_visibility)
    assert is_applicability_write(audit, field, value, "respondent") is expected


VERDICT_FOR_AUDITORS = {
    **SCORE_ONLY,
    "result": {"auditor": "edit", "respondent": "hidden"},
}


@pytest.mark.parametrize(
    "field_visibility, role, expected",
    [
        (SCORE_ONLY, "respondent", True),
        (SCORE_ONLY, "auditor", True),
        ({**SCORE_ONLY, "result": EDIT}, "respondent", True),
        (VERDICT_FOR_AUDITORS, "respondent", False),
        (VERDICT_FOR_AUDITORS, "auditor", True),
        ({**SCORE_ONLY, "score": HIDDEN}, "auditor", False),
    ],
)
@pytest.mark.django_db
def test_is_applicability_readable(field_visibility, role, expected):
    audit = ComplianceAssessment(field_visibility=field_visibility)
    assert is_applicability_readable(audit, role) is expected
