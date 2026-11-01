"""API tests for auditors who are also a requirement's assignee.

The assignment page shows its assignees the respondent view whatever other role they
hold, so the respondent's write rights must work for them there: a field read-only
for the auditor but editable by the respondent is written instead of being dropped.
"""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    Question,
    RequirementAssessment,
    RequirementAssignment,
    RequirementNode,
)
from iam.models import Folder, User, UserGroup


@pytest.fixture
def app_config():
    startup(sender=None, **{})


def _admin_client(email):
    user = User.objects.create_user(email=email)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    user.folder = admin_group.folder
    user.save()
    admin_group.user_set.add(user)
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {_auth_token[1]}")
    return user, client


@pytest.fixture
def assignee_fixture(app_config):
    root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    folder = Folder.objects.create(parent_folder=root_folder, name="assignee writes")
    perimeter = Perimeter.objects.create(name="assignee writes", folder=folder)
    framework = Framework.objects.create(name="assignee writes", folder=folder)
    compliance_assessment = ComplianceAssessment.objects.create(
        name="assignee writes",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        field_visibility={
            "result": {"auditor": "read", "respondent": "edit"},
            "answers": {"auditor": "read", "respondent": "edit"},
            "observation": {"auditor": "read", "respondent": "read"},
            "status": {"auditor": "edit", "respondent": "hidden"},
        },
    )

    def requirement(key):
        node = RequirementNode.objects.create(
            framework=framework,
            urn=f"urn:test:risk:req_node:assignee-writes:{key}",
            ref_id=key.upper(),
            assessable=True,
            folder=folder,
        )
        question = Question.objects.create(
            requirement_node=node,
            urn=f"urn:test:risk:question:assignee-writes:{key}",
            type=Question.Type.TEXT,
            folder=folder,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=compliance_assessment,
            requirement=node,
            folder=folder,
        )
        return ra, question

    assigned, assigned_question = requirement("assigned")
    other, other_question = requirement("other")

    user, client = _admin_client("assignee_writes@tests.com")
    assignment = RequirementAssignment.objects.create(
        compliance_assessment=compliance_assessment,
        folder=folder,
        status="in_progress",
    )
    assignment.actor.set([user.actor])
    assignment.requirement_assessments.set([assigned])

    return {
        "folder": folder,
        "client": client,
        "assignment": assignment,
        "assigned": assigned,
        "assigned_question": assigned_question,
        "other": other,
        "other_question": other_question,
    }


def _patch(client, ra, payload):
    response = client.patch(
        f"/api/requirement-assessments/{ra.id}/", payload, format="json"
    )
    assert response.status_code == 200, response.json()
    ra.refresh_from_db()
    return ra


@pytest.mark.django_db
class TestRequirementAssessmentWrites:
    def test_assignee_writes_what_the_respondent_may(self, assignee_fixture):
        ra = _patch(
            assignee_fixture["client"],
            assignee_fixture["assigned"],
            {"result": "compliant"},
        )
        assert ra.result == "compliant"

    def test_read_only_still_dropped_without_assignment(self, assignee_fixture):
        ra = _patch(
            assignee_fixture["client"],
            assignee_fixture["other"],
            {"result": "compliant"},
        )
        assert ra.result == "not_assessed"

    def test_submitted_assignment_no_longer_counts(self, assignee_fixture):
        RequirementAssignment.objects.filter(
            pk=assignee_fixture["assignment"].pk
        ).update(status="submitted")
        ra = _patch(
            assignee_fixture["client"],
            assignee_fixture["assigned"],
            {"result": "compliant"},
        )
        assert ra.result == "not_assessed"

    def test_read_only_for_both_roles_stays_dropped(self, assignee_fixture):
        ra = _patch(
            assignee_fixture["client"],
            assignee_fixture["assigned"],
            {"observation": "written anyway"},
        )
        assert not ra.observation

    def test_assignee_keeps_auditor_rights(self, assignee_fixture):
        ra = _patch(
            assignee_fixture["client"],
            assignee_fixture["assigned"],
            {"status": "done"},
        )
        assert ra.status == "done"


@pytest.mark.django_db
class TestAnswerWrites:
    def _answer(self, fixture, ra, question):
        return fixture["client"].post(
            "/api/answers/",
            {
                "requirement_assessment": str(ra.id),
                "question": str(question.id),
                "value": "yes",
                "folder": str(fixture["folder"].id),
            },
            format="json",
        )

    def test_assignee_answers(self, assignee_fixture):
        response = self._answer(
            assignee_fixture,
            assignee_fixture["assigned"],
            assignee_fixture["assigned_question"],
        )
        assert response.status_code == 201, response.json()

    def test_auditor_without_assignment_refused(self, assignee_fixture):
        response = self._answer(
            assignee_fixture,
            assignee_fixture["other"],
            assignee_fixture["other_question"],
        )
        assert response.status_code == 400
        assert "not editable for your role" in str(response.json())
