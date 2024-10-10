from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from ciso_assistant.settings import CISO_ASSISTANT_URL

from core.views import BaseModelViewSet
from iam.sso.models import SSOSettings

from .serializers import GlobalSettingsSerializer

from .models import GlobalSettings


class GlobalSettingsViewSet(viewsets.ModelViewSet):
    queryset = GlobalSettings.objects.all()
    serializer_class = GlobalSettingsSerializer

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": "Global settings can only be created through data migrations."},
            status=405,
        )

    def delete(self, request, *args, **kwargs):
        return Response(
            {"detail": "Global settings can only be deleted through data migrations."},
            status=405,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Global settings can only be updated through data migrations."},
            status=405,
        )


UPDATABLE_GENERAL_SETTINGS = frozenset(
    ["lang"]
)  # This represents the list of "general" GlobalSettings an admin has the right to change.
PUBLIC_GENERAL_SETTINGS = [
    "lang"
]  # List of general settings accessible by anyone (non-sensitive general settings).


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def get_general_settings(request):
    """
    API endpoint to get the general settings.
    """
    general_settings = GlobalSettings.objects.filter(name="general").first()
    if general_settings is None:
        public_settings = {}
    else:
        public_settings = {
            key: general_settings.value.get(key) for key in PUBLIC_GENERAL_SETTINGS
        }
    return Response(public_settings)


@api_view(["PATCH"])
@permission_classes([permissions.IsAdminUser])
def update_general_settings(request):
    """
    API endpoint to update general settings as an administrator.
    """
    BaseModelViewSet._process_request_data(request)

    general_settings = GlobalSettings.objects.filter(name="general").first()
    if general_settings is not None:
        general_settings = general_settings.value
    else:
        general_settings = {}

    for key, value in request.data.items():
        # There is no schema verification for this
        # An attacker may be able to break a ciso-assistant instance by injecting values with bad types in future general settings.
        if key in UPDATABLE_GENERAL_SETTINGS:
            general_settings[key] = value

    GlobalSettings.objects.update_or_create(
        name="general", defaults={"value": general_settings}
    )

    return Response({})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def get_sso_info(request):
    """
    API endpoint that return the SSO configuration info
    """
    settings = SSOSettings.objects.get()
    sp_entity_id = settings.settings["sp"].get("entity_id")
    callback_url = CISO_ASSISTANT_URL + "/"
    return Response(
        {
            "is_enabled": settings.is_enabled,
            "sp_entity_id": sp_entity_id,
            "callback_url": callback_url,
        }
    )
