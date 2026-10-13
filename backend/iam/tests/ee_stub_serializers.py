"""EE-shaped stub for the MODULE_PATHS write-serializer seam tests.

Mirrors enterprise_core.serializers.ServiceAccountWriteSerializer — keep the
validate() logic in sync so the CE tests exercise what the enterprise build
actually ships (the enterprise backend has no test infrastructure yet).
"""

from django.conf import settings
from rest_framework import serializers

from iam.models import ServiceAccount
from iam.serializers import (
    ServiceAccountWriteSerializer as CommunityServiceAccountWriteSerializer,
)


class ServiceAccountWriteSerializer(CommunityServiceAccountWriteSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.context.get("instance")
        if instance is None:
            becoming_active = True
        else:
            becoming_active = attrs.get("is_active") is True and not instance.is_active
        if becoming_active:
            active_accounts = ServiceAccount.objects.filter(is_active=True)
            if instance is not None:
                active_accounts = active_accounts.exclude(pk=instance.pk)
            if active_accounts.count() >= settings.LICENSE_SEATS:
                raise serializers.ValidationError(
                    {"error": "errorServiceAccountSeatsExceeded"}
                )
        return attrs
