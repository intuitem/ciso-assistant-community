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
    "currency",
    "daily_rate",
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
        # Track old currency value for potential propagation
        old_currency = instance.value.get("currency") if instance.value else None

        for key, value in validated_data["value"].items():
            if key not in GENERAL_SETTINGS_KEYS:
                raise serializers.ValidationError(f"Invalid key: {key}")
            setattr(instance, "value", validated_data["value"])

        # Get new currency value
        new_currency = validated_data["value"].get("currency")

        instance.save()

        # If currency has changed, propagate to AppliedControl records
        if old_currency != new_currency and new_currency:
            self._update_applied_control_currencies(old_currency, new_currency)

        return instance

    def _update_applied_control_currencies(self, old_currency, new_currency):
        """Update currency in all AppliedControl cost structures"""
        from core.models import AppliedControl

        updated_count = 0

        # Get all AppliedControl records that have cost data
        for control in AppliedControl.objects.filter(cost__isnull=False):
            if isinstance(control.cost, dict):
                current_currency = control.cost.get("currency")

                # Update if:
                # 1. Control's currency matches the old global currency, OR
                # 2. Old global currency was None (first time setting global currency), OR
                # 3. Control has no currency set
                should_update = (
                    current_currency == old_currency
                    or old_currency is None
                    or current_currency is None
                )

                if should_update:
                    control.cost["currency"] = new_currency
                    control.save(update_fields=["cost"])
                    updated_count += 1

        print(
            f"Updated currency from '{old_currency}' to '{new_currency}' "
            f"in {updated_count} AppliedControl records"
        )

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
    terminologies = serializers.BooleanField(
        source="value.terminologies", required=False, default=True
    )
    bia = serializers.BooleanField(source="value.bia", required=False, default=True)
    project_management = serializers.BooleanField(
        source="value.project_management", required=False, default=False
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
            "terminologies",
            "bia",
            "project_management",
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
