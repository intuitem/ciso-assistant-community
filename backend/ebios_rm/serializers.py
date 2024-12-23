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
    StrategicScenario,
    AttackPath,
    OperationalScenario,
)
from rest_framework import serializers
import logging


class EbiosRMStudyWriteSerializer(BaseModelSerializer):
    risk_matrix = serializers.PrimaryKeyRelatedField(
        queryset=RiskMatrix.objects.all(), required=False
    )

    class Meta:
        model = EbiosRMStudy
        exclude = ["created_at", "updated_at"]


class EbiosRMStudyReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    project = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    reference_entity = FieldsRelatedField()
    risk_matrix = FieldsRelatedField()
    reference_entity = FieldsRelatedField()
    assets = FieldsRelatedField(many=True)
    compliance_assessments = FieldsRelatedField(many=True)
    risk_assessments = FieldsRelatedField(many=True)
    authors = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)
    roto_count = serializers.IntegerField()
    attack_path_count = serializers.IntegerField()
    operational_scenario_count = serializers.IntegerField()

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

    motivation = serializers.CharField(source="get_motivation_display")
    resources = serializers.CharField(source="get_resources_display")
    activity = serializers.CharField(source="get_activity_display")
    pertinence = serializers.CharField(source="get_pertinence")

    class Meta:
        model = RoTo
        fields = "__all__"


class StakeholderWriteSerializer(BaseModelSerializer):
    current_criticality = serializers.IntegerField(read_only=True)
    residual_criticality = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        validated_data["residual_dependency"] = validated_data["current_dependency"]
        validated_data["residual_penetration"] = validated_data["current_penetration"]
        validated_data["residual_maturity"] = validated_data["current_maturity"]
        validated_data["residual_trust"] = validated_data["current_trust"]
        return super().create(validated_data)

    class Meta:
        model = Stakeholder
        exclude = ["created_at", "updated_at", "folder"]


class StakeholderReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    entity = FieldsRelatedField()
    applied_controls = FieldsRelatedField(many=True)

    category = serializers.CharField(source="get_category_display")
    current_criticality = serializers.CharField(
        source="get_current_criticality_display"
    )
    residual_criticality = serializers.CharField(
        source="get_residual_criticality_display"
    )

    class Meta:
        model = Stakeholder
        fields = "__all__"


class StrategicScenarioWriteSerializer(BaseModelSerializer):
    class Meta:
        model = StrategicScenario
        exclude = ["created_at", "updated_at", "folder"]


class StrategicScenarioReadSerializer(BaseModelSerializer):
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    ro_to_couple = FieldsRelatedField()
    gravity = serializers.JSONField(source="get_gravity_display")
    attack_paths = FieldsRelatedField(many=True)

    class Meta:
        model = StrategicScenario
        fields = "__all__"


class AttackPathWriteSerializer(BaseModelSerializer):
    class Meta:
        model = AttackPath
        exclude = ["created_at", "updated_at", "folder", "ebios_rm_study"]


class AttackPathReadSerializer(BaseModelSerializer):
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
    attack_path = FieldsRelatedField(["id", "name", "description"])
    stakeholders = FieldsRelatedField(many=True)
    ro_to = FieldsRelatedField(["risk_origin", "target_objective"])
    threats = FieldsRelatedField(many=True)
    likelihood = serializers.JSONField(source="get_likelihood_display")
    gravity = serializers.JSONField(source="get_gravity_display")
    risk_level = serializers.JSONField(source="get_risk_level_display")
    ref_id = serializers.CharField()

    class Meta:
        model = OperationalScenario
        fields = "__all__"
