from django.conf import settings as django_settings
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
    "mapping_max_depth",
    "allow_self_validation",
    "show_warning_external_links",
    "builtin_metrics_retention_days",
    "allow_assignments_to_entities",
    "enforce_mfa",
    "default_language",
    "llm_provider",
    "ollama_base_url",
    "ollama_model",
    "ollama_embed_model",
    "embedding_backend",
    "chat_system_prompt",
    "openai_api_base",
    "openai_model",
    "openai_api_key",
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
        fields = ["id", "name", "created_at", "updated_at"]


class GeneralSettingsSerializer(serializers.ModelSerializer):
    conversion_rate = serializers.FloatField(
        write_only=True, required=False, default=1.0
    )

    def to_representation(self, instance):
        """Never expose sensitive keys in GET responses (same pattern as integrations)."""
        ret = super().to_representation(instance)
        if "value" in ret and isinstance(ret["value"], dict):
            ret["value"].pop("openai_api_key", None)
        return ret

    def update(self, instance, validated_data):
        # Preserve existing API key if not provided in the update
        if "value" in validated_data and isinstance(validated_data["value"], dict):
            if not validated_data["value"].get("openai_api_key") and instance.value:
                existing_key = instance.value.get("openai_api_key")
                if existing_key:
                    validated_data["value"]["openai_api_key"] = existing_key

        # Track old currency value for potential propagation
        old_currency = instance.value.get("currency") if instance.value else None

        # Extract conversion_rate before validation (it's not stored in settings, just used for conversion)
        conversion_rate = 1.0
        if "value" in validated_data and "conversion_rate" in validated_data["value"]:
            conversion_rate = validated_data["value"].pop("conversion_rate")
        elif "conversion_rate" in validated_data:
            conversion_rate = validated_data.pop("conversion_rate")

        for key, value in validated_data["value"].items():
            if key not in GENERAL_SETTINGS_KEYS:
                raise serializers.ValidationError(f"Invalid key: {key}")
            # Validate builtin_metrics_retention_days minimum value
            if key == "builtin_metrics_retention_days":
                if not isinstance(value, int) or value < 1:
                    raise serializers.ValidationError(
                        {
                            "builtin_metrics_retention_days": "Retention days must be at least 1"
                        }
                    )
            if key == "default_language":
                valid_codes = [code for code, _ in django_settings.LANGUAGES]
                if value not in valid_codes:
                    raise serializers.ValidationError(
                        {
                            "default_language": f"Invalid language. Must be one of: {valid_codes}"
                        }
                    )
            setattr(instance, "value", validated_data["value"])

        # Get new currency value
        new_currency = validated_data["value"].get("currency")

        instance.save()

        # If currency has changed, propagate to AppliedControl records
        if old_currency != new_currency and new_currency:
            self._update_applied_control_currencies(
                old_currency, new_currency, conversion_rate
            )

        return instance

    def _update_applied_control_currencies(
        self, old_currency, new_currency, conversion_rate=1.0
    ):
        """Update currency in all AppliedControl cost structures and apply conversion rate"""
        from core.models import AppliedControl
        from decimal import Decimal

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
                    # Update currency
                    control.cost["currency"] = new_currency

                    # Apply conversion rate to cost amounts
                    if conversion_rate != 1.0:
                        # Convert build costs
                        if "build" in control.cost:
                            if "fixed_cost" in control.cost["build"]:
                                control.cost["build"]["fixed_cost"] = float(
                                    Decimal(str(control.cost["build"]["fixed_cost"]))
                                    * Decimal(str(conversion_rate))
                                )

                        # Convert run costs
                        if "run" in control.cost:
                            if "fixed_cost" in control.cost["run"]:
                                control.cost["run"]["fixed_cost"] = float(
                                    Decimal(str(control.cost["run"]["fixed_cost"]))
                                    * Decimal(str(conversion_rate))
                                )

                    control.save(update_fields=["cost"])
                    updated_count += 1

        print(
            f"Updated currency from '{old_currency}' to '{new_currency}' "
            f"with conversion rate {conversion_rate} in {updated_count} AppliedControl records"
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
    control_plan = serializers.BooleanField(
        source="value.control_plan", required=False, default=True
    )
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
    contracts = serializers.BooleanField(
        source="value.contracts", required=False, default=False
    )
    reports = serializers.BooleanField(
        source="value.reports", required=False, default=False
    )
    validation_flows = serializers.BooleanField(
        source="value.validation_flows", required=False, default=False
    )
    outgoing_webhooks = serializers.BooleanField(
        source="value.outgoing_webhooks", required=False, default=False
    )
    metrology = serializers.BooleanField(
        source="value.metrology", required=False, default=True
    )
    personal_data = serializers.BooleanField(
        source="value.personal_data", required=False, default=True
    )
    purposes = serializers.BooleanField(
        source="value.purposes", required=False, default=True
    )
    right_requests = serializers.BooleanField(
        source="value.right_requests", required=False, default=True
    )
    data_breaches = serializers.BooleanField(
        source="value.data_breaches", required=False, default=True
    )
    chat_mode = serializers.BooleanField(
        source="value.chat_mode", required=False, default=False
    )
    auditee_mode = serializers.BooleanField(
        source="value.auditee_mode", required=False, default=False
    )
    advanced_analytics = serializers.BooleanField(
        source="value.advanced_analytics", required=False, default=False
    )
    comments = serializers.BooleanField(
        source="value.comments", required=False, default=True
    )
    journeys = serializers.BooleanField(
        source="value.journeys", required=False, default=True
    )
    policy_documents = serializers.BooleanField(
        source="value.policy_documents", required=False, default=True
    )

    class Meta:
        model = GlobalSettings
        exclude = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "value",
            "folder",
            "is_published",
        ]
        read_only_fields = ["name"]

    def get_fields(self):
        fields = super().get_fields()
        from django.conf import settings

        if not getattr(settings, "ENABLE_CHAT", False):
            fields.pop("chat_mode", None)
        return fields

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


