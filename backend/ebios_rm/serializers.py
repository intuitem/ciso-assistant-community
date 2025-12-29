from core.serializers import (
    BaseModelSerializer,
)
from core.serializer_fields import IdRelatedField, HashSlugRelatedField
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
    perimeter = IdRelatedField(["id", "folder"])
    folder = IdRelatedField()
    reference_entity = IdRelatedField()
    risk_matrix = IdRelatedField()
    reference_entity = IdRelatedField()
    assets = IdRelatedField(["id", "type", {"folder": ["id"]}], many=True)
    compliance_assessments = IdRelatedField(many=True)
    risk_assessments = IdRelatedField(many=True)
    authors = IdRelatedField(many=True)
    reviewers = IdRelatedField(many=True)
    roto_count = serializers.IntegerField()
    selected_roto_count = serializers.IntegerField()
    selected_attack_path_count = serializers.IntegerField()
    operational_scenario_count = serializers.IntegerField()
    applied_control_count = serializers.IntegerField()
    last_risk_assessment = IdRelatedField()
    counters = serializers.SerializerMethodField()
    validation_flows = IdRelatedField(
        many=True,
        fields=[
            "id",
            "ref_id",
            "status",
            {"approver": ["id", "email", "first_name", "last_name"]},
        ],
        source="validationflow_set",
    )

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
    ebios_rm_study = IdRelatedField()
    qualifications = IdRelatedField(many=True)
    assets = IdRelatedField(many=True)
    gravity = serializers.JSONField(source="get_gravity_display")
    folder = IdRelatedField()

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
    ebios_rm_study = IdRelatedField()
    folder = IdRelatedField()
    feared_events = IdRelatedField(["folder", "id"], many=True)
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
    ebios_rm_study = IdRelatedField()
    folder = IdRelatedField()
    entity = IdRelatedField()
    applied_controls = IdRelatedField(many=True)
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
    ebios_rm_study = IdRelatedField()
    folder = IdRelatedField()
    ro_to_couple = IdRelatedField()
    gravity = serializers.JSONField(source="get_gravity_display")
    attack_paths = IdRelatedField(many=True)
    feared_events = serializers.SerializerMethodField()

    def get_feared_events(self, obj):
        """Get feared events from the RoTo couple with their gravity"""
        feared_events_data = []
        for feared_event in obj.ro_to_couple.feared_events.all():
            # Build display string with name and gravity
            gravity_display = feared_event.get_gravity_display()
            display_str = f"{feared_event.name} ({gravity_display['name']})"

            feared_events_data.append(
                {
                    "id": str(feared_event.id),
                    "str": display_str,
                    "name": feared_event.name,
                    "description": feared_event.description,
                    "ref_id": feared_event.ref_id,
                    "gravity": gravity_display,
                    "is_selected": feared_event.is_selected,
                }
            )
        return feared_events_data

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
    form_display_name = serializers.CharField()
    ebios_rm_study = IdRelatedField()
    folder = IdRelatedField()
    ro_to_couple = IdRelatedField()
    stakeholders = IdRelatedField(many=True)
    risk_origin = serializers.CharField(
        source="ro_to_couple.risk_origin.get_name_translated"
    )
    target_objective = serializers.CharField(source="ro_to_couple.target_objective")

    strategic_scenario = IdRelatedField()

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
    ebios_rm_study = IdRelatedField()
    folder = IdRelatedField()
    attack_path = IdRelatedField(["id", "name", "description", "form_display_name"])
    stakeholders = IdRelatedField(many=True)
    ro_to = IdRelatedField(["risk_origin", "target_objective"])
    threats = IdRelatedField(many=True)
    strategic_scenario = serializers.SerializerMethodField()
    likelihood = serializers.JSONField(source="get_likelihood_display")
    gravity = serializers.JSONField(source="get_gravity_display")
    risk_level = serializers.JSONField(source="get_risk_level_display")
    ref_id = serializers.CharField()
    operating_modes_description = serializers.SerializerMethodField()
    operating_modes = IdRelatedField(many=True)

    def get_strategic_scenario(self, obj):
        if obj.attack_path and obj.attack_path.strategic_scenario:
            return IdRelatedField().to_representation(
                obj.attack_path.strategic_scenario
            )
        return None

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


from core.serializers import ThreatReadSerializer


class ElementaryActionReadSerializer(BaseModelSerializer):
    icon = serializers.CharField(source="get_icon_display")
    icon_fa_class = serializers.CharField()
    icon_fa_hex = serializers.CharField()
    threat = IdRelatedField(["id", "name"], serializer=ThreatReadSerializer)
    folder = IdRelatedField()
    attack_stage = serializers.CharField(source="get_attack_stage_display")

    class Meta:
        model = ElementaryAction
        fields = "__all__"


class OperatingModeWriteSerializer(BaseModelSerializer):
    class Meta:
        model = OperatingMode
        exclude = ["created_at", "updated_at"]


class OperatingModeReadSerializer(BaseModelSerializer):
    operational_scenario = IdRelatedField()
    folder = IdRelatedField()
    elementary_actions = IdRelatedField(many=True)
    likelihood = serializers.JSONField(source="get_likelihood_display")
    ebios_rm_study = IdRelatedField()

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
    operating_mode = IdRelatedField()
    elementary_action = IdRelatedField()
    antecedents = IdRelatedField(many=True)
    attack_stage = serializers.CharField()
    folder = IdRelatedField()
    str = serializers.CharField(source="__str__")

    class Meta:
        model = KillChain
        fields = "__all__"
