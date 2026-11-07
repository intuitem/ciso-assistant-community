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
from core.utils import is_applicability_write
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


@pytest.mark.parametrize(
    "field_visibility, field, value, expected",
    [
        (SCORE_ONLY, "result", "not_applicable", True),
        (SCORE_ONLY, "result", "not_assessed", True),
        (SCORE_ONLY, "result", "compliant", False),
        (SCORE_ONLY, "status", "done", False),
        ({**SCORE_ONLY, "result": EDIT}, "result", "not_applicable", False),
        ({**SCORE_ONLY, "score": HIDDEN}, "result", "not_applicable", False),
    ],
)
@pytest.mark.django_db
def test_is_applicability_write(field_visibility, field, value, expected):
    audit = ComplianceAssessment(field_visibility=field_visibility)
    assert is_applicability_write(audit, field, value, "respondent") is expected
