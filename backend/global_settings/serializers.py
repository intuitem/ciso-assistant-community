import copy
import ipaddress
import re
import uuid
from types import MappingProxyType

import structlog

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models, transaction
from rest_framework import serializers

from urllib.parse import urlparse

from core.utils import get_report_timezone, get_report_timezone_names
from core.net_safety import (
    BlockedRequestError,
    DnsLookupError,
    assert_public_url_unless_dev,
)
from iam.models import User

from .models import GlobalSettings, Mailer, MailerConfiguration, MailerHealth

logger = structlog.get_logger(__name__)


def canonical_ip_or_cidr(value: str) -> str:
    """Return the canonical string form of an IP address or CIDR network.

    Host-bit CIDRs are normalised to their network (e.g. ``10.0.0.7/24`` ->
    ``10.0.0.0/24``) and IPv6 is lower-cased/compressed, so the value published
    to downstream consumers is stable and equivalent ranges dedupe correctly.
    Raises ``DjangoValidationError`` on invalid input.
    """
    candidate = (value or "").strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        pass
    try:
        return str(ipaddress.ip_network(candidate, strict=False))
    except ValueError:
        raise DjangoValidationError(
            f"'{value}' is not a valid IP address or CIDR range."
        )


def validate_default_dashboard_value(value):
    """Validate the default_custom_analytics_dashboard setting value.

    Returns the canonical string form (UUID as str) or None if cleared.
    Raises serializers.ValidationError on bad input.
    Shared by GeneralSettingsSerializer.update and the
    set_default_dashboard view action so the rules don't drift.
    """
    from metrology.models import Dashboard

    if value in (None, ""):
        return None
    try:
        uuid.UUID(str(value))
    except ValueError, TypeError:
        raise serializers.ValidationError(
            {"default_custom_analytics_dashboard": "Must be a valid UUID."}
        )
    if not Dashboard.objects.filter(id=value).exists():
        raise serializers.ValidationError(
            {"default_custom_analytics_dashboard": "Dashboard does not exist."}
        )
    return str(value)


GENERAL_SETTINGS_KEYS = [
    "security_objective_scale",
    "organisation_score_scale",
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
    "show_get_started",
    "builtin_metrics_retention_days",
    "allow_assignments_to_entities",
    "enforce_mfa",
    "default_language",
    "default_date_format",
    "report_timezone",
    "llm_provider",
    "ollama_base_url",
    "ollama_model",
    "ollama_embed_model",
    "embedding_backend",
    "chat_system_prompt",
    "openai_api_base",
    "openai_model",
    "openai_api_key",
    "chat_temperature_enabled",
    "chat_temperature",
    "default_custom_analytics_dashboard",
    "audit_tree_aggregation_strategy",
    "default_landing",
    "default_packager",
    "personal_folders",
    "personal_folders_parent",
    "disable_partially_compliant_result",
    "documentation_score_first",
    "use_risk_category_label",
    "disabled_email_templates",
]

LLM_URL_DEFAULTS = {
    "ollama_base_url": "http://localhost:11434",
    "openai_api_base": "http://localhost:1234/v1",
}


# Proposed on the audit form for frameworks without a scale of their own.
DEFAULT_ORGANISATION_SCORE_SCALE = {
    "score_scale_preset": "0-5",
    "min_score": 0,
    "max_score": 5,
    "scores_definition": [],
}


def _normalize_organisation_score_scale(value):
    from core.models import normalize_score_scale

    if not isinstance(value, dict):
        raise serializers.ValidationError(
            {"organisation_score_scale": "scoreScaleErrorInvalid"}
        )
    levels = value.get("scores_definition")
    if levels is not None and not isinstance(levels, list):
        raise serializers.ValidationError(
            {"organisation_score_scale": "scoreScaleErrorInvalid"}
        )
    try:
        preset, min_score, max_score = normalize_score_scale(
            value.get("score_scale_preset"),
            value.get("min_score"),
            value.get("max_score"),
            levels,
        )
    except DjangoValidationError as e:
        raise serializers.ValidationError({"organisation_score_scale": e.messages})
    if min_score is None:
        raise serializers.ValidationError(
            {"organisation_score_scale": "scoreScaleErrorRangeRequired"}
        )
    return {
        "score_scale_preset": preset,
        "min_score": min_score,
        "max_score": max_score,
        "scores_definition": levels or [],
    }


