from rest_framework import serializers

from core.serializers import (
    BaseModelSerializer,
    ReferentialSerializer,
    FieldsRelatedField,
    PathField,
)
from core.serializer_fields import HashSlugRelatedField
from core.serializers import REFERENTIAL_IMPORT_EXPORT_FIELDS
from .models import SecurityAdvisory, CWE, TTPCatalog, Tactic, Technique


class SecurityAdvisoryWriteSerializer(BaseModelSerializer):
    class Meta:
        model = SecurityAdvisory
        exclude = ["translations"]


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


class TTPCatalogWriteSerializer(BaseModelSerializer):
    class Meta:
        model = TTPCatalog
        exclude = ["translations"]


class TTPCatalogReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])

    class Meta:
        model = TTPCatalog
        exclude = ["translations"]


class TTPCatalogImportExportSerializer(BaseModelSerializer):
    library = serializers.SlugRelatedField(slug_field="urn", read_only=True)
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)

    class Meta:
        model = TTPCatalog
        fields = REFERENTIAL_IMPORT_EXPORT_FIELDS + ["grouping_definition"]


class TacticWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Tactic
        exclude = ["translations"]


class TacticReadSerializer(ReferentialSerializer):
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    catalog = FieldsRelatedField()

    class Meta:
        model = Tactic
        exclude = ["translations"]


class TacticImportExportSerializer(BaseModelSerializer):
    library = serializers.SlugRelatedField(slug_field="urn", read_only=True)
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    catalog = serializers.SlugRelatedField(slug_field="urn", read_only=True)

    class Meta:
        model = Tactic
        fields = REFERENTIAL_IMPORT_EXPORT_FIELDS + ["catalog", "order_id"]


class TechniqueWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Technique
        exclude = ["translations"]


class TechniqueReadSerializer(ReferentialSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    filtering_labels = FieldsRelatedField(["id", "folder"], many=True)
    catalog = FieldsRelatedField()
    parent = FieldsRelatedField()
    tactics = FieldsRelatedField(many=True)
    reference_controls = FieldsRelatedField(many=True)

    class Meta:
        model = Technique
        exclude = ["translations"]


class TechniqueImportExportSerializer(BaseModelSerializer):
    library = serializers.SlugRelatedField(slug_field="urn", read_only=True)
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    catalog = serializers.SlugRelatedField(slug_field="urn", read_only=True)
    parent = serializers.SlugRelatedField(slug_field="urn", read_only=True)
    tactics = serializers.SlugRelatedField(slug_field="urn", read_only=True, many=True)
    reference_controls = serializers.SlugRelatedField(
        slug_field="urn", read_only=True, many=True
    )

    class Meta:
        model = Technique
        # explicit list: a new field must be added here or serdes drops it
        fields = REFERENTIAL_IMPORT_EXPORT_FIELDS + [
            "catalog",
            "parent",
            "tactics",
            "order_id",
            "groups",
            "reference_controls",
            "is_deprecated",
        ]
