from rest_framework import serializers
import re


class LoadBackupSerializer(serializers.Serializer):
    file = serializers.Field

    class Meta:
        fields = ("file",)


class MetaSerializer(serializers.Serializer):
    media_version = serializers.CharField()
    exported_at = serializers.CharField()


class ObjectSerializer(serializers.Serializer):
    model = serializers.CharField()
    id = serializers.CharField()
    fields = serializers.DictField(
        child=serializers.JSONField(),  # Accept any JSON-serializable value
        allow_empty=True,
    )

    def validate_fields(self, value):
        # Validate that all field names match the pattern ^[a-z_]+$
        pattern = re.compile(r"^[a-z_]+$")

        for field_name in value.keys():
            if not pattern.match(field_name):
                raise serializers.ValidationError(
                    f"Field name '{field_name}' must contain only lowercase letters and underscores"
                )
        return value


class ExportSerializer(serializers.Serializer):
    meta = MetaSerializer()
    objects = ObjectSerializer(many=True)
