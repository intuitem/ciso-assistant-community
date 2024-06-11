from .models import IdentityProvider

from core.serializers import BaseModelSerializer


class IdentityProviderReadSerializer(BaseModelSerializer):
    class Meta:
        model = IdentityProvider
        fields = "__all__"


class IdentityProviderWriteSerializer(BaseModelSerializer):
    class Meta:
        model = IdentityProvider
        fields = "__all__"
