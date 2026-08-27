import ipaddress

from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.db import models

from iam.models import FolderMixin
from core.base_models import AbstractBaseModel


def validate_ip_or_cidr(value: str) -> None:
    """Validate that ``value`` is a single IP address or a CIDR network."""
    candidate = (value or "").strip()
    try:
        ipaddress.ip_address(candidate)
        return
    except ValueError:
        pass
    try:
        ipaddress.ip_network(candidate, strict=False)
    except ValueError as exc:
        raise ValidationError(
            f"'{value}' is not a valid IP address or CIDR range."
        ) from exc


class GlobalSettings(AbstractBaseModel, FolderMixin):
    """
    Global settings for the application.
    New setting categories should only be added through data migrations.
    """

    class Names(models.TextChoices):
        GENERAL = "general", "General"
        SSO = "sso", "SSO"
        FEATURE_FLAGS = "feature-flags", "Feature Flags"
        VULNERABILITY_SLA = "vulnerability-sla", "Vulnerability SLA"
        SEC_INTEL_FEEDS = "sec-intel-feeds", "Vulnerability Feeds"
        INFRA_CONFIG = "infra-config", "Infra config"

    # Name of the setting category.
    name = models.CharField(
        max_length=30,
        unique=True,
        choices=Names,
        default=Names.GENERAL,
    )
    # Value of the setting.
    value = models.JSONField(default=dict)

    GENERAL_DEFAULT_VALUE = {
        "security_objective_scale": "1-4",
        "ebios_radar_max": 6,
        "ebios_radar_green_zone_radius": 0.2,
        "ebios_radar_yellow_zone_radius": 0.9,
        "ebios_radar_red_zone_radius": 2.5,
        "notifications_enable_mailing": False,
        "interface_agg_scenario_matrix": False,
        "risk_matrix_swap_axes": False,
        "risk_matrix_flip_vertical": False,
        "risk_matrix_labels": "ISO",
        "currency": "€",
        "daily_rate": 500,
        "mapping_max_depth": 3,
        "allow_self_validation": False,
        "show_warning_external_links": True,
        "show_get_started": True,
        "personal_folders": False,
        "builtin_metrics_retention_days": 730,  # 2 years default, minimum is 1
        "allow_assignments_to_entities": False,
        "enforce_mfa": False,
        "default_language": "en",
        "default_custom_analytics_dashboard": None,
        "default_packager": "custom",
        "disable_partially_compliant_result": False,
        "use_risk_category_label": False,
    }
    """Default `value` used when creating a new `GENERAL` GlobalSetting. """

    class Meta:
        permissions = [
            ("view_central_auditlog", "Can access the central audit log"),
            ("view_object_audittrail", "Can view object audit trails"),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def get_daily_rate(cls) -> float:
        gs = cls.objects.filter(name="general").only("value").first()
        return gs.value.get("daily_rate", 500) if gs else 500


# value holds all settings/flags; masked to scrub secrets while keeping the diff.
# ssosettings is the reverse MTI relation to the unmanaged SSOSettings child;
# tracking it makes auditlog query its non-existent table on create/delete.
auditlog.register(
    GlobalSettings,
    exclude_fields=["created_at", "updated_at", "is_published", "ssosettings"],
    mask_fields=["value"],
    mask_callable="global_settings.utils.mask_sensitive_settings",
)
