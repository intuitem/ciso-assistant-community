from core.serializers import (
    BaseModelSerializer,
    FieldsRelatedField,
)
from core.models import StoredLibrary, RiskMatrix
from .models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    Stakeholder,
    AttackPath,
    OperationalScenario,
)
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
    ebios_rm_study = FieldsRelatedField()
    qualifications = FieldsRelatedField(["name"], many=True)
    assets = FieldsRelatedField(many=True)
    gravity = serializers.JSONField(source="get_gravity_display")
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
    feared_events = FieldsRelatedField(["folder", "id"], many=True)

    pertinence = serializers.CharField(source="get_pertinence_display")
    motivation = serializers.CharField(source="get_motivation_display")
    resources = serializers.CharField(source="get_resources_display")

    class Meta:
        model = RoTo
        fields = "__all__"


class StakeholderWriteSerializer(BaseModelSerializer):
    current_criticality = serializers.IntegerField(read_only=True)
    residual_criticality = serializers.IntegerField(read_only=True)

    class Meta:
        model = Stakeholder
        exclude = ["created_at", "updated_at", "folder"]


class StakeholderReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    entity = FieldsRelatedField()
    applied_controls = FieldsRelatedField(many=True)

    current_criticality = serializers.IntegerField()
    residual_criticality = serializers.IntegerField()

    class Meta:
        model = Stakeholder
        fields = "__all__"


class AttackPathWriteSerializer(BaseModelSerializer):
    class Meta:
        model = AttackPath
        exclude = ["created_at", "updated_at", "folder"]


class AttackPathReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    ro_to_couple = FieldsRelatedField()
    stakeholders = FieldsRelatedField(many=True)
    risk_origin = serializers.CharField(source="ro_to_couple.get_risk_origin_display")
    target_objective = serializers.CharField(source="ro_to_couple.target_objective")

    class Meta:
        model = AttackPath
        fields = "__all__"


class OperationalScenarioWriteSerializer(BaseModelSerializer):
    class Meta:
        model = OperationalScenario
        exclude = ["created_at", "updated_at", "folder"]


class OperationalScenarioReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    attack_paths = FieldsRelatedField(many=True)
    threats = FieldsRelatedField(many=True)
    likelihood = serializers.JSONField(source="get_likelihood_display")

    class Meta:
        model = OperationalScenario
        fields = "__all__"
