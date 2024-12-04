from core.serializers import (
    BaseModelSerializer,
    FieldsRelatedField,
)
from core.models import StoredLibrary, RiskMatrix
from .models import EbiosRMStudy, FearedEvent, RoTo
from rest_framework import serializers
import logging


class EbiosRMStudyWriteSerializer(BaseModelSerializer):
    risk_matrix = serializers.PrimaryKeyRelatedField(
        queryset=RiskMatrix.objects.all(), required=False
    )

    def create(self, validated_data):
        if not validated_data.get("risk_matrix"):
            try:
                ebios_matrix = RiskMatrix.objects.filter(
                    urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
                ).first()
                if not ebios_matrix:
                    ebios_matrix_library = StoredLibrary.objects.get(
                        urn="urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm"
                    )
                    ebios_matrix_library.load()
                    ebios_matrix = RiskMatrix.objects.get(
                        urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
                    )
                validated_data["risk_matrix"] = ebios_matrix
            except (StoredLibrary.DoesNotExist, RiskMatrix.DoesNotExist) as e:
                logging.error(f"Error loading risk matrix: {str(e)}")
                raise serializers.ValidationError(
                    "An error occurred while loading the risk matrix."
                )
        return super().create(validated_data)

    class Meta:
        model = EbiosRMStudy
        exclude = ["created_at", "updated_at"]


class EbiosRMStudyReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    project = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    risk_matrix = FieldsRelatedField()
    reference_entity = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    compliance_assessments = FieldsRelatedField(many=True)
    risk_assessments = FieldsRelatedField(many=True)
    authors = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)

    class Meta:
        model = EbiosRMStudy
        fields = "__all__"


class FearedEventWriteSerializer(BaseModelSerializer):
    class Meta:
        model = FearedEvent
        exclude = ["created_at", "updated_at", "folder"]


class FearedEventReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()

    class Meta:
        model = FearedEvent
        fields = "__all__"


class RoToWriteSerializer(BaseModelSerializer):
    class Meta:
        model = RoTo
        exclude = ["created_at", "updated_at", "folder"]


class RoToReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    fearead_events = FieldsRelatedField(many=True)

    class Meta:
        model = RoTo
        fields = "__all__"
