import re

from django.utils import timezone
from django.conf import settings
from django.db.models.query import QuerySet
from rest_framework import serializers

from .utils import app_dot_model


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

    @staticmethod
    def dump_data(scope: list[QuerySet]) -> dict:
        meta = {
            "media_version": settings.VERSION,
            "exported_at": timezone.now().isoformat(),
        }

        objects = []

        for queryset in scope:
            for obj in queryset:
                objects.append(
                    {
                        "model": app_dot_model(queryset.model),
                        "id": str(obj.id),
                        "fields": obj.__dict__,
                    }
                )

        return {"meta": meta, "objects": objects}
