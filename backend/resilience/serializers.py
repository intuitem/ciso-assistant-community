from core.serializers import BaseModelSerializer, AssessmentReadSerializer
from core.serializer_fields import FieldsRelatedField
from .models import (
    BusinessImpactAnalysis,
    EscalationThreshold,
    AssetAssessment,
    DoraIncidentReport,
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


class DoraIncidentReportReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    incident = FieldsRelatedField(["id", "name", "ref_id", "status", "severity"])
    submitting_entity = FieldsRelatedField(["id", "name"])
    ultimate_parent_entity = FieldsRelatedField(["id", "name"])
    affected_entities = FieldsRelatedField(["id", "name"], many=True)
    folder = FieldsRelatedField()
    incident_submission_display = serializers.CharField(
        source="get_incident_submission_display", read_only=True
    )

    class Meta:
        model = DoraIncidentReport
        exclude = []


class DoraIncidentReportWriteSerializer(BaseModelSerializer):
    class Meta:
        model = DoraIncidentReport
        exclude = ["created_at", "updated_at", "submitted_at"]

    # Submission types that can only exist once per incident
    UNIQUE_SUBMISSION_TYPES = [
        "initial_notification",
        "final_report",
        "major_incident_reclassified_as_non-major",
    ]

    def validate(self, attrs):
        # Prevent edits to submitted reports (except toggling is_submitted itself)
        if self.instance and self.instance.is_submitted:
            allowed_fields = {"is_submitted", "submitted_at"}
            changed_fields = set(attrs.keys()) - allowed_fields
            if changed_fields:
                raise serializers.ValidationError(
                    "This report has been submitted and cannot be modified."
                )

        incident = attrs.get("incident") or (
            self.instance.incident if self.instance else None
        )
        submission_type = attrs.get("incident_submission") or (
            self.instance.incident_submission if self.instance else None
        )

        if incident and submission_type in self.UNIQUE_SUBMISSION_TYPES:
            existing = DoraIncidentReport.objects.filter(
                incident=incident,
                incident_submission=submission_type,
            )
            # Exclude current instance on update
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                labels = dict(DoraIncidentReport.SubmissionType.choices)
                label = labels.get(submission_type, submission_type)
                raise serializers.ValidationError(
                    {
                        "incident_submission": f"A '{label}' report already exists for this incident."
                    }
                )

        return super().validate(attrs)

    def create(self, validated_data):
        incident = validated_data.get("incident")
        if incident:
            validated_data["folder"] = incident.folder
        return super().create(validated_data)
