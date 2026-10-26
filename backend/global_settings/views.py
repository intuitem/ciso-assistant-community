from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from core.permissions import IsGlobalAdmin
from core.serializers import SerializerFactory
from iam.models import Folder, Permission, RoleAssignment, User
from iam.sso.models import SSOSettings
from integrations.models import IntegrationConfiguration, IntegrationProvider
from core.serializers import SerializerFactory
from django.conf import settings
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.views.decorators.http import require_GET
from .utils import (
    get_instance_feature_flags,
    get_user_hidden_feature_flags,
    get_user_hideable_feature_flags,
    resolve_feature_flags,
)
from .serializers import (
    GeneralSettingsSerializer,
    FeatureFlagsSerializer,
    VulnerabilitySlaSerializer,
    SecIntelFeedsSerializer,
    InfraConfigSerializer,
)
from django.db import transaction
from .models import GlobalSettings, MailerConfiguration, MailerHealth
from core import mailer as mail_service
import structlog

logger = structlog.get_logger(__name__)


class GlobalSettingsSerializerFactory(SerializerFactory):
    """Factory to get a serializer class from a list of modules.
    Attributes:
    modules (list): List of module names to search for the serializer.
    """

    def __init__(self, *modules: str):
        # Reverse to prioritize later modules
        self.modules = list(reversed(modules))

    def get_serializer(self, base_name: str, action: str = "default"):
        return self._get_serializer_class(f"{base_name}Serializer")


