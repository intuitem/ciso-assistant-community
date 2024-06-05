from rest_framework import serializers


class LoadBackupSerializer(serializers.Serializer):
    file = serializers.Field

    class Meta:
        fields = ("file",)
