from rest_framework import serializers

from .models import GlobalSettings

GENERAL_SETTINGS_KEYS = [
    "security_objective_scale",
]


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


class GeneralSettingsSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        for key, value in validated_data["value"].items():
            if key not in GENERAL_SETTINGS_KEYS:
                raise serializers.ValidationError(f"Invalid key: {key}")
            setattr(instance, "value", validated_data["value"])
        instance.save()
        return instance

    class Meta:
        model = GlobalSettings
        exclude = ["is_published", "folder"]
        read_only_fields = ["name"]
