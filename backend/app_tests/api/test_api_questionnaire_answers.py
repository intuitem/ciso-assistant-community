"""Tests for the PATCH→GET answer cycle on RequirementAssessment API."""

import pytest
from rest_framework.test import APIClient
from core.models import (
    Answer,
    ComplianceAssessment,
    Framework,
    LoadedLibrary,
    Question,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder, User, UserGroup
from core.apps import startup
from knox.models import AuthToken
from library.utils import RequirementNodeImporter
from core.models import Perimeter


@pytest.fixture
def app_config():
    startup(sender=None, **{})


@pytest.fixture
def authenticated_client(app_config):
    admin = User.objects.create_superuser("admin@tests.com", is_published=True)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=admin)
    auth_token = _auth_token[1]
    client.credentials(HTTP_AUTHORIZATION=f"Token {auth_token}")
    return client


@pytest.fixture
def framework_with_questions(app_config):
    """Create a framework with a requirement node that has questions and choices."""
    root = Folder.get_root_folder()
    lib = LoadedLibrary.objects.create(
        name="Test Answers Library",
        urn="urn:test:answers:lib",
        ref_id="ANS-LIB",
        version=1,
        locale="en",
        default_locale=True,
        folder=root,
        is_published=True,
    )
    fw = Framework.objects.create(
        name="Answers Test Framework",
        urn="urn:test:answers:fw",
        folder=root,
        library=lib,
        status=Framework.Status.DRAFT,
        is_published=True,
        locale="en",
        default_locale=True,
    )

    # Import a requirement node with Yes/No/N/A single-choice question
    importer = RequirementNodeImporter(
        {
            "urn": "urn:test:answers:req:1",
            "ref_id": "ANS-REQ-1",
            "assessable": True,
            "questions": {
                "urn:test:answers:q1": {
                    "type": "unique_choice",
                    "text": "Is this control implemented?",
                    "choices": [
                        {
                            "urn": "urn:test:answers:q1:yes",
                            "value": "Yes",
                            "add_score": 10,
                            "compute_result": "true",
                        },
                        {
                            "urn": "urn:test:answers:q1:no",
                            "value": "No",
                            "add_score": 0,
                            "compute_result": "false",
                        },
                        {
                            "urn": "urn:test:answers:q1:na",
                            "value": "N/A",
                            "add_score": 0,
                        },
                    ],
                },
                "urn:test:answers:q2": {
                    "type": "text",
                    "text": "Provide details",
                },
            },
        },
        index=0,
    )
    err = importer.is_valid()
    assert err is None
    importer.import_requirement_node(fw)

    rn = RequirementNode.objects.get(urn="urn:test:answers:req:1")
    return {"framework": fw, "library": lib, "requirement_node": rn}


@pytest.fixture
def compliance_assessment_with_ra(authenticated_client, framework_with_questions):
    """Create a compliance assessment and its requirement assessments."""
    root = Folder.get_root_folder()
    fw = framework_with_questions["framework"]
    rn = framework_with_questions["requirement_node"]

    perimeter = Perimeter.objects.create(
        name="Test Perimeter",
        folder=root,
    )
    ca = ComplianceAssessment.objects.create(
        name="Test Compliance Assessment",
        framework=fw,
        perimeter=perimeter,
        folder=root,
    )
    ca.create_requirement_assessments()

    ra = RequirementAssessment.objects.get(
        compliance_assessment=ca,
        requirement=rn,
    )
    return {
        "compliance_assessment": ca,
        "requirement_assessment": ra,
        "requirement_node": rn,
    }


