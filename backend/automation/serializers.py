from core.serializers import (
    AssessmentReadSerializer,
    BaseModelSerializer,
    FieldsRelatedField,
    PathField,
)

from .models import PostureAssessment, PostureResult


class PostureAssessmentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = PostureAssessment
        exclude = ["created_at", "updated_at"]


class PostureAssessmentReadSerializer(AssessmentReadSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    framework = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    follow_up_assessment = FieldsRelatedField()

    class Meta:
        model = PostureAssessment
        fields = "__all__"


class PostureResultReadSerializer(BaseModelSerializer):
    requirement = FieldsRelatedField(["id", "ref_id", "name"])
    asset = FieldsRelatedField()

    class Meta:
        model = PostureResult
        fields = [
            "id",
            "requirement",
            "asset",
            "result",
            "timestamp",
            "run_id",
            "actual",
            "expected",
            "message",
            "tool",
            "source",
        ]
