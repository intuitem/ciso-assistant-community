from core.serializers import BaseModelSerializer, AssessmentReadSerializer
from core.serializer_fields import FieldsRelatedField
from .models import (
    BusinessImpactAnalysis,
    EscalationThreshold,
    AssetAssessment,
)

from rest_framework import serializers


class BusinessImpactAnalysisReadSerializer(AssessmentReadSerializer):
    class Meta:
        model = BusinessImpactAnalysis
        exclude = []

    str = serializers.CharField(source="__str__")
    perimeter = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    risk_matrix = FieldsRelatedField()
    validation_flows = FieldsRelatedField(
        many=True,
        fields=[
            "id",
            "ref_id",
            "status",
            {"approver": ["id", "email", "first_name", "last_name"]},
        ],
        source="validationflow_set",
    )


class BusinessImpactAnalysisWriteSerializer(BaseModelSerializer):
    class Meta:
        model = BusinessImpactAnalysis
        fields = "__all__"


class AssetAssessmentReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    # name = serializers.CharField(source="__str__")

    bia = FieldsRelatedField(["id", "name", "is_locked"])
    asset = FieldsRelatedField()
    asset_ref_id = serializers.CharField(
        source="asset.ref_id", read_only=True, allow_null=True
    )
    asset_folder = FieldsRelatedField(source="asset.folder")
    children_assets = FieldsRelatedField(source="asset.children_assets", many=True)
    folder = FieldsRelatedField()

    dependencies = FieldsRelatedField(many=True)
    evidences = FieldsRelatedField(many=True)
    associated_controls = FieldsRelatedField(
        ["id", "folder", "name", "status", "eta"], many=True
    )

    class Meta:
        model = AssetAssessment
        exclude = []


class AssetAssessmentWriteSerializer(BaseModelSerializer):
    class Meta:
        model = AssetAssessment
        fields = "__all__"

    def validate(self, attrs):
        # Check for updates (when instance exists)
        if hasattr(self, "instance") and self.instance and self.instance.bia.is_locked:
            raise serializers.ValidationError(
                "⚠️ Cannot modify the asset assessment when the business impact analysis is locked."
            )
        # Check for creates (when BIA is locked)
        bia = attrs.get("bia")
        if bia and bia.is_locked:
            raise serializers.ValidationError(
                "⚠️ Cannot create asset assessments when the business impact analysis is locked."
            )
        return super().validate(attrs)

    def create(self, validated_data):
        bia = validated_data.get("bia")
        if not bia:
            raise serializers.ValidationError({"bia": "mandatory"})
        validated_data["folder"] = bia.folder

        return super().create(validated_data)


class EscalationThresholdReadSerializer(BaseModelSerializer):
    asset_assessment = FieldsRelatedField()
    folder = FieldsRelatedField()
    name = serializers.CharField(source="__str__")

    qualifications = FieldsRelatedField(many=True)
    get_human_pit = serializers.JSONField()
    quali_impact = serializers.JSONField(source="get_impact_display")

    class Meta:
        model = EscalationThreshold
        exclude = []


class EscalationThresholdWriteSerializer(BaseModelSerializer):
    class Meta:
        model = EscalationThreshold
        fields = "__all__"

    def validate(self, attrs):
        # Check for updates (when instance exists)
        if (
            hasattr(self, "instance")
            and self.instance
            and self.instance.asset_assessment.bia.is_locked
        ):
            raise serializers.ValidationError(
                "⚠️ Cannot modify the escalation threshold when the business impact analysis is locked."
            )
        # Check for creates (when BIA is locked)
        asset_assessment = attrs.get("asset_assessment")
        if asset_assessment and asset_assessment.bia.is_locked:
            raise serializers.ValidationError(
                "⚠️ Cannot create escalation thresholds when the business impact analysis is locked."
            )
        return super().validate(attrs)

    def create(self, validated_data):
        print(validated_data)
        bia = validated_data.get("asset_assessment").bia
        if not bia:
            raise serializers.ValidationError({"bia": "mandatory"})
        validated_data["folder"] = bia.folder

        return super().create(validated_data)