@pytest.mark.django_db
class TestRequirementAssessmentAnswersPatchGet:
    """Test the PATCH→GET answer cycle to ensure answers persist correctly."""

    def test_patch_single_choice_answer_then_get(
        self, authenticated_client, compliance_assessment_with_ra
    ):
        """PATCH with a single-choice answer, then GET should return the same answer."""
        ra = compliance_assessment_with_ra["requirement_assessment"]

        # Verify question and choices exist
        q1 = Question.objects.get(urn="urn:test:answers:q1")
        assert q1.type == "single_choice"
        assert q1.choices.count() == 3

        # PATCH the RA with answers
        patch_data = {
            "answers": {
                "urn:test:answers:q1": "yes",  # ref_id of the "Yes" choice
            },
            "compliance_assessment": str(
                compliance_assessment_with_ra["compliance_assessment"].id
            ),
        }
        response = authenticated_client.patch(
            f"/api/requirement-assessments/{ra.id}/",
            data=patch_data,
            format="json",
        )
        assert response.status_code == 200, f"PATCH failed: {response.data}"

        # GET the RA and check answers
        response = authenticated_client.get(
            f"/api/requirement-assessments/{ra.id}/",
        )
        assert response.status_code == 200
        answers = response.data.get("answers", {})
        assert answers.get("urn:test:answers:q1") == "yes", (
            f"Expected answer 'yes' for q1, got: {answers}"
        )

    def test_patch_text_answer_then_get(
        self, authenticated_client, compliance_assessment_with_ra
    ):
        """PATCH with a text answer, then GET should return the same answer."""
        ra = compliance_assessment_with_ra["requirement_assessment"]

        patch_data = {
            "answers": {
                "urn:test:answers:q2": "This is a detailed explanation.",
            },
            "compliance_assessment": str(
                compliance_assessment_with_ra["compliance_assessment"].id
            ),
        }
        response = authenticated_client.patch(
            f"/api/requirement-assessments/{ra.id}/",
            data=patch_data,
            format="json",
        )
        assert response.status_code == 200, f"PATCH failed: {response.data}"

        response = authenticated_client.get(
            f"/api/requirement-assessments/{ra.id}/",
        )
        assert response.status_code == 200
        answers = response.data.get("answers", {})
        assert answers.get("urn:test:answers:q2") == "This is a detailed explanation."

    def test_patch_multiple_answers_then_get(
        self, authenticated_client, compliance_assessment_with_ra
    ):
        """PATCH with both single-choice and text answers, then GET should return both."""
        ra = compliance_assessment_with_ra["requirement_assessment"]

        patch_data = {
            "answers": {
                "urn:test:answers:q1": "no",
                "urn:test:answers:q2": "Not yet implemented.",
            },
            "compliance_assessment": str(
                compliance_assessment_with_ra["compliance_assessment"].id
            ),
        }
        response = authenticated_client.patch(
            f"/api/requirement-assessments/{ra.id}/",
            data=patch_data,
            format="json",
        )
        assert response.status_code == 200, f"PATCH failed: {response.data}"

        response = authenticated_client.get(
            f"/api/requirement-assessments/{ra.id}/",
        )
        assert response.status_code == 200
        answers = response.data.get("answers", {})
        assert answers.get("urn:test:answers:q1") == "no"
        assert answers.get("urn:test:answers:q2") == "Not yet implemented."

    def test_patch_overwrites_previous_answer(
        self, authenticated_client, compliance_assessment_with_ra
    ):
        """PATCHing a new answer should overwrite the previous one."""
        ra = compliance_assessment_with_ra["requirement_assessment"]
        ca_id = str(compliance_assessment_with_ra["compliance_assessment"].id)

        # First PATCH: set to "yes"
        response = authenticated_client.patch(
            f"/api/requirement-assessments/{ra.id}/",
            data={
                "answers": {"urn:test:answers:q1": "yes"},
                "compliance_assessment": ca_id,
            },
            format="json",
        )
        assert response.status_code == 200

        # Second PATCH: change to "no"
        response = authenticated_client.patch(
            f"/api/requirement-assessments/{ra.id}/",
            data={
                "answers": {"urn:test:answers:q1": "no"},
                "compliance_assessment": ca_id,
            },
            format="json",
        )
        assert response.status_code == 200

        # GET should return the latest answer
        response = authenticated_client.get(
            f"/api/requirement-assessments/{ra.id}/",
        )
        assert response.status_code == 200
        answers = response.data.get("answers", {})
        assert answers.get("urn:test:answers:q1") == "no"

    def test_empty_answers_dict_preserves_existing(
        self, authenticated_client, compliance_assessment_with_ra
    ):
        """PATCHing with empty answers dict should not clear existing answers."""
        ra = compliance_assessment_with_ra["requirement_assessment"]
        ca_id = str(compliance_assessment_with_ra["compliance_assessment"].id)

        # First set an answer
        response = authenticated_client.patch(
            f"/api/requirement-assessments/{ra.id}/",
            data={
                "answers": {"urn:test:answers:q1": "yes"},
                "compliance_assessment": ca_id,
            },
            format="json",
        )
        assert response.status_code == 200

        # PATCH with no answers field
        response = authenticated_client.patch(
            f"/api/requirement-assessments/{ra.id}/",
            data={
                "status": "in_progress",
                "compliance_assessment": ca_id,
            },
            format="json",
        )
        assert response.status_code == 200

        # GET should still have the answer
        response = authenticated_client.get(
            f"/api/requirement-assessments/{ra.id}/",
        )
        assert response.status_code == 200
        answers = response.data.get("answers", {})
        assert answers.get("urn:test:answers:q1") == "yes"

    def test_answers_from_get_match_patch_format(
        self, authenticated_client, compliance_assessment_with_ra
    ):
        """GET response answers should use the same URN format as PATCH input."""
        ra = compliance_assessment_with_ra["requirement_assessment"]

        # Verify Answer objects were created by create_requirement_assessments
        answer_count = Answer.objects.filter(requirement_assessment=ra).count()
        assert answer_count == 2, f"Expected 2 empty Answer rows, got {answer_count}"

        # GET the RA before any PATCH
        response = authenticated_client.get(
            f"/api/requirement-assessments/{ra.id}/",
        )
        assert response.status_code == 200
        answers = response.data.get("answers", {})

        # Empty answers should have None/null values for the question URNs
        assert "urn:test:answers:q1" in answers, (
            f"Question q1 URN not in answers keys: {list(answers.keys())}"
        )
        assert "urn:test:answers:q2" in answers, (
            f"Question q2 URN not in answers keys: {list(answers.keys())}"
        )
