from core.serializers import (
    BaseModelSerializer,
)
from core.serializer_fields import FieldsRelatedField, HashSlugRelatedField
from core.models import RiskMatrix
from .models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    Stakeholder,
    StrategicScenario,
    AttackPath,
    OperationalScenario,
    ElementaryAction,
    OperatingMode,
    KillChain,
)
from rest_framework import serializers


class EbiosRMStudyWriteSerializer(BaseModelSerializer):
    risk_matrix = serializers.PrimaryKeyRelatedField(
        queryset=RiskMatrix.objects.all(), required=False
    )

    class Meta:
        model = EbiosRMStudy
        exclude = ["created_at", "updated_at"]


class EbiosRMStudyReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    perimeter = FieldsRelatedField(["id", "folder"])
    folder = FieldsRelatedField()
    reference_entity = FieldsRelatedField()
    risk_matrix = FieldsRelatedField()
    reference_entity = FieldsRelatedField()
    assets = FieldsRelatedField(["id", "type", {"folder": ["id"]}], many=True)
    compliance_assessments = FieldsRelatedField(many=True)
    risk_assessments = FieldsRelatedField(many=True)
    authors = FieldsRelatedField(many=True)
    reviewers = FieldsRelatedField(many=True)
    roto_count = serializers.IntegerField()
    selected_roto_count = serializers.IntegerField()
    selected_attack_path_count = serializers.IntegerField()
    operational_scenario_count = serializers.IntegerField()
    applied_control_count = serializers.IntegerField()
    last_risk_assessment = FieldsRelatedField()
    counters = serializers.SerializerMethodField()

    def get_counters(self, obj):
        return obj.get_counters()

    class Meta:
        model = EbiosRMStudy
        fields = "__all__"


class EbiosRMStudyImportExportSerializer(BaseModelSerializer):
    risk_matrix = serializers.SlugRelatedField(slug_field="urn", read_only=True)

    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    assets = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)
    compliance_assessments = HashSlugRelatedField(
        slug_field="pk", read_only=True, many=True
    )
    reference_entity = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = EbiosRMStudy
        fields = [
            "ref_id",
            "name",
            "description",
            "eta",
            "due_date",
            "version",
            "status",
            "observation",
            "meta",
            "assets",
            "compliance_assessments",
            "folder",
            "risk_matrix",
            "reference_entity",
            "created_at",
            "updated_at",
        ]


class FearedEventWriteSerializer(BaseModelSerializer):
    class Meta:
        model = FearedEvent
        exclude = ["created_at", "updated_at"]


class FearedEventReadSerializer(BaseModelSerializer):
    ebios_rm_study = FieldsRelatedField()
    qualifications = FieldsRelatedField(many=True)
    assets = FieldsRelatedField(many=True)
    gravity = serializers.JSONField(source="get_gravity_display")
    folder = FieldsRelatedField()

    class Meta:
        model = FearedEvent
        fields = "__all__"


class FearedEventImportExportSerializer(BaseModelSerializer):
    qualifications = serializers.SlugRelatedField(
        slug_field="name", read_only=True, many=True
    )

    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    ebios_rm_study = HashSlugRelatedField(slug_field="pk", read_only=True)
    assets = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)

    class Meta:
        model = FearedEvent
        fields = [
            "ref_id",
            "name",
            "description",
            "gravity",
            "is_selected",
            "justification",
            "ebios_rm_study",
            "qualifications",
            "assets",
            "folder",
            "created_at",
            "updated_at",
        ]


class RoToWriteSerializer(BaseModelSerializer):
    class Meta:
        model = RoTo
        exclude = ["created_at", "updated_at"]


class RoToReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    feared_events = FieldsRelatedField(["folder", "id"], many=True)
    risk_origin = serializers.SerializerMethodField()

    def get_risk_origin(self, obj):
        return obj.risk_origin.get_name_translated

    motivation = serializers.CharField(source="get_motivation_display")
    resources = serializers.CharField(source="get_resources_display")
    activity = serializers.CharField(source="get_activity_display")
    pertinence = serializers.CharField(source="get_pertinence_display")

    class Meta:
        model = RoTo
        fields = "__all__"


class RoToImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    ebios_rm_study = HashSlugRelatedField(slug_field="pk", read_only=True)
    feared_events = HashSlugRelatedField(slug_field="pk", many=True, read_only=True)
    risk_origin = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = RoTo
        fields = [
            "risk_origin",
            "target_objective",
            "motivation",
            "resources",
            "activity",
            "is_selected",
            "justification",
            "ebios_rm_study",
            "feared_events",
            "folder",
            "created_at",
            "updated_at",
        ]


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
        exclude = ["created_at", "updated_at"]


class StakeholderReadSerializer(BaseModelSerializer):
    str = serializers.CharField(source="__str__")
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    entity = FieldsRelatedField()
    applied_controls = FieldsRelatedField(many=True)
    category = serializers.SerializerMethodField()

    def get_category(self, obj):
        return obj.category.get_name_translated if obj.category else None

    current_criticality = serializers.CharField(
        source="get_current_criticality_display"
    )
    residual_criticality = serializers.CharField(
        source="get_residual_criticality_display"
    )

    class Meta:
        model = Stakeholder
        fields = "__all__"


class StakeholderImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    ebios_rm_study = HashSlugRelatedField(slug_field="pk", read_only=True)
    entity = HashSlugRelatedField(slug_field="pk", read_only=True)
    applied_controls = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)
    category = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = Stakeholder
        fields = [
            "created_at",
            "updated_at",
            "folder",
            "ebios_rm_study",
            "entity",
            "category",
            "current_dependency",
            "current_penetration",
            "current_maturity",
            "current_trust",
            "residual_dependency",
            "residual_penetration",
            "residual_maturity",
            "residual_trust",
            "is_selected",
            "applied_controls",
        ]


class StrategicScenarioWriteSerializer(BaseModelSerializer):
    class Meta:
        model = StrategicScenario
        exclude = ["created_at", "updated_at"]


class StrategicScenarioReadSerializer(BaseModelSerializer):
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    ro_to_couple = FieldsRelatedField()
    gravity = serializers.JSONField(source="get_gravity_display")
    attack_paths = FieldsRelatedField(many=True)

    class Meta:
        model = StrategicScenario
        fields = "__all__"


class StrategicScenarioImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    ebios_rm_study = HashSlugRelatedField(slug_field="pk", read_only=True)
    ro_to_couple = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = StrategicScenario
        fields = [
            "ref_id",
            "name",
            "description",
            "ebios_rm_study",
            "ro_to_couple",
            "folder",
            "created_at",
            "updated_at",
        ]


class AttackPathWriteSerializer(BaseModelSerializer):
    class Meta:
        model = AttackPath
        exclude = ["created_at", "updated_at"]


class AttackPathReadSerializer(BaseModelSerializer):
    ebios_rm_study = FieldsRelatedField()
    folder = FieldsRelatedField()
    ro_to_couple = FieldsRelatedField()
    stakeholders = FieldsRelatedField(many=True)
    risk_origin = serializers.CharField(
        source="ro_to_couple.risk_origin.get_name_translated"
    )
    target_objective = serializers.CharField(source="ro_to_couple.target_objective")

    strategic_scenario = FieldsRelatedField()

    class Meta:
        model = AttackPath
        fields = "__all__"


class AttackPathImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    ebios_rm_study = HashSlugRelatedField(slug_field="pk", read_only=True)
    strategic_scenario = HashSlugRelatedField(slug_field="pk", read_only=True)
    stakeholders = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)

    class Meta:
        model = AttackPath
        fields = [
            "ref_id",
            "name",
            "description",
            "ebios_rm_study",
            "strategic_scenario",
            "stakeholders",
            "folder",
            "is_selected",
            "justification",
            "created_at",
            "updated_at",
        ]


class OperationalScenarioWriteSerializer(BaseModelSerializer):
    quotation_method = serializers.CharField(read_only=True)

    class Meta:
        model = OperationalScenario
        exclude = ["created_at", "updated_at"]


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
    operating_modes_description = serializers.SerializerMethodField()
    operating_modes = FieldsRelatedField(many=True)

    def get_operating_modes_description(self, obj):
        # If there's a description, use it
        if obj.operating_modes_description:
            return obj.operating_modes_description

        # Otherwise, generate from operating modes
        operating_modes = obj.operating_modes.all()
        if operating_modes:
            return " | ".join([mode.name for mode in operating_modes])

        return ""

    class Meta:
        model = OperationalScenario
        fields = "__all__"


