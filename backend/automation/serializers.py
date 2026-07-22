from django.contrib.auth.models import Permission
from rest_framework import serializers

from core.models import Asset, FindingsAssessment
from core.serializers import (
    AssessmentReadSerializer,
    BaseModelSerializer,
    FieldsRelatedField,
    PathField,
)
from iam.models import Folder, RoleAssignment

from .models import PostureAssessment


class PostureAssessmentWriteSerializer(BaseModelSerializer):
    create_follow_up_assessment = serializers.BooleanField(
        default=False, write_only=True, required=False
    )

    def validate_follow_up_assessment(self, value):
        if value and not RoleAssignment.is_access_allowed(
            user=self.context["request"].user,
            perm=Permission.objects.get(codename="view_findingsassessment"),
            folder=value.folder,
        ):
            raise serializers.ValidationError(
                "permission denied to link this findings assessment"
            )
        return value

    def validate(self, attrs):
        if self.instance and self.instance.is_locked:
            if "is_locked" in attrs and attrs["is_locked"] is False:
                return super().validate(attrs)
            if [field for field in attrs if field != "is_locked"]:
                raise serializers.ValidationError("cannot modify a locked assessment")
        return super().validate(attrs)

    def create(self, validated_data):
        create_follow_up = validated_data.pop("create_follow_up_assessment", False)
        request = self.context.get("request")
        if create_follow_up and not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_findingsassessment"),
            folder=validated_data.get("folder") or Folder.get_root_folder(),
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

    def _viewable_asset_ids(self):
        request = self.context.get("request")
        if request is None:
            return None
        return set(
            RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), request.user, Asset
            )[0]
        )

    def validate_assets(self, assets):
        viewable = self._viewable_asset_ids()
        if viewable is None:
            return assets
        current = (
            set(self.instance.assets.values_list("id", flat=True))
            if self.instance
            else set()
        )
        if any(a.id not in viewable and a.id not in current for a in assets):
            raise serializers.ValidationError("permission denied to add this asset")
        return assets

    def update(self, instance, validated_data):
        validated_data.pop("create_follow_up_assessment", None)
        if "assets" in validated_data:
            kept = {asset.id for asset in validated_data["assets"]}
            current = set(instance.assets.values_list("id", flat=True))
            viewable = self._viewable_asset_ids()
            if viewable is not None:
                # the submitted list only covers viewable assets; keep invisible ones linked
                invisible = current - viewable - kept
                if invisible:
                    validated_data["assets"] = list(validated_data["assets"]) + list(
                        Asset.objects.filter(id__in=invisible)
                    )
                    kept |= invisible
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
    assets = serializers.SerializerMethodField()
    follow_up_assessment = FieldsRelatedField()

    def get_assets(self, obj):
        assets = obj.assets.all()
        request = self.context.get("request")
        if request:
            viewable = self.context.get("viewable_asset_ids")
            if viewable is None:
                viewable = set(
                    RoleAssignment.get_accessible_object_ids(
                        Folder.get_root_folder(), request.user, Asset
                    )[0]
                )
                self.context["viewable_asset_ids"] = viewable
            assets = [a for a in assets if a.id in viewable]
        field = FieldsRelatedField(["id", {"folder": ["id"]}])
        return [field.to_representation(a) for a in assets]

    class Meta:
        model = PostureAssessment
        fields = "__all__"
