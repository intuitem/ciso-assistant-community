import ipaddress

from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.db import models

from iam.models import Folder, FolderMixin
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
        TPRM = "tprm", "TPRM"

    # Name of the setting category.
    name = models.CharField(
        max_length=30,
        unique=True,
        choices=Names,
        default=Names.GENERAL,
    )
    # Value of the setting.
    value = models.JSONField(default=dict)

    # All sensitive global settings (e.g. `SSO`, `INFRA_CONFIG`) MUST have extra permission checks on their API views.
    # Otherwise anyone with a `"view_globalsettings"` permission on any folder could view these sensitive global settings (as `GlobalSettings` are always stored in the root folder).
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
        "default_date_format": "auto",
        "default_custom_analytics_dashboard": None,
        "default_packager": "custom",
        "disable_partially_compliant_result": False,
        # Score pairs show documentation before implementation (CyFun tools).
        "documentation_score_first": False,
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
    exclude_fields=["created_at", "updated_at", "ssosettings"],
    mask_fields=["value"],
    mask_callable="global_settings.utils.mask_sensitive_settings",
)


class MailerConfiguration(AbstractBaseModel, FolderMixin):
    """The outgoing-mail configuration an administrator stores in the app.

    One row per instance. When ``ENABLE_CUSTOM_MAILER`` is set and
    ``is_active`` is true, its mailers replace the environment ones entirely;
    otherwise the environment applies. See the custom-mailer-settings ADR.
    """

    is_active = models.BooleanField(default=False)
    from_email = models.CharField(max_length=254, blank=True)
    last_tested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Mailer configuration"

    @classmethod
    def get(cls) -> "MailerConfiguration":
        instance = cls.objects.order_by("created_at").first()
        return instance or cls.objects.create()

    def __str__(self):
        return "mailer configuration"