class FeatureFlagsViewSet(viewsets.ModelViewSet):
    model = GlobalSettings
    serializer_class = FeatureFlagsSerializer
    queryset = GlobalSettings.objects.filter(name=GlobalSettings.Names.FEATURE_FLAGS)
    serializers_module = "global_settings.serializers"

    def get_serializer_class(self, **kwargs):
        serializer_factory = GlobalSettingsSerializerFactory(
            self.serializers_module, settings.MODULE_PATHS.get("serializers", [])
        )
        serializer_class = serializer_factory.get_serializer(
            "FeatureFlags", kwargs.get("action", "default")
        )
        logger.debug(
            "Serializer class",
            serializer_class=serializer_class,
            action=kwargs.get("action", self.action),
            viewset=self,
            module_paths=settings.MODULE_PATHS,
        )

        return serializer_class

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except PermissionDenied:
            # We want users to be able to see `FEATURE_FLAGS` global settings, even when they don't have the "view_globalsettings" permission.
            instance = FeatureFlagsViewSet.queryset.first()

        serializer = self.get_serializer_class()(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer_class()(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_object(self):
        obj, _ = self.model.objects.get_or_create(name="feature-flags")
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def effective(self, request, pk=None):
        """The instance flags narrowed by the caller's hides.

        Separate from `retrieve`, which stays the raw row: the admin form reads
        that one and PUTs the whole body back, so serving the narrowed view
        there would save an admin's personal hides instance-wide.
        """
        hideable = get_user_hideable_feature_flags()
        instance_flags = get_instance_feature_flags()
        return Response(
            {
                "flags": resolve_feature_flags(request.user),
                "hideable": sorted(hideable),
                "hidden": sorted(get_user_hidden_feature_flags(request.user)),
                # Un-narrowed, so the UI can tell "you hid this" from "your
                # organisation disabled it" — false in `flags` either way.
                "instance": {
                    name: instance_flags.get(name, False) for name in hideable
                },
            }
        )

    @action(detail=True, methods=["get"])
    def defaults(self, request, pk=None):
        """Expose each flag's serializer default so the frontend "Reset to
        defaults" never drifts from the backend. Only exposed flags are
        returned (get_fields already drops gated ones like chat_mode)."""
        serializer = self.get_serializer_class()()
        flag_defaults = {
            name: field.default
            for name, field in serializer.fields.items()
            if name not in serializer.Meta.read_only_fields
            and getattr(field, "default", serializers.empty) is not serializers.empty
        }
        return Response(flag_defaults)


class GeneralSettingsViewSet(viewsets.ModelViewSet):
    model = GlobalSettings
    serializer_class = GeneralSettingsSerializer
    queryset = GlobalSettings.objects.filter(name=GlobalSettings.Names.GENERAL)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except PermissionDenied:
            # We want users to be able to see `GENERAL` global settings, even when they don't have the "view_globalsettings" permission.
            instance = GeneralSettingsViewSet.queryset.first()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Clear cached LLM/embedder so new settings take effect immediately
        from django.conf import settings as django_settings

        if getattr(django_settings, "ENABLE_CHAT", False):
            from chat.providers import clear_provider_cache

            clear_provider_cache()
        return Response(serializer.data)

    def get_object(self):
        obj = self.model.objects.get(name=GlobalSettings.Names.GENERAL)
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, name="Get write data")
    def object(self, request, pk=None):
        default_settings = GlobalSettings.GENERAL_DEFAULT_VALUE

        settings, created = GlobalSettings.objects.get_or_create(name="general")

        if created or not all(key in settings.value for key in default_settings):
            existing_value = settings.value or {}
            updated_value = {**default_settings, **existing_value}
            settings.value = updated_value
            settings.save()

        # Only configurations the caller can reach: the ids are consumed as a
        # "is an integration usable here" signal, and an unscoped list handed
        # every domain's configuration UUIDs to any authenticated user.

        accessible_config_ids = RoleAssignment.get_viewable_object_ids(
            request.user, IntegrationConfiguration
        )

        settings.value["enabled_integrations"] = [
            {
                "id": provider.id,
                "provider_type": provider.provider_type,
                "name": provider.name,
                "configurations": [
                    str(config_id)
                    for config_id in provider.configurations.filter(
                        id__in=accessible_config_ids
                    ).values_list("id", flat=True)
                ],
            }
            for provider in IntegrationProvider.objects.filter(is_active=True)
        ]

        return Response(GeneralSettingsSerializer(settings).data.get("value"))

    @action(detail=True, name="Get available languages")
    def default_language(self, request, pk=None):
        choices = {code: name for code, name in settings.LANGUAGES}
        return Response(choices)

    @action(
        detail=True,
        methods=["post"],
        name="Set default custom analytics dashboard",
        url_path="set-default-dashboard",
    )
    def set_default_dashboard(self, request, pk=None):
        """Partial update of the default_custom_analytics_dashboard key.

        Guarded by change_globalsettings so non-admins can't change the
        org-wide default from the analytics Custom tab.

        Note: this bypasses GeneralSettingsSerializer.update on purpose
        because that serializer replaces the entire `value` dict with the
        payload (no real PATCH semantics). For this single-key change we
        merge into the existing dict. If the general settings ever grow
        cross-key side effects beyond currency propagation, route this
        through the serializer instead.
        """
        from .serializers import validate_default_dashboard_value

        perm = Permission.objects.get(codename="change_globalsettings")
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=perm,
            folder=Folder.get_root_folder(),
        ):
            return Response(
                {"error": "You do not have permission to change global settings."},
                status=403,
            )

        try:
            new_value = validate_default_dashboard_value(
                request.data.get("dashboard_id")
            )
        except serializers.ValidationError as exc:
            return Response({"error": exc.detail}, status=400)

        settings_obj, _ = GlobalSettings.objects.get_or_create(name="general")
        if not isinstance(settings_obj.value, dict):
            settings_obj.value = {}
        settings_obj.value["default_custom_analytics_dashboard"] = new_value
        # Include updated_at because AbstractBaseModel uses auto_now and Django
        # only refreshes auto_now fields named in update_fields.
        settings_obj.save(update_fields=["value", "updated_at"])
        return Response({"default_custom_analytics_dashboard": new_value})

    @action(detail=True, name="Get available dashboards for the custom analytics tab")
    def default_custom_analytics_dashboard(self, request, pk=None):
        """Return a {dashboard_uuid: dashboard_name} map of dashboards
        the requester can see, so an admin can pick one as the
        instance default for the analytics Custom tab.
        """
        from metrology.models import Dashboard

        accessible_ids = RoleAssignment.get_viewable_object_ids(request.user, Dashboard)
        dashboards = Dashboard.objects.filter(id__in=accessible_ids).order_by("name")
        choices = {"": "—"}
        for d in dashboards:
            choices[str(d.id)] = d.name
        return Response(choices)

    @action(detail=True, methods=["post"], name="Force language for all users")
    def force_language(self, request, pk=None):
        perm = Permission.objects.get(codename="change_user")
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=perm,
            folder=Folder.get_root_folder(),
        ):
            return Response(
                {"error": "userDoesNotHavePermissionToChangeUserPreferences"},
                status=403,
            )
        general = GlobalSettings.objects.filter(
            name=GlobalSettings.Names.GENERAL
        ).first()
        lang = (
            general.value.get("default_language")
            if general and isinstance(general.value, dict)
            else None
        )
        if not lang or lang not in dict(settings.LANGUAGES):
            return Response(
                {"error": "noDefaultLanguageConfigured"},
                status=400,
            )
        with transaction.atomic():
            users = User.objects.select_for_update().all()
            updated = 0
            for user in users:
                if not isinstance(user.preferences, dict):
                    user.preferences = {}
                user.preferences["lang"] = lang
                user.save(update_fields=["preferences"])
                updated += 1
        return Response({"updated": updated, "language": lang})

    @action(detail=True, methods=["post"], name="Force date format for all users")
    def force_date_format(self, request, pk=None):
        perm = Permission.objects.get(codename="change_user")
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=perm,
            folder=Folder.get_root_folder(),
        ):
            return Response(
                {"error": "userDoesNotHavePermissionToChangeUserPreferences"},
                status=403,
            )
        general = GlobalSettings.objects.filter(
            name=GlobalSettings.Names.GENERAL
        ).first()
        date_format = (
            general.value.get("default_date_format")
            if general and isinstance(general.value, dict)
            else None
        )
        if not isinstance(date_format, str) or date_format not in User.DATE_FORMATS:
            return Response(
                {"error": "noDefaultDateFormatConfigured"},
                status=400,
            )
        with transaction.atomic():
            users = User.objects.select_for_update().all()
            updated = 0
            for user in users:
                if not isinstance(user.preferences, dict):
                    user.preferences = {}
                user.preferences["date_format"] = date_format
                user.save(update_fields=["preferences"])
                updated += 1
        return Response({"updated": updated, "date_format": date_format})

    @action(detail=True, name="Get security objective scales")
    def security_objective_scale(self, request):
        choices = {
            "1-3": "1-3",
            "1-4": "1-4",
            "1-5": "1-5",
            "0-3": "0-3",
            "0-4": "0-4",
            "FIPS-199": "FIPS-199",
        }
        return Response(choices)

    @action(detail=True, name="Get ebios rm radar parameters")
    def ebios_radar_parameters(self, request):
        try:
            instance = self.get_object()
        except PermissionDenied:
            # We want users to be able to see `GENERAL` global settings, even when they don't have the "view_globalsettings" permission.
            instance = GeneralSettingsViewSet.queryset.first()

        ebios_rm_parameters = {
            "ebios_radar_max": instance.value.get("ebios_radar_max"),
            "ebios_radar_green_zone_radius": instance.value.get(
                "ebios_radar_green_zone_radius"
            ),
            "ebios_radar_yellow_zone_radius": instance.value.get(
                "ebios_radar_yellow_zone_radius"
            ),
            "ebios_radar_red_zone_radius": instance.value.get(
                "ebios_radar_red_zone_radius"
            ),
        }
        return Response(ebios_rm_parameters)

    @action(detail=True, name="Get notifications settings")
    def notifications_settings(self, request):
        try:
            instance = self.get_object()
        except PermissionDenied:
            # We want users to be able to see `GENERAL` global settings, even when they don't have the "view_globalsettings" permission.
            instance = GeneralSettingsViewSet.queryset.first()

        notifications_settings = {
            "notifications_enable_mailing": instance.value.get(
                "notifications_enable_mailing"
            ),
        }
        return Response(notifications_settings)

    @action(detail=True, name="Get interface settings")
    def interface_settings(self, request):
        try:
            instance = self.get_object()
        except PermissionDenied:
            # We want users to be able to see `GENERAL` global settings, even when they don't have the "view_globalsettings" permission.
            instance = GeneralSettingsViewSet.queryset.first()

        interface_settings = {
            "interface_agg_scenario_matrix": instance.value.get(
                "interface_agg_scenario_matrix"
            ),
        }
        return Response(interface_settings)


