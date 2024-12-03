from core.serializers import (
    BaseModelSerializer,
    FieldsRelatedField,
    AssessmentReadSerializer,
)
from core.models import StoredLibrary, RiskMatrix
from .models import EbiosRMStudy
from rest_framework import serializers


class EbiosRMStudyWriteSerializer(BaseModelSerializer):
    def create(self, validated_data):
        if not validated_data.get("risk_matrix"):
            try:
                ebios_matrix_library = StoredLibrary.objects.get(
                    urn="urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm"
                )
                ebios_matrix_library.load()

                validated_data["risk_matrix"] = RiskMatrix.objects.get(
                    urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
                )
            except (StoredLibrary.DoesNotExist, RiskMatrix.DoesNotExist) as e:
                raise serializers.ValidationError(f"Erreur : {str(e)}")
        return super().create(validated_data)

    class Meta:
        model = EbiosRMStudy
        exclude = ["created_at", "updated_at"]


class EbiosRMStudyReadSerializer(AssessmentReadSerializer):
    str = serializers.CharField(source="__str__")
    project = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    risk_matrix = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    compliance_assessments = FieldsRelatedField(many=True)
    risk_assessments = FieldsRelatedField(many=True)

    class Meta:
        model = EbiosRMStudy
        fields = "__all__"
