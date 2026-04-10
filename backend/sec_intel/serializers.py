from rest_framework import serializers

from core.serializers import (
    BaseModelSerializer,
    ReferentialSerializer,
    FieldsRelatedField,
    PathField,
)
from .models import SecurityAdvisory, CWE


class SecurityAdvisoryWriteSerializer(BaseModelSerializer):
    class Meta:
        model = SecurityAdvisory
        exclude = ["translations"]

    def create(self, validated_data):
        instance = super().create(validated_data)
        if instance.ref_id and instance.ref_id.startswith("CVE-"):
            try:
                from sec_intel.feeds import NVDFeed

                NVDFeed.enrich_cve(instance)
            except Exception:
                import structlog

                structlog.get_logger(__name__).warning(
                    "NVD enrichment failed on create",
                    ref_id=instance.ref_id,
                    exc_info=True,
                )
        return instance


class SecurityAdvisoryReadSerializer(ReferentialSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    references = serializers.SerializerMethodField()
    aliases = serializers.SerializerMethodField()

    def get_references(self, obj):
        if not obj.references:
            return []
        return [
            {"str": ref.get("url", ""), "source": ref.get("source", "")}
            for ref in obj.references
        ]

    def get_aliases(self, obj):
        if not obj.aliases:
            return []
        return [
            {"str": f"{alias.get('source', '')}: {alias.get('id', '')}"}
            for alias in obj.aliases
        ]

    class Meta:
        model = SecurityAdvisory
        exclude = ["translations"]


class CWEWriteSerializer(BaseModelSerializer):
    class Meta:
        model = CWE
        exclude = ["translations"]


class CWEReadSerializer(ReferentialSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)

    class Meta:
        model = CWE
        exclude = ["translations"]
