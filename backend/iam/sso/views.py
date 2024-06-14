from rest_framework.response import Response
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .models import SSOSettings
from rest_framework.decorators import action
from allauth.socialaccount import providers


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "iam.sso.serializers"


class SSOSettingsViewSet(BaseModelViewSet):
    model = SSOSettings

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        _providers = providers.registry.as_choices()
        return Response({p[0]: p[1] for p in _providers})
