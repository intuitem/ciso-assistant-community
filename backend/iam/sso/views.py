from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .models import IdentityProvider


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "iam.sso.serializers"


class IdentityProviderViewSet(BaseModelViewSet):
    model = IdentityProvider
