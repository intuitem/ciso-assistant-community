import ipaddress

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

    class Meta:
        permissions = [
            ("view_central_auditlog", "Can access the central audit log"),
            ("view_object_audittrail", "Can view object audit trails"),
        ]

    def __str__(self):
        return self.name
