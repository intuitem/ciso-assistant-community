from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from ciso_assistant.settings import CISO_ASSISTANT_URL
from rest_framework.decorators import action

from iam.sso.models import SSOSettings

from .serializers import GlobalSettingsSerializer, GeneralSettingsSerializer

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


class GeneralSettingsViewSet(viewsets.ModelViewSet):
    model = GlobalSettings
    serializer_class = GeneralSettingsSerializer
    queryset = GlobalSettings.objects.filter(name="general")

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
        obj = self.model.objects.get(name="general")
        obj.is_published = True  # we could do that at creation, but it's ok here
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, name="Get write data")
    def object(self, request, pk=None):
        default_settings = {
            "security_objective_scale": "1-4",
            "ebios_radar_max": 6,
            "ebios_radar_green_zone_radius": 0.2,
            "ebios_radar_yellow_zone_radius": 0.9,
            "ebios_radar_red_zone_radius": 2.5,
        }

        settings, created = GlobalSettings.objects.get_or_create(name="general")

        if created or not all(key in settings.value for key in default_settings):
            existing_value = settings.value or {}
            updated_value = {**default_settings, **existing_value}
            settings.value = updated_value
            settings.save()

        return Response(GeneralSettingsSerializer(settings).data.get("value"))

    @action(detail=True, name="Get security objective scales")
    def security_objective_scale(self, request):
        choices = {
            "1-4": "1-4",
            "0-3": "0-3",
            "FIPS-199": "FIPS-199",
        }
        return Response(choices)

    @action(detail=True, name="Get ebios rm radar parameters")
    def ebios_radar_parameters(self, request):
        ebios_rm_parameters = {
            "ebios_radar_max": self.get_object().value.get("ebios_radar_max"),
            "ebios_radar_green_zone_radius": self.get_object().value.get(
                "ebios_radar_green_zone_radius"
            ),
            "ebios_radar_yellow_zone_radius": self.get_object().value.get(
                "ebios_radar_yellow_zone_radius"
            ),
            "ebios_radar_red_zone_radius": self.get_object().value.get(
                "ebios_radar_red_zone_radius"
            ),
        }
        return Response(ebios_rm_parameters)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def get_sso_info(request):
    """
    API endpoint that returns the CSRF token.
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
