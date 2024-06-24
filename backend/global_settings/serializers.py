from rest_framework import serializers

from .models import GlobalSettings


class GlobalSettingsSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        raise serializers.ValidationError(
            "Global settings can only be created through data migrations."
        )

    def delete(self, instance):
        raise serializers.ValidationError(
            "Global settings can only be deleted through data migrations."
        )

    def update(self, instance, validated_data):
        validated_data.pop("name")
        return super().update(instance, validated_data)

    class Meta:
        model = GlobalSettings
        fields = "__all__"
