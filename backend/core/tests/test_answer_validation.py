import pytest
from rest_framework.exceptions import ValidationError
from core.models import (
    Answer,
    ComplianceAssessment,
    Framework,
    Question,
    RequirementAssessment,
    RequirementNode,
    Assessment,
)
from core.serializers import AnswerWriteSerializer
from iam.models import Folder

@pytest.fixture
def validation_setup(db):
    folder = Folder.get_root_folder()
    fw = Framework.objects.create(
        name="Validation FW",
        folder=folder,
        is_published=True,
    )
    rn1 = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:val:req:1",
        ref_id="REQ1",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    rn2 = RequirementNode.objects.create(
        framework=fw,
        urn="urn:test:val:req:2",
        ref_id="REQ2",
        assessable=True,
        folder=folder,
        is_published=True,
    )
    q1 = Question.objects.create(
        requirement_node=rn1,
        urn="urn:test:q1",
        ref_id="Q1",
        type=Question.Type.TEXT,
        folder=folder,
        is_published=True,
    )
    q2 = Question.objects.create(
        requirement_node=rn2,
        urn="urn:test:q2",
        ref_id="Q2",
        type=Question.Type.TEXT,
        folder=folder,
        is_published=True,
    )
    ca = ComplianceAssessment.objects.create(
        name="Validation CA",
        framework=fw,
        folder=folder,
        status=Assessment.Status.IN_PROGRESS,
    )
    ra1 = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=rn1,
        folder=folder,
    )
    return {
        "ca": ca,
        "ra1": ra1,
        "q1": q1,
        "q2": q2,
        "folder": folder,
    }

@pytest.mark.django_db
class TestAnswerValidation:
    def test_validate_parent_child_consistency(self, validation_setup):
        """Verify that a question must belong to the requirement assessment's node."""
        data = validation_setup
        serializer = AnswerWriteSerializer(data={
            "requirement_assessment": data["ra1"].id,
            "question": data["q2"].id,  # q2 belongs to rn2, ra1 belongs to rn1
            "value": "some text",
            "folder": data["folder"].id,
        })
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "question" in excinfo.value.detail
        assert "does not belong to requirement assessment" in str(excinfo.value.detail["question"][0])

    def test_validate_locked_ca(self, validation_setup):
        """Verify that answers cannot be modified if the compliance assessment is locked."""
        data = validation_setup
        data["ca"].is_locked = True
        data["ca"].save()

        serializer = AnswerWriteSerializer(data={
            "requirement_assessment": data["ra1"].id,
            "question": data["q1"].id,
            "value": "some text",
            "folder": data["folder"].id,
        })
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "audit is locked" in str(excinfo.value.detail["non_field_errors"][0])

    def test_validate_in_review_ca(self, validation_setup):
        """Verify that answers cannot be modified if the compliance assessment is in review."""
        data = validation_setup
        data["ca"].status = Assessment.Status.IN_REVIEW
        data["ca"].save()

        serializer = AnswerWriteSerializer(data={
            "requirement_assessment": data["ra1"].id,
            "question": data["q1"].id,
            "value": "some text",
            "folder": data["folder"].id,
        })
        with pytest.raises(ValidationError) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "audit is in review" in str(excinfo.value.detail["non_field_errors"][0])
