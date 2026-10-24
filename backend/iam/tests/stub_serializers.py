"""Overriding write serializer for the MODULE_PATHS seam tests, shaped like the
enterprise build's (enterprise_core.serializers.ServiceAccountWriteSerializer).

It rejects creating an account named "rejected", and reactivating an inactive
account: enough to show the override runs on create, and sees activation changes
on update with the instance in context."""

from rest_framework import serializers

from iam.serializers import (
    ServiceAccountWriteSerializer as CommunityServiceAccountWriteSerializer,
)


class ServiceAccountWriteSerializer(CommunityServiceAccountWriteSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.context.get("instance")
        if instance is None and attrs.get("name") == "rejected":
            raise serializers.ValidationError({"error": "rejectedByOverride"})
        if (
            instance is not None
            and attrs.get("is_active") is True
            and not instance.is_active
        ):
            raise serializers.ValidationError(
                {"error": "reactivationRejectedByOverride"}
            )
        return attrs