class VulnerabilitySlaSerializer(serializers.ModelSerializer):
    """
    Serializer for managing Vulnerability SLA policy settings.
    Maps severity levels to remediation deadlines (in days).
    """

    critical = serializers.IntegerField(
        source="value.critical", required=False, allow_null=True, default=None
    )
    high = serializers.IntegerField(
        source="value.high", required=False, allow_null=True, default=None
    )
    medium = serializers.IntegerField(
        source="value.medium", required=False, allow_null=True, default=None
    )
    low = serializers.IntegerField(
        source="value.low", required=False, allow_null=True, default=None
    )
    info = serializers.IntegerField(
        source="value.info", required=False, allow_null=True, default=None
    )

    class Meta:
        model = GlobalSettings
        exclude = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "value",
            "folder",
            "is_published",
        ]
        read_only_fields = ["name"]

    def update(self, instance, validated_data):
        current_value_dict = instance.value if isinstance(instance.value, dict) else {}
        value_changed = False
        new_value_dict = validated_data.get("value", {})

        for field_name, field_instance in self.fields.items():
            if field_name in self.Meta.read_only_fields:
                continue
            if not hasattr(
                field_instance, "source"
            ) or not field_instance.source.startswith("value."):
                continue

            if field_name in new_value_dict:
                source_key = field_instance.source.split(".")[-1]
                new_flag_value = new_value_dict[field_name]

                if current_value_dict.get(source_key) != new_flag_value:
                    if new_flag_value is None:
                        current_value_dict.pop(source_key, None)
                    else:
                        current_value_dict[source_key] = new_flag_value
                    value_changed = True

        if value_changed:
            instance.value = current_value_dict
            instance.save(update_fields=["value"])

        return instance


class SecIntelFeedsSerializer(serializers.ModelSerializer):
    """
    Serializer for managing Security Intelligence feed settings.
    Controls which external feeds are enabled and network parameters.
    """

    kev_feed_enabled = serializers.BooleanField(
        source="value.kev_feed_enabled", required=False, default=False
    )
    epss_feed_enabled = serializers.BooleanField(
        source="value.epss_feed_enabled", required=False, default=False
    )
    nvd_enrich_enabled = serializers.BooleanField(
        source="value.nvd_enrich_enabled", required=False, default=False
    )
    network_timeout = serializers.IntegerField(
        source="value.network_timeout", required=False, default=30
    )

    class Meta:
        model = GlobalSettings
        exclude = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "value",
            "folder",
            "is_published",
        ]
        read_only_fields = ["name"]

    def update(self, instance, validated_data):
        current_value_dict = instance.value if isinstance(instance.value, dict) else {}
        value_changed = False
        new_value_dict = validated_data.get("value", {})

        for field_name, field_instance in self.fields.items():
            if field_name in self.Meta.read_only_fields:
                continue
            if not hasattr(
                field_instance, "source"
            ) or not field_instance.source.startswith("value."):
                continue

            if field_name in new_value_dict:
                source_key = field_instance.source.split(".")[-1]
                new_flag_value = new_value_dict[field_name]

                if current_value_dict.get(source_key) != new_flag_value:
                    current_value_dict[source_key] = new_flag_value
                    value_changed = True

        if value_changed:
            instance.value = current_value_dict
            instance.save(update_fields=["value"])

        return instance