class VulnerabilitySlaViewSet(viewsets.ModelViewSet):
    model = GlobalSettings
    serializer_class = VulnerabilitySlaSerializer
    queryset = GlobalSettings.objects.filter(
        name=GlobalSettings.Names.VULNERABILITY_SLA
    )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_object(self):
        obj, _ = self.model.objects.get_or_create(
            name=GlobalSettings.Names.VULNERABILITY_SLA
        )
        self.check_object_permissions(self.request, obj)
        return obj


class SecIntelFeedsViewSet(viewsets.ModelViewSet):
    model = GlobalSettings
    serializer_class = SecIntelFeedsSerializer
    queryset = GlobalSettings.objects.filter(name=GlobalSettings.Names.SEC_INTEL_FEEDS)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_object(self):
        obj, _ = self.model.objects.get_or_create(
            name=GlobalSettings.Names.SEC_INTEL_FEEDS
        )
        self.check_object_permissions(self.request, obj)
        return obj


class InfraConfigViewSet(viewsets.ModelViewSet):
    """Singleton GET/PUT for infrastructure configuration settings (stored as a
    JSON object). Restricted to administrators."""

    model = GlobalSettings
    serializer_class = InfraConfigSerializer
    queryset = GlobalSettings.objects.filter(name=GlobalSettings.Names.INFRA_CONFIG)
    permission_classes = [IsAuthenticated, IsGlobalAdmin]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        # "partial" is `True` for `PATCH` requests (or `False` otherwise).
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_object(self):
        obj, _ = self.model.objects.get_or_create(
            name=GlobalSettings.Names.INFRA_CONFIG
        )
        self.check_object_permissions(self.request, obj)
        return obj


