from rest_framework import serializers

from core.serializers import (
    BaseModelSerializer,
    ReferentialSerializer,
    FieldsRelatedField,
    PathField,
)
from .models import CVE, CWE


class CVEWriteSerializer(BaseModelSerializer):
    class Meta:
        model = CVE
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


class CVEReadSerializer(ReferentialSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    references = serializers.SerializerMethodField()

    def get_references(self, obj):
        if not obj.references:
            return []
        return [
            {"str": ref.get("url", ""), "source": ref.get("source", "")}
            for ref in obj.references
        ]

    class Meta:
        model = CVE
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
