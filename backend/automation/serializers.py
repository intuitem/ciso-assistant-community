from django.contrib.auth.models import Permission
from rest_framework import serializers

from core.models import Asset, FindingsAssessment
from core.serializers import (
    AssessmentReadSerializer,
    BaseModelSerializer,
    FieldsRelatedField,
    PathField,
)
from iam.models import RoleAssignment

from .models import PostureAssessment


class PostureAssessmentWriteSerializer(BaseModelSerializer):
    create_follow_up_assessment = serializers.BooleanField(
        default=False, write_only=True, required=False
    )

    def create(self, validated_data):
        create_follow_up = validated_data.pop("create_follow_up_assessment", False)
        request = self.context.get("request")
        if create_follow_up and not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_findingsassessment"),
            folder=validated_data["folder"],
        ):
            raise serializers.ValidationError(
                {
                    "create_follow_up_assessment": "permission denied to create a findings assessment in this domain"
                }
            )
        instance = super().create(validated_data)
        if create_follow_up and instance.follow_up_assessment_id is None:
            instance.follow_up_assessment = FindingsAssessment.objects.create(
                name=f"{instance.name} — follow-up"[:200],
                folder=instance.folder,
                perimeter=instance.perimeter,
                category=FindingsAssessment.Category.POSTURE,
            )
            instance.save(update_fields=["follow_up_assessment"])
        return instance

    def update(self, instance, validated_data):
        validated_data.pop("create_follow_up_assessment", None)
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
    assets = FieldsRelatedField(["id", {"folder": ["id"]}], many=True)
    follow_up_assessment = FieldsRelatedField()

    class Meta:
        model = PostureAssessment
        fields = "__all__"
