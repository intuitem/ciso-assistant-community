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


class BusinessImpactAnalysisWriteSerializer(BaseModelSerializer):
    class Meta:
        model = BusinessImpactAnalysis
        fields = "__all__"


class AssetAssessmentReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    # name = serializers.CharField(source="__str__")

    bia = FieldsRelatedField()
    asset = FieldsRelatedField()
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

    def create(self, validated_data):
        print(validated_data)
        bia = validated_data.get("asset_assessment").bia
        if not bia:
            raise serializers.ValidationError({"bia": "mandatory"})
        validated_data["folder"] = bia.folder

        return super().create(validated_data)