class OperationalScenarioImportExportSerializer(BaseModelSerializer):
    ebios_rm_study = HashSlugRelatedField(slug_field="pk", read_only=True)
    attack_path = HashSlugRelatedField(slug_field="pk", read_only=True)
    threats = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    operating_modes_description = serializers.SerializerMethodField()

    def get_operating_modes_description(self, obj):
        if obj.operating_modes_description:
            return obj.operating_modes_description

        # If empty, return combination of operating modes
        operating_modes = obj.operating_modes.all()
        if operating_modes:
            mode_descriptions = []
            for mode in operating_modes:
                mode_text = mode.name
                if mode.description:
                    mode_text += f": {mode.description}"
                mode_descriptions.append(mode_text)
            return "\n".join(mode_descriptions)

        return ""

    class Meta:
        model = OperationalScenario
        fields = [
            "operating_modes_description",
            "likelihood",
            "is_selected",
            "justification",
            "ebios_rm_study",
            "attack_path",
            "threats",
            "folder",
            "created_at",
            "updated_at",
        ]


class ElementaryActionWriteSerializer(BaseModelSerializer):
    operating_modes = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=OperatingMode.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = ElementaryAction
        exclude = ["created_at", "updated_at"]


class ElementaryActionReadSerializer(BaseModelSerializer):
    icon = serializers.CharField(source="get_icon_display")
    icon_fa_class = serializers.CharField()
    icon_fa_hex = serializers.CharField()
    threat = FieldsRelatedField()
    folder = FieldsRelatedField()
    attack_stage = serializers.CharField(source="get_attack_stage_display")

    class Meta:
        model = ElementaryAction
        fields = "__all__"


class OperatingModeWriteSerializer(BaseModelSerializer):
    class Meta:
        model = OperatingMode
        exclude = ["created_at", "updated_at"]


class OperatingModeReadSerializer(BaseModelSerializer):
    operational_scenario = FieldsRelatedField()
    folder = FieldsRelatedField()
    elementary_actions = FieldsRelatedField(many=True)
    likelihood = serializers.JSONField(source="get_likelihood_display")
    ebios_rm_study = FieldsRelatedField()

    class Meta:
        model = OperatingMode
        fields = "__all__"


class KillChainWriteSerializer(BaseModelSerializer):
    class Meta:
        model = KillChain
        exclude = ["created_at", "updated_at"]

    def validate(self, attrs):
        elementary_action = attrs.get("elementary_action")
        antecedents = attrs.get("antecedents", [])
        attack_stage = elementary_action.attack_stage

        if attack_stage == ElementaryAction.AttackStage.KNOW and antecedents:
            raise serializers.ValidationError(
                "Antecedents cannot be selected in attack stage 'Know'."
            )

        if elementary_action in antecedents:
            raise serializers.ValidationError(
                "An elementary action cannot be its own antecedent."
            )

        if antecedents:
            for antecedent in antecedents:
                if not KillChain.objects.filter(
                    operating_mode=attrs.get("operating_mode"),
                    elementary_action=antecedent,
                ).exists():
                    raise serializers.ValidationError(
                        f"Antecedent '{antecedent}' has not been used in the operating mode yet"
                    )

                antecedent_kill_chain = KillChain.objects.filter(
                    operating_mode=attrs.get("operating_mode"),
                    elementary_action=antecedent,
                ).first()

                if antecedent_kill_chain and antecedent.attack_stage > attack_stage:
                    raise serializers.ValidationError(
                        {
                            "antecedents": f"The attack stage of the antecedent '{antecedent}' needs to be the same or before the attack stage of the elementary action"
                        }
                    )

        return super().validate(attrs)


class KillChainReadSerializer(BaseModelSerializer):
    operating_mode = FieldsRelatedField()
    elementary_action = FieldsRelatedField()
    antecedents = FieldsRelatedField(many=True)
    attack_stage = serializers.CharField()
    folder = FieldsRelatedField()
    str = serializers.CharField(source="__str__")

    class Meta:
        model = KillChain
        fields = "__all__"