class GeneralSettingsSerializer(serializers.ModelSerializer):
    conversion_rate = serializers.FloatField(
        write_only=True, required=False, default=1.0
    )

    def to_representation(self, instance):
        """Never expose sensitive keys in GET responses (same pattern as integrations)."""
        ret = super().to_representation(instance)
        if "value" in ret and isinstance(ret["value"], dict):
            ret["value"].pop("openai_api_key", None)
            # Always a value, so the audit form never re-implements the fallback.
            if not ret["value"].get("organisation_score_scale"):
                ret["value"]["organisation_score_scale"] = copy.deepcopy(
                    DEFAULT_ORGANISATION_SCORE_SCALE
                )
        return ret

    def update(self, instance, validated_data):
        # Keys not provided by the client (openai_api_key, per-template email
        # toggles) are preserved from the row under a lock right before save,
        # see below.

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
            if key in ("ollama_base_url", "openai_api_base") and value:
                if not isinstance(value, str):
                    raise serializers.ValidationError({key: "URL must be a string."})
                parsed = urlparse(value)
                if parsed.scheme not in ("http", "https"):
                    raise serializers.ValidationError(
                        {key: "URL must use http or https scheme."}
                    )
                if "#" in value:
                    raise serializers.ValidationError(
                        {key: "URL must not contain a fragment (#)."}
                    )
                stored = (instance.value or {}).get(key)
                if value != stored and value != LLM_URL_DEFAULTS.get(key):
                    try:
                        assert_public_url_unless_dev(
                            value, allowed_schemes=("http", "https")
                        )
                    except BlockedRequestError:
                        raise serializers.ValidationError(
                            {key: "URL must point to a public address."}
                        )
                    except DnsLookupError:
                        raise serializers.ValidationError(
                            {key: "URL hostname could not be resolved."}
                        )
            # Validate builtin_metrics_retention_days minimum value
            if key == "organisation_score_scale":
                validated_data["value"][key] = _normalize_organisation_score_scale(
                    value
                )
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
            if key == "default_date_format":
                # isinstance first: DATE_FORMATS is a set, so an unhashable JSON
                # value (list/dict) would raise TypeError instead of a 400.
                if not isinstance(value, str) or value not in User.DATE_FORMATS:
                    raise serializers.ValidationError(
                        {
                            "default_date_format": f"Invalid date format. Must be one of: {sorted(User.DATE_FORMATS)}"
                        }
                    )
            if key == "report_timezone":
                # A stored name that still loads (a renamed region) stays accepted:
                # the form sends every key, so rejecting it would block saving any
                # other general setting.
                if not isinstance(value, str) or (
                    value not in get_report_timezone_names()
                    and value != get_report_timezone().key
                ):
                    raise serializers.ValidationError(
                        {
                            "report_timezone": "Invalid time zone. Must be an IANA region such as Europe/Paris."
                        }
                    )
            if key == "default_packager":
                # Identity alphabet of library packagers / ref_ids
                # (core.LibraryDraft.IDENTITY_REGEX). fullmatch, not match:
                # `$` would still accept a trailing newline.
                if not isinstance(value, str) or not re.fullmatch(
                    r"[a-z0-9_-]+", value
                ):
                    raise serializers.ValidationError(
                        {"default_packager": "Must match [a-z0-9_-]+."}
                    )
            if key == "disabled_email_templates":
                if not isinstance(value, list) or not all(
                    isinstance(v, str) for v in value
                ):
                    raise serializers.ValidationError(
                        {"disabled_email_templates": "Must be a list of template keys."}
                    )
            if key == "chat_temperature_enabled":
                if not isinstance(value, bool):
                    raise serializers.ValidationError(
                        {"chat_temperature_enabled": "Must be a boolean."}
                    )
            if key == "chat_temperature":
                try:
                    temp = float(value)
                except TypeError, ValueError:
                    raise serializers.ValidationError(
                        {"chat_temperature": "Must be a number."}
                    )
                if not 0 <= temp <= 2:
                    raise serializers.ValidationError(
                        {"chat_temperature": "Must be between 0 and 2."}
                    )
                validated_data["value"][key] = temp
            if key == "default_custom_analytics_dashboard":
                validated_data["value"][key] = validate_default_dashboard_value(value)
        # Get new currency value
        new_currency = validated_data["value"].get("currency")

        with transaction.atomic():
            # Lock and reload the row before merging preserved keys, so this
            # read-merge-write can't overwrite a concurrent writer (e.g. the
            # per-template email toggles endpoint).
            instance = GlobalSettings.objects.select_for_update().get(pk=instance.pk)
            current = instance.value if isinstance(instance.value, dict) else {}
            # Preserve existing API key if not provided in the update
            if not validated_data["value"].get("openai_api_key"):
                existing_key = current.get("openai_api_key")
                if existing_key:
                    validated_data["value"]["openai_api_key"] = existing_key
            # Preserve per-template email toggles if not provided in the update
            # (they are managed from the email templates settings, not the
            # general form)
            if "disabled_email_templates" not in validated_data["value"]:
                existing_disabled = current.get("disabled_email_templates")
                if existing_disabled is not None:
                    validated_data["value"]["disabled_email_templates"] = (
                        existing_disabled
                    )
            instance.value = validated_data["value"]
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

        to_update = []

        # Get all AppliedControl records that have cost data
        for control in AppliedControl.objects.filter(cost__isnull=False).only(
            "id", "cost"
        ):
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

                    to_update.append(control)

        AppliedControl.objects.bulk_update(to_update, ["cost"], batch_size=500)
        logger.info(
            "Applied control currencies updated",
            old_currency=old_currency,
            new_currency=new_currency,
            conversion_rate=conversion_rate,
            count=len(to_update),
        )

    class Meta:
        model = GlobalSettings
        exclude = ["folder"]
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
    risk_management = serializers.BooleanField(
        source="value.risk_management", required=False, default=True
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
    audit_tree_inheritance = serializers.BooleanField(
        source="value.audit_tree_inheritance", required=False, default=False
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
    threat_modeling = serializers.BooleanField(
        source="value.threat_modeling", required=False, default=False
    )
    ttps = serializers.BooleanField(source="value.ttps", required=False, default=False)
    terminologies = serializers.BooleanField(
        source="value.terminologies", required=False, default=True
    )
    bia = serializers.BooleanField(source="value.bia", required=False, default=True)
    project_management = serializers.BooleanField(
        source="value.project_management", required=False, default=False
    )
    # Per-entry switches inside the Project management menu, which
    # `project_management` gates as a whole.
    generic_collections = serializers.BooleanField(
        source="value.generic_collections", required=False, default=True
    )
    accreditations = serializers.BooleanField(
        source="value.accreditations", required=False, default=True
    )
    projects = serializers.BooleanField(
        source="value.projects", required=False, default=True
    )
    responsibility_matrices = serializers.BooleanField(
        source="value.responsibility_matrices", required=False, default=True
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
    workflows = serializers.BooleanField(
        source="value.workflows", required=False, default=False
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
    # Default on: the inbox is the channel that works out of the box, where
    # notifications_enable_mailing defaults off and most installs get nothing.
    notification_center = serializers.BooleanField(
        source="value.notification_center", required=False, default=True
    )
    data_breaches = serializers.BooleanField(
        source="value.data_breaches", required=False, default=True
    )
    dpias = serializers.BooleanField(
        source="value.dpias", required=False, default=False
    )
    chat_mode = serializers.BooleanField(
        source="value.chat_mode", required=False, default=False
    )
    infra_config_management = serializers.BooleanField(
        source="value.infra_config_management", required=False, default=True
    )
    auditee_mode = serializers.BooleanField(
        source="value.auditee_mode", required=False, default=True
    )
    quick_forms = serializers.BooleanField(
        source="value.quick_forms", required=False, default=False
    )
    advanced_analytics = serializers.BooleanField(
        source="value.advanced_analytics", required=False, default=True
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
    document_management = serializers.BooleanField(
        source="value.document_management", required=False, default=True
    )
    security_advisories = serializers.BooleanField(
        source="value.security_advisories", required=False, default=True
    )
    cwes = serializers.BooleanField(source="value.cwes", required=False, default=True)
    vulnerability_sla = serializers.BooleanField(
        source="value.vulnerability_sla", required=False, default=True
    )
    custom_portals = serializers.BooleanField(
        source="value.custom_portals", required=False, default=False
    )
    posture_assessments = serializers.BooleanField(
        source="value.posture_assessments", required=False, default=False
    )
    commitment_management = serializers.BooleanField(
        source="value.commitment_management", required=False, default=False
    )
    findings_from_requirements = serializers.BooleanField(
        source="value.findings_from_requirements", required=False, default=False
    )
    dora = serializers.BooleanField(source="value.dora", required=False, default=True)
    external_ratings = serializers.BooleanField(
        source="value.external_ratings", required=False, default=False
    )
    jit_provisioning = serializers.BooleanField(
        source="value.jit_provisioning", required=False, default=False
    )
    relations_graph = serializers.BooleanField(
        source="value.relations_graph", required=False, default=False
    )

    # Flags a user may switch off for themselves. Opt-in, like batch actions: a
    # new flag is not hideable until listed. Eligible means it hides a navigation
    # area and nothing else — a flag that also gates data rendering, a write path,
    # role behaviour or IAM config would make two users read different data.
    USER_HIDEABLE_FLAGS = frozenset(
        {
            "accreditations",
            "bia",
            "commitment_management",
            "compliance",
            "contracts",
            "control_plan",
            "custom_portals",
            "data_breaches",
            "dpias",
            "document_management",
            "ebiosrm",
            "exceptions",
            "experimental",
            "follow_up",
            "generic_collections",
            "incidents",
            "journeys",
            "metrology",
            "notification_center",
            "organisation_issues",
            "organisation_objectives",
            "personal_data",
            "posture_assessments",
            "privacy",
            "project_management",
            "projects",
            "purposes",
            "quantitative_risk_studies",
            "quick_forms",
            "reports",
            "responsibility_matrices",
            "right_requests",
            "risk_acceptances",
            "risk_management",
            "scoring_assistant",
            "security_advisories",
            "cwes",
            "tasks",
            "threat_modeling",
            "tprm",
            "ttps",
            "validation_flows",
            "vulnerabilities",
            "workflows",
            "xrays",
        }
    )

    # Flags that only work with others on: turning one on turns those on too, and
    # turning one of those off turns it off (see utils.apply_flag_requirements).
    FLAG_REQUIRES = MappingProxyType(
        {
            # DPIAs are quick forms: screenings and assessments are responses.
            "dpias": frozenset({"quick_forms"}),
            # The SLA computes vulnerability due dates.
            "vulnerability_sla": frozenset({"vulnerabilities"}),
        }
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
        ]
        read_only_fields = ["name"]

    def get_fields(self):
        fields = super().get_fields()
        from django.conf import settings

        if not getattr(settings, "ENABLE_CHAT", False):
            fields.pop("chat_mode", None)
        if not getattr(settings, "ENABLE_INFRA_CONFIG_MANAGEMENT", False):
            fields.pop("infra_config_management", None)
        return fields

    def update(self, instance, validated_data):
        """
        Custom update logic to handle saving changes to the nested 'value' field,
        iterating directly over the serializer's fields.
        """
        # Local import: utils imports this module at load time.
        from global_settings.utils import (
            apply_flag_requirements,
            clear_feature_flags_cache,
        )

        current_value_dict = instance.value if isinstance(instance.value, dict) else {}
        value_changed = False
        idp_groups_changed = False
        turned_off = set()
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

            # A dependent flag a full PUT leaves out keeps its stored value: its
            # default could otherwise switch on the flags it needs (FLAG_REQUIRES).
            if (
                field_name in self.FLAG_REQUIRES
                and not self.partial
                and field_name not in self.initial_data
            ):
                continue

            if field_name in new_value_dict:
                # Get the key name used within the 'value' dictionary (e.g., 'xrays')
                source_key = field_instance.source.split(".")[-1]
                new_flag_value = new_value_dict[field_name]

                if current_value_dict.get(source_key) != new_flag_value:
                    if current_value_dict.get(source_key) and not new_flag_value:
                        turned_off.add(source_key)
                    current_value_dict[source_key] = new_flag_value
                    value_changed = True
                    if source_key == "idp_groups":
                        idp_groups_changed = True

        before_requirements = dict(current_value_dict)
        apply_flag_requirements(current_value_dict, turned_off)
        value_changed = value_changed or current_value_dict != before_requirements

        if value_changed:
            instance.value = current_value_dict
            instance.save(update_fields=["value"])
            # Every flags write must invalidate the read cache; the only other
            # write path is PresetExecutor._apply_feature_flags, which does
            # the same.
            clear_feature_flags_cache()

        return instance


class VulnerabilitySlaSerializer(serializers.ModelSerializer):
    """
    Serializer for managing Vulnerability SLA policy settings.
    Maps severity levels to remediation deadlines (in days).
    """

    sla_anchor = serializers.ChoiceField(
        source="value.sla_anchor",
        choices=["detected_at", "published_date"],
        required=False,
        default="detected_at",
    )
    critical = serializers.IntegerField(
        source="value.critical", required=False, allow_null=True
    )
    high = serializers.IntegerField(
        source="value.high", required=False, allow_null=True
    )
    medium = serializers.IntegerField(
        source="value.medium", required=False, allow_null=True
    )
    low = serializers.IntegerField(source="value.low", required=False, allow_null=True)
    info = serializers.IntegerField(
        source="value.info", required=False, allow_null=True
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


MAX_ALLOWED_IPS = 50


class InfraConfigSerializer(serializers.ModelSerializer):
    """
    Serializer for infrastructure configuration settings, stored as a JSON object
    in the 'value' field of a GlobalSettings instance (singleton). Currently holds
    the list of IPs/CIDRs allowed to reach the backend API; new keys can be added
    over time without a schema change.
    """

    allowed_ips = serializers.ListField(
        child=serializers.CharField(),
        source="value.allowed_ips",
        required=False,
        default=list,
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
        ]
        read_only_fields = ["name"]

    def validate_allowed_ips(self, value):
        cleaned = []
        errors = []
        seen = set()
        for raw in value:
            ip = (raw or "").strip()
            if not ip:
                continue
            try:
                canonical = canonical_ip_or_cidr(ip)
            except DjangoValidationError as exc:
                errors.extend(exc.messages)
                continue
            # Dedupe on the canonical form so equivalent ranges (e.g.
            # 10.0.0.0/24 and 10.0.0.7/24) collapse to a single entry.
            if canonical in seen:
                continue
            seen.add(canonical)
            cleaned.append(canonical)
        if errors:
            raise serializers.ValidationError(errors)
        if len(cleaned) > MAX_ALLOWED_IPS:
            raise serializers.ValidationError(
                f"You can add at most {MAX_ALLOWED_IPS} IP addresses."
            )
        return cleaned

    def update(self, instance, validated_data):
        current_value_dict = instance.value if isinstance(instance.value, dict) else {}
        new_value_dict = validated_data.get("value", {})
        value_changed = False

        for field_name, field_instance in self.fields.items():
            if field_name in self.Meta.read_only_fields:
                continue
            if not hasattr(
                field_instance, "source"
            ) or not field_instance.source.startswith("value."):
                continue
            if field_name in new_value_dict:
                source_key = field_instance.source.split(".")[-1]
                new_val = new_value_dict[field_name]
                if current_value_dict.get(source_key) != new_val:
                    current_value_dict[source_key] = new_val
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
        source="value.network_timeout",
        required=False,
        default=30,
        min_value=5,
        max_value=120,
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


class MailerSerializer(serializers.ModelSerializer):
    """One mailer row. Secrets are write-only; ``has_*`` says whether one is
    stored. A blank secret on an existing position keeps the stored one."""

    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=False
    )
    oauth2_client_secret = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=False
    )
    oauth2_refresh_token = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=False
    )
    oauth2_private_key = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=False
    )
    has_password = serializers.SerializerMethodField()
    has_oauth2_client_secret = serializers.SerializerMethodField()
    has_oauth2_refresh_token = serializers.SerializerMethodField()
    has_oauth2_private_key = serializers.SerializerMethodField()

    class Meta:
        model = Mailer
        fields = [
            "position",
            "transport",
            "host",
            "port",
            "use_tls",
            "use_ssl",
            "username",
            "password",
            "has_password",
            "oauth2_grant_type",
            "oauth2_token_url",
            "oauth2_scope",
            "oauth2_client_id",
            "oauth2_client_secret",
            "has_oauth2_client_secret",
            "oauth2_refresh_token",
            "has_oauth2_refresh_token",
            "oauth2_issuer",
            "oauth2_private_key",
            "has_oauth2_private_key",
            "oauth2_audience",
            "graph_tenant_id",
        ]

    def get_has_password(self, obj) -> bool:
        return bool(obj.password)

    def get_has_oauth2_client_secret(self, obj) -> bool:
        return bool(obj.oauth2_client_secret)

    def get_has_oauth2_refresh_token(self, obj) -> bool:
        return bool(obj.oauth2_refresh_token)

    def get_has_oauth2_private_key(self, obj) -> bool:
        return bool(obj.oauth2_private_key)


class MailerConfigurationSerializer(serializers.ModelSerializer):
    """The stored configuration with its mailers. Saving requires a test token
    issued by the test endpoint for these exact values, or an explicit
    override (custom-mailer-settings ADR)."""

    mailers = MailerSerializer(many=True)
    test_token = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
    override_untested = serializers.BooleanField(
        write_only=True, required=False, default=False
    )

    class Meta:
        model = MailerConfiguration
        fields = [
            "is_active",
            "from_email",
            "last_tested_at",
            "mailers",
            "test_token",
            "override_untested",
        ]
        read_only_fields = ["last_tested_at"]

    def validate_mailers(self, mailers):
        positions = [item.get("position") for item in mailers]
        if not mailers or len(mailers) > 2:
            raise serializers.ValidationError("Configure one or two mailers.")
        if sorted(positions) != list(range(1, len(mailers) + 1)):
            raise serializers.ValidationError("Mailer positions must be 1, then 2.")
        return mailers

    def validate(self, attrs):
        if attrs.get("is_active") and not attrs.get("from_email"):
            raise serializers.ValidationError(
                {"from_email": "A sender address is required to activate the mailers."}
            )
        return attrs

    def build_rows(self, instance, mailers_data) -> list[Mailer]:
        """Unsaved rows for the payload: existing rows at the same position
        are updated in place, blank secrets keep the stored value. Validates
        each row the way the environment builder validates its variables."""
        from .mailer_settings import network_problems

        existing = {row.position: row for row in instance.mailers.all()}
        rows = []
        for item in mailers_data:
            row = existing.get(item["position"]) or Mailer(
                configuration=instance,
                position=item["position"],
                folder=instance.folder,
            )
            for name, value in item.items():
                if name in Mailer.SECRET_FIELDS and value in ("", None):
                    continue
                if value is None and isinstance(
                    Mailer._meta.get_field(name), (models.CharField, models.TextField)
                ):
                    # Text columns are NOT NULL; a cleared port stays NULL and
                    # the backend picks the standard port for the TLS mode.
                    value = ""
                setattr(row, name, value)
            # Problems are reported as our own messages, never as exception
            # text: nothing raised below the API may reach the caller.
            problems = row.configuration_problems() or network_problems(row)
            if problems:
                raise serializers.ValidationError(
                    {"mailers": f"mailer {item['position']}: {problems[0]}"}
                )
            rows.append(row)
        return rows

    def update(self, instance, validated_data):
        from django.utils import timezone

        from .mailer_settings import (
            configuration_digest,
            specs_from_rows,
            test_token_matches,
        )

        mailers_data = validated_data.pop("mailers")
        token = validated_data.pop("test_token", "")
        override = validated_data.pop("override_untested", False)
        rows = self.build_rows(instance, mailers_data)
        from_email = validated_data.get("from_email", instance.from_email)
        tested = test_token_matches(
            token, configuration_digest(from_email, specs_from_rows(rows))
        )
        if not tested and not override:
            raise serializers.ValidationError(
                {
                    "test_token": "Send a test email with these exact values before saving, "
                    "or set override_untested."
                }
            )
        with transaction.atomic():
            instance.is_active = validated_data.get("is_active", instance.is_active)
            instance.from_email = from_email
            if tested:
                instance.last_tested_at = timezone.now()
            instance.save()
            keep = {row.position for row in rows}
            instance.mailers.exclude(position__in=keep).delete()
            for row in rows:
                row.save()
        return instance


class MailerHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = MailerHealth
        fields = [
            "alias",
            "source",
            "last_attempt_at",
            "last_outcome",
            "last_error",
            "via_failover",
            "last_success_at",
        ]
