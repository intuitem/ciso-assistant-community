from rest_framework import serializers


class LibraryObjectSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=[
            "risk_matrix",
            "reference_control",
            "threat",
            "framework",
        ]
    )
    fields = serializers.DictField(child=serializers.CharField())


class LibrarySerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()
    locale = serializers.ChoiceField(choices=["en", "fr"])
    objects = LibraryObjectSerializer(many=True)
    format_version = serializers.CharField()
    copyright = serializers.CharField()


class LibraryUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    class Meta:
        fields = ["file"]
