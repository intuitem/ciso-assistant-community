from rest_framework.response import Response
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .models import SSOSettings
from .serializers import SSOSettingsReadSerializer
from rest_framework.decorators import action
from allauth.socialaccount import providers


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "iam.sso.serializers"


class SSOSettingsViewSet(BaseModelViewSet):
    model = SSOSettings

    def retrieve(self, request, *args, **kwargs):
        instance = self.model.objects.get()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.model.objects.get()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        _providers = providers.registry.as_choices()
        return Response({p[0]: p[1] for p in _providers})
