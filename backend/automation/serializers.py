from rest_framework import serializers

from core.models import Asset
from core.serializers import (
    AssessmentReadSerializer,
    BaseModelSerializer,
    FieldsRelatedField,
    PathField,
)

from .models import PostureAssessment, PostureResult


class PostureAssessmentWriteSerializer(BaseModelSerializer):
    def update(self, instance, validated_data):
        if "assets" in validated_data:
            kept = {asset.id for asset in validated_data["assets"]}
            current = set(instance.assets.values_list("id", flat=True))
            measured = set(
                instance.results.values_list("asset_id", flat=True).distinct()
            )
            dropped = (current & measured) - kept
            if dropped:
                names = ", ".join(
                    Asset.objects.filter(id__in=dropped).values_list("name", flat=True)
                )
                raise serializers.ValidationError(
                    {"assets": f"cannot remove assets with recorded results: {names}"}
                )
        return super().update(instance, validated_data)

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