class Mailer(AbstractBaseModel, FolderMixin):
    """One mailer of the stored configuration. Position 1 is tried first,
    position 2 only when 1 cannot be reached. The fields are what a
    ``MAILERS`` entry holds; secrets are write-only through the API."""

    class Transport(models.TextChoices):
        SMTP = "smtp", "SMTP with a password"
        SMTP_OAUTH2 = "smtp-oauth2", "SMTP with OAuth 2.0"
        GRAPH = "graph", "Microsoft Graph"

    class Grant(models.TextChoices):
        CLIENT_CREDENTIALS = "client_credentials", "Client credentials"
        REFRESH_TOKEN = "refresh_token", "Refresh token"
        JWT_BEARER = "jwt_bearer", "JWT bearer"

    SECRET_FIELDS = (
        "password",
        "oauth2_client_secret",
        "oauth2_refresh_token",
        "oauth2_private_key",
    )

    configuration = models.ForeignKey(
        MailerConfiguration, on_delete=models.CASCADE, related_name="mailers"
    )
    position = models.PositiveSmallIntegerField()
    transport = models.CharField(
        max_length=16, choices=Transport.choices, default=Transport.SMTP
    )
    # Blank for Microsoft Graph, which has no host of the operator's.
    host = models.CharField(max_length=253, blank=True)
    port = models.PositiveIntegerField(null=True, blank=True)
    use_tls = models.BooleanField(default=False)
    use_ssl = models.BooleanField(default=False)
    username = models.CharField(max_length=254, blank=True)
    password = models.TextField(blank=True)
    oauth2_grant_type = models.CharField(
        max_length=32, choices=Grant.choices, blank=True
    )
    oauth2_token_url = models.CharField(max_length=2048, blank=True)
    oauth2_scope = models.CharField(max_length=1024, blank=True)
    oauth2_client_id = models.CharField(max_length=512, blank=True)
    oauth2_client_secret = models.TextField(blank=True)
    oauth2_refresh_token = models.TextField(blank=True)
    oauth2_issuer = models.CharField(max_length=512, blank=True)
    oauth2_private_key = models.TextField(blank=True)
    oauth2_audience = models.CharField(max_length=2048, blank=True)
    graph_tenant_id = models.CharField(max_length=253, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["configuration", "position"], name="unique_mailer_position"
            )
        ]

    @property
    def alias(self) -> str:
        return f"custom-{self.position}"

    def __str__(self):
        target = self.graph_tenant_id if self.is_graph else self.host
        return f"{self.alias} ({self.transport} {target})"

    @property
    def is_graph(self) -> bool:
        return self.transport == self.Transport.GRAPH

    def graph_config(self) -> dict:
        """The Graph configuration for this row, unvalidated. The client
        credentials share the OAuth columns."""
        return {
            "tenant_id": self.graph_tenant_id or None,
            "client_id": self.oauth2_client_id or None,
            "client_secret": self.oauth2_client_secret or None,
            "mailbox": self.username or None,
        }

    def oauth2_config(self) -> dict:
        """The ``oauth2`` option for this row, unvalidated."""
        return {
            "user": self.username or None,
            "grant_type": self.oauth2_grant_type or None,
            "token_url": self.oauth2_token_url or None,
            "scope": self.oauth2_scope or None,
            "client_id": self.oauth2_client_id or None,
            "client_secret": self.oauth2_client_secret or None,
            "refresh_token": self.oauth2_refresh_token or None,
            "service_account_file": None,
            "issuer": self.oauth2_issuer or None,
            "private_key": self.oauth2_private_key or None,
            "audience": self.oauth2_audience or None,
        }

    def configuration_problems(self) -> list[str]:
        """Why this row cannot be used, as operator-facing messages, checked
        the way the environment builder validates its variables. Empty when
        the row is usable. Never raises: the settings API reports these
        messages to the caller, and no exception text must reach it."""
        from ciso_assistant.mailers import graph_problems, oauth2_problems

        if self.is_graph:
            return graph_problems(self.graph_config())
        problems = []
        if not self.host:
            problems.append("a host is required")
        if self.use_tls and self.use_ssl:
            problems.append("TLS and SSL are mutually exclusive")
        if self.transport == self.Transport.SMTP_OAUTH2:
            problems.extend(oauth2_problems(self.oauth2_config()))
        return problems

    def mailer_entry(self) -> dict:
        """The ``MAILERS``-shaped entry for this row. Raises ValueError with
        the first configuration problem."""
        from ciso_assistant.mailers import SMTP_BACKEND, graph_entry

        problems = self.configuration_problems()
        if problems:
            raise ValueError(problems[0])
        if self.is_graph:
            return graph_entry(self.graph_config(), timeout=15)
        options = {
            "host": self.host,
            "port": self.port,
            "username": self.username or None,
            "password": self.password or None,
            "use_tls": self.use_tls,
            "use_ssl": self.use_ssl,
            "timeout": 5,
        }
        if self.transport == self.Transport.SMTP_OAUTH2:
            options["password"] = None
            options["oauth2"] = self.oauth2_config()
        return {"BACKEND": SMTP_BACKEND, "OPTIONS": options}


class MailerHealth(AbstractBaseModel):
    """Last delivery attempt per mailer, updated in place so it never grows.
    Written by ``core.mailer`` for environment and custom mailers alike."""

    # Not a scoped object: read only through the mailer settings endpoint,
    # which checks the permission on the root folder itself.
    IAM_SCOPE_FIELD = Folder.IAM_NOT_IMPLEMENTED

    class Outcome(models.TextChoices):
        OK = "ok", "Delivered"
        UNREACHABLE = "unreachable", "Unreachable"
        FAILED = "failed", "Failed after handover"

    alias = models.CharField(max_length=64, unique=True)
    source = models.CharField(max_length=16)  # "environment" or "custom"
    last_attempt_at = models.DateTimeField()
    last_outcome = models.CharField(max_length=16, choices=Outcome.choices)
    last_error = models.TextField(blank=True)
    via_failover = models.BooleanField(default=False)
    last_success_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["alias"]
        verbose_name_plural = "Mailer health"


auditlog.register(
    MailerConfiguration, exclude_fields=["created_at", "updated_at", "last_tested_at"]
)
auditlog.register(
    Mailer,
    exclude_fields=["created_at", "updated_at"],
    mask_fields=list(Mailer.SECRET_FIELDS),
    mask_callable="global_settings.utils.redact_secret_value",
)
