from rest_framework import serializers
from core.models import Library

from core.serializers import (
    BaseModelSerializer,
    FrameworkReadSerializer,
    RiskMatrixReadSerializer,
    SecurityFunctionReadSerializer,
    ThreatReadSerializer,
)


class LibraryObjectSerializer(serializers.Serializer):
    framework = FrameworkReadSerializer()
    risk_matrix = RiskMatrixReadSerializer()
    threats = ThreatReadSerializer(many=True)
    security_functions = SecurityFunctionReadSerializer(many=True)


class LibrarySerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    locale = serializers.ChoiceField(choices=["en", "fr"])
    objects = LibraryObjectSerializer(many=True)
    format_version = serializers.CharField()
    copyright = serializers.CharField()


class LibraryModelSerializer(BaseModelSerializer):
    class Meta:
        model = Library
        fields = "__all__"


class LibraryUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    class Meta:
        fields = ["file"]
