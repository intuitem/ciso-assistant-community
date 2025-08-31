from rest_framework import serializers

from .models import GlobalSettings

GENERAL_SETTINGS_KEYS = [
    "security_objective_scale",
    "ebios_radar_max",
    "ebios_radar_green_zone_radius",
    "ebios_radar_yellow_zone_radius",
    "ebios_radar_red_zone_radius",
    "interface_agg_scenario_matrix",
    "notifications_enable_mailing",
    "risk_matrix_swap_axes",
    "risk_matrix_flip_vertical",
    "risk_matrix_labels",
]


class GlobalSettingsSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        raise serializers.ValidationError(
            "Global settings can only be created through data migrations."
        )

    def delete(self, instance):
        raise serializers.ValidationError(
            "Global settings can only be deleted through data migrations."
        )

    def update(self, instance, validated_data):
        validated_data.pop("name")
        return super().update(instance, validated_data)

    class Meta:
        model = GlobalSettings
        fields = "__all__"


class GeneralSettingsSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        for key, value in validated_data["value"].items():
            if key not in GENERAL_SETTINGS_KEYS:
                raise serializers.ValidationError(f"Invalid key: {key}")
            setattr(instance, "value", validated_data["value"])
        instance.save()
        return instance

    class Meta:
        model = GlobalSettings
        exclude = ["is_published", "folder"]
        read_only_fields = ["name"]


class FeatureFlagsSerializer(serializers.ModelSerializer):
    """
    Serializer for managing Feature Flags stored within the 'value' JSON field
    of a GlobalSettings instance. Each flag is represented as an explicit
    BooleanField, mapping directly to keys within the 'value' dictionary.
    """

    xrays = serializers.BooleanField(source="value.xrays", required=False, default=True)
    incidents = serializers.BooleanField(
        source="value.incidents", required=False, default=True
    )
    tasks = serializers.BooleanField(source="value.tasks", required=False, default=True)
    risk_acceptances = serializers.BooleanField(
        source="value.risk_acceptances", required=False, default=True
    )
    exceptions = serializers.BooleanField(
        source="value.exceptions", required=False, default=True
    )
    follow_up = serializers.BooleanField(
        source="value.follow_up", required=False, default=True
    )
    ebiosrm = serializers.BooleanField(
        source="value.ebiosrm", required=False, default=True
    )
    scoring_assistant = serializers.BooleanField(
        source="value.scoring_assistant", required=False, default=True
    )
    vulnerabilities = serializers.BooleanField(
        source="value.vulnerabilities", required=False, default=True
    )
    compliance = serializers.BooleanField(
        source="value.compliance", required=False, default=True
    )
    tprm = serializers.BooleanField(source="value.tprm", required=False, default=True)
    privacy = serializers.BooleanField(
        source="value.privacy", required=False, default=True
    )
    experimental = serializers.BooleanField(
        source="value.experimental", required=False, default=True
    )
    inherent_risk = serializers.BooleanField(
        source="value.inherent_risk", required=False, default=False
    )
    organisation_objectives = serializers.BooleanField(
        source="value.organisation_objectives", required=False, default=True
    )
    organisation_issues = serializers.BooleanField(
        source="value.organisation_issues", required=False, default=True
    )
    quantitative_risk_studies = serializers.BooleanField(
        source="value.quantitative_risk_studies", required=False, default=True
    )

    class Meta:
        model = GlobalSettings
        fields = [
            "xrays",
            "incidents",
            "tasks",
            "risk_acceptances",
            "exceptions",
            "follow_up",
            "ebiosrm",
            "scoring_assistant",
            "vulnerabilities",
            "compliance",
            "tprm",
            "privacy",
            "experimental",
            "inherent_risk",
            "organisation_objectives",
            "organisation_issues",
            "quantitative_risk_studies",
        ]
        read_only_fields = ["name"]

    def update(self, instance, validated_data):
        """
        Custom update logic to handle saving changes to the nested 'value' field,
        iterating directly over the serializer's fields.
        """
        current_value_dict = instance.value if isinstance(instance.value, dict) else {}
        value_changed = False
        new_value_dict = validated_data.get("value", {})

        for field_name, field_instance in self.fields.items():
            # Skip read-only fields or fields not intended for the 'value' dict
            # Use Meta.read_only_fields for robustness
            if field_name in self.Meta.read_only_fields:
                continue

            if not hasattr(
                field_instance, "source"
            ) or not field_instance.source.startswith("value."):
                continue  # Skip fields not mapped to the 'value' dictionary

            if field_name in new_value_dict:
                # Get the key name used within the 'value' dictionary (e.g., 'xrays')
                source_key = field_instance.source.split(".")[-1]
                new_flag_value = new_value_dict[field_name]

                if current_value_dict.get(source_key) != new_flag_value:
                    current_value_dict[source_key] = new_flag_value
                    value_changed = True

        if value_changed:
            instance.value = current_value_dict
            instance.save(update_fields=["value"])

        return instance
