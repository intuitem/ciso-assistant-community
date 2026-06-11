from allauth.headless.base.views import APIView
from allauth.headless.socialaccount.forms import RedirectToProviderForm
from allauth.socialaccount import providers
from allauth.socialaccount.providers.saml.views import render_authentication_error
from django.core.exceptions import ValidationError
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from structlog import get_logger

from global_settings.models import GlobalSettings

from .models import SSOSettings
from iam.models import User
from .oidc.views import oidc_redirect
from .serializers import GroupSyncConfigSerializer, SSOSettingsWriteSerializer

GROUP_SYNC_DEFAULTS = {
    "enabled": False,
    "authoritative": False,
    "oidc_groups_claim": "groups",
    "saml_groups_attribute": "groups",
}

logger = get_logger(__name__)


class RedirectToProviderView(APIView):
    handle_json_input = False

    def post(self, request, *args, **kwargs):
        form = RedirectToProviderForm(request.POST)
        if not form.is_valid():
            return render_authentication_error(
                request,
                provider=request.POST.get("provider"),
                exception=ValidationError(form.errors),
            )
        provider = form.cleaned_data["provider"]
        next_url = form.cleaned_data["callback_url"]
        process = form.cleaned_data["process"]
        try:
            # OIDC uses our custom redirect to send a long, standard-compliant
            # state + nonce. Other providers (SAML, ...) use allauth's default.
            if provider.id == "openid_connect":
                return oidc_redirect(
                    request,
                    provider,
                    process=process,
                    next_url=next_url,
                    headless=True,
                )
            return provider.redirect(
                request,
                process,
                next_url=next_url,
                headless=True,
            )
        except Exception as e:
            logger.error("SSO redirection failed", provider=provider.id, exc_info=e)
            return render_authentication_error(request, provider, error="failedSSO")


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "iam.sso.serializers"


class SSOSettingsViewSet(BaseModelViewSet):
    model = SSOSettings

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        is_enabled = serializer.validated_data.get("is_enabled", False)
        force_sso = serializer.validated_data.get("force_sso", False)

        if is_enabled and force_sso:
            for user in User.objects.all():
                if not user.keep_local_login:
                    user.set_unusable_password()

        return Response(serializer.data)

    @action(detail=True, name="Get provider choices")
    def provider(self, request):
        _providers = providers.registry.as_choices()
        return Response({p[0]: p[1] for p in _providers})

    def get_object(self):
        obj = self.model.objects.get()
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, name="Get write data")
    def object(self, request, pk=None):
        return Response(SSOSettingsWriteSerializer(self.get_object()).data)

    @action(detail=True, methods=["get", "patch"], name="Group sync configuration")
    def group_sync(self, request, pk=None):
        """
        GET   — return the current IdP group synchronization policy.
        PATCH — merge the provided keys into settings.group_sync, leaving the
                rest of the SSO configuration untouched.
        """
        settings_object = GlobalSettings.objects.get(name=GlobalSettings.Names.SSO)
        value = settings_object.value or {}
        inner = value.get("settings", {})
        current = {**GROUP_SYNC_DEFAULTS, **inner.get("group_sync", {})}

        if request.method == "GET":
            return Response(current)

        serializer = GroupSyncConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        current.update(serializer.validated_data)

        inner["group_sync"] = current
        value["settings"] = inner
        settings_object.value = value
        settings_object.save()

        logger.info("idp group_sync config updated", config=current)
        return Response(current)
