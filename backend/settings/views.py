from rest_framework import viewsets
from rest_framework.response import Response

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