@require_GET
def infra_config_view(request):
    """Unauthenticated endpoint exposing infrastructure configuration settings
    for the infrastructure layer to consume.

    Mirrors the /metrics endpoint contract: it must never be reachable from
    the public internet — keep it behind the reverse proxy / restricted to
    trusted networks. Only registered when ENABLE_INFRA_CONFIG_MANAGEMENT is set.
    """
    obj = GlobalSettings.objects.filter(name=GlobalSettings.Names.INFRA_CONFIG).first()
    if obj is None:
        raise Http404

    data = dict(InfraConfigSerializer(obj).data)

    # The stored JSON isn't schema-checked (admin/migration/import can write anything).
    for key in ("allowed_ips", "not_rate_limited_ips", "proxy_ips"):
        if not isinstance(data.get(key), list):
            data[key] = []

    return JsonResponse(data)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def get_sso_info(request):
    """
    API endpoint that returns the CSRF token.
    """
    sso_settings = SSOSettings.objects.get()
    sp_settings = (sso_settings.settings or {}).get("sp") or {}
    sp_entity_id = (
        sp_settings.get("entity_id")
        or sso_settings.provider_id
        or sso_settings.provider
    )
    callback_url = settings.CISO_ASSISTANT_URL + "/"
    return Response(
        {
            "is_enabled": sso_settings.is_enabled,
            "sp_entity_id": sp_entity_id,
            "callback_url": callback_url,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def get_default_language(request):
    """
    Returns the configured default language. Falls back to English if unset or invalid.
    """
    general = GlobalSettings.objects.filter(name="general").first()
    default_language = "en"
    if general and isinstance(general.value, dict):
        default_language = general.value.get("default_language", default_language)

    if default_language not in dict(settings.LANGUAGES):
        default_language = "en"

    return Response({"default_language": default_language})


class MailerSettingsViewSet(viewsets.ViewSet):
    """GET/PUT of the custom mailer configuration, a test send of unsaved
    values, and delivery health. Only registered when ENABLE_CUSTOM_MAILER is
    set, so the switch is enforced by the absence of the route."""

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _require(request, codename: str) -> None:
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename=codename),
            folder=Folder.get_root_folder(),
        ):
            raise PermissionDenied()

    def retrieve(self, request, *args, **kwargs):
        from .serializers import MailerConfigurationSerializer

        self._require(request, "view_mailerconfiguration")
        return Response(MailerConfigurationSerializer(MailerConfiguration.get()).data)

    def update(self, request, *args, **kwargs):
        from .serializers import MailerConfigurationSerializer

        self._require(request, "change_mailerconfiguration")
        configuration = MailerConfiguration.get()
        # Captured before the change: the notification goes through the
        # mailers the change replaces, which the new ones cannot suppress.
        previous_mailers = mail_service.active_mailers()
        previous_sender = mail_service.sender_address()
        serializer = MailerConfigurationSerializer(configuration, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        _notify_administrators_of_mailer_change(
            request.user, configuration, previous_mailers, previous_sender
        )
        return Response(MailerConfigurationSerializer(configuration).data)

    partial_update = update

    @action(detail=True, methods=["post"])
    def test(self, request, *args, **kwargs):
        """Send one test message through each mailer in the form, to the
        requesting administrator. The save token is issued only when every
        mailer delivered. Health is recorded when the tested values are the
        saved ones, so testing the live configuration refreshes the table."""
        from .mailer_settings import (
            configuration_digest,
            issue_test_token,
            specs_from_rows,
        )
        from .serializers import MailerConfigurationSerializer

        self._require(request, "change_mailerconfiguration")
        configuration = MailerConfiguration.get()
        try:
            stored_digest = configuration_digest(
                configuration.from_email, specs_from_rows(configuration.mailers.all())
            )
        except ValueError:
            stored_digest = None
        serializer = MailerConfigurationSerializer(configuration, data=request.data)
        serializer.is_valid(raise_exception=True)
        rows = serializer.build_rows(
            configuration, serializer.validated_data["mailers"]
        )
        from_email = (
            serializer.validated_data.get("from_email") or configuration.from_email
        )
        specs = specs_from_rows(rows)
        digest = configuration_digest(from_email, specs)
        results = [
            mail_service.send_test(
                request.user.email,
                mailers=[spec],
                from_email=from_email,
                record_health=digest == stored_digest,
            )
            for spec in specs
        ]
        payload = {
            "ok": all(result.ok for result in results),
            "recipient": request.user.email,
            "results": [
                {
                    "mailer": spec.alias,
                    "ok": result.ok,
                    "backend": result.backend,
                    # A single mailer was tried, so the skip reason is the error.
                    "error": result.skipped[0][1] if result.skipped else result.error,
                }
                for spec, result in zip(specs, results)
            ],
        }
        if payload["ok"]:
            payload["test_token"] = issue_test_token(digest)
        return Response(payload)

    @action(detail=True, methods=["get"])
    def health(self, request, *args, **kwargs):
        """One row per active mailer, attempted or not, plus rows of mailers
        that are no longer configured but were attempted."""
        from .serializers import MailerHealthSerializer

        self._require(request, "view_mailerconfiguration")
        rows = {
            row.alias: MailerHealthSerializer(row).data
            for row in MailerHealth.objects.all()
        }
        listed = []
        for spec in mail_service.active_mailers():
            listed.append(
                rows.pop(spec.alias, None)
                or {
                    "alias": spec.alias,
                    "source": spec.source,
                    "last_attempt_at": None,
                    "last_outcome": None,
                    "last_error": "",
                    "via_failover": False,
                    "last_success_at": None,
                }
            )
        listed.extend(rows.values())
        return Response(listed)


def _notify_administrators_of_mailer_change(
    actor, configuration, previous_mailers, previous_sender
):
    """Email the other administrators through the mailers that were active
    before the change. Best effort: the change is already saved."""
    recipients = list(
        User.objects.filter(user_groups__name="BI-UG-ADM", is_active=True)
        .exclude(pk=actor.pk)
        .values_list("email", flat=True)
        .distinct()
    )
    if not recipients or not previous_mailers or not previous_sender:
        return
    mailers = (
        ", ".join(
            f"{row.alias}: {row.transport} {row.host}"
            for row in configuration.mailers.all()
        )
        or "none"
    )
    state = (
        "active" if configuration.is_active else "parked (environment mailers apply)"
    )
    body = (
        f"{actor.email} changed the outgoing mail configuration of "
        f"{settings.CISO_ASSISTANT_URL} on {timezone.now():%Y-%m-%d %H:%M %Z}.\n"
        f"Sender address: {configuration.from_email or '(unset)'}\n"
        f"Mailers: {mailers}\n"
        f"State: {state}\n\n"
        "Password reset links and invitations now go through these mailers. "
        "If you did not expect this change, review it in Settings > Mailer."
    )
    try:
        mail_service.send(
            "CISO Assistant: outgoing mail configuration changed",
            body,
            recipients,
            from_email=previous_sender,
            mailers=previous_mailers,
        )
    except Exception as error:
        logger.error(
            "mailer change notification not sent",
            actor=actor.email,
            recipients=len(recipients),
            error=str(error),
        )
