from typing import Optional

from rest_framework import serializers

from core.models import LibraryDraft, LoadedLibrary, StoredLibrary
from core.serializer_fields import FieldsRelatedField, HashSlugRelatedField
from core.serializers import BaseModelSerializer, ReferentialSerializer
from library import builder


class StoredLibrarySerializer(ReferentialSerializer):
    locales = serializers.ListField(source="get_locales", read_only=True)
    loaded_library = serializers.SerializerMethodField()
    filtering_labels = FieldsRelatedField(many=True, fields=["id", "label"])
    is_preset = serializers.BooleanField(read_only=True)
    profile = serializers.SerializerMethodField()
    scaffolded_objects = serializers.SerializerMethodField()

    def get_loaded_library(self, obj) -> Optional[str]:
        loaded_library = obj.get_loaded_library()
        return str(loaded_library.id) if loaded_library else None

    def get_profile(self, obj) -> Optional[dict]:
        if obj.is_preset:
            return obj.content.get("preset", {}).get("profile")
        return None

    def get_scaffolded_objects(self, obj) -> Optional[list]:
        if not obj.is_preset:
            return None
        items = obj.content.get("preset", {}).get("scaffolded_objects", [])
        if not items:
            return None
        from collections import Counter

        counts = Counter(item["type"] for item in items)
        return [
            {"type": obj_type, "count": count} for obj_type, count in counts.items()
        ]

    class Meta:
        model = StoredLibrary
        fields = [
            "id",
            "name",
            "description",
            "urn",
            "ref_id",
            "locale",
            "version",
            "packager",
            "provider",
            "filtering_labels",
            "publication_date",
            "builtin",
            "objects_meta",
            "reference_count",
            "is_loaded",
            "is_update",
            "locales",
            "loaded_library",
            "copyright",
            "is_preset",
            "profile",
            "scaffolded_objects",
        ]


class StoredLibraryDetailedSerializer(ReferentialSerializer):
    locales = serializers.ListField(source="get_locales", read_only=True)

    class Meta:
        model = StoredLibrary
        exclude = ["translations"]


class LoadedLibraryImportExportSerializer(BaseModelSerializer):
    folder = HashSlugRelatedField(slug_field="pk", read_only=True)
    dependencies = HashSlugRelatedField(slug_field="pk", read_only=True, many=True)

    class Meta:
        model = LoadedLibrary
        fields = [
            "created_at",
            "updated_at",
            "version",
            "folder",
            "urn",
            "ref_id",
            "provider",
            "name",
            "description",
            "annotation",
            "locale",
            "packager",
            "publication_date",
            "builtin",
            "objects_meta",
            "translations",
            "dependencies",
            "copyright",
        ]


class LoadedLibraryDetailedSerializer(ReferentialSerializer):
    locales = serializers.ListField(source="get_locales", read_only=True)
    dependencies = FieldsRelatedField(many=True, fields=["id", "urn", "str", "name"])

    class Meta:
        model = LoadedLibrary
        exclude = ["translations"]


class LoadedLibrarySerializer(ReferentialSerializer):
    locales = serializers.ListField(source="get_locales", read_only=True)

    class Meta:
        model = LoadedLibrary
        fields = [
            "id",
            "name",
            "description",
            "urn",
            "ref_id",
            "locale",
            "version",
            "packager",
            "provider",
            "publication_date",
            "builtin",
            "objects_meta",
            "reference_count",
            "locales",
            "has_update",
        ]


class LibraryUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)

    class Meta:
        fields = ["file"]


class LibraryDraftReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    urn = serializers.CharField(source="effective_urn", read_only=True)
    identity_locked = serializers.BooleanField(read_only=True)
    has_unpublished_changes = serializers.BooleanField(read_only=True)
    objects_meta = serializers.SerializerMethodField()

    def get_objects_meta(self, obj) -> dict:
        objects = builder.normalize_objects(obj.content or {})
        meta = {
            field: len(value)
            for field, value in objects.items()
            if isinstance(value, list)
        }
        if "preset" in objects:
            meta["preset"] = 1
        return meta

    class Meta:
        model = LibraryDraft
        fields = [
            "id",
            "name",
            "description",
            "folder",
            "urn",
            "packager",
            "ref_id",
            "locale",
            "version",
            "provider",
            "copyright",
            "publication_date",
            "annotation",
            "translations",
            "dependencies",
            "labels",
            "content",
            "objects_meta",
            "identity_locked",
            "has_unpublished_changes",
            "first_published_at",
            "last_published_at",
            "last_published_version",
            "created_at",
            "updated_at",
        ]


class LibraryDraftWriteSerializer(BaseModelSerializer):
    class Meta:
        model = LibraryDraft
        # urn and the published-* snapshot are lifecycle fields, only ever set
        # by the adopt/publish actions; is_published is the IAM visibility flag
        # (unrelated to library publication) and is never client-writable.
        exclude = [
            "created_at",
            "updated_at",
            "is_published",
            "urn",
            "first_published_at",
            "last_published_at",
            "last_published_version",
            "last_published_hash",
        ]

    def validate_content(self, content):
        if not isinstance(content, dict):
            raise serializers.ValidationError("contentMustBeAnObject")
        normalized = builder.normalize_objects(content)
        # Shape boundary: stored draft content is always well-formed, so
        # everything reading it can assume structure. Completeness (names,
        # references, …) stays a validate/publish concern.
        if errors := builder.check_document_shape(normalized):
            raise serializers.ValidationError(errors)
        return normalized

    def validate_dependencies(self, dependencies):
        if not isinstance(dependencies, list) or not all(
            isinstance(dep, str) for dep in dependencies
        ):
            raise serializers.ValidationError("dependenciesMustBeAListOfUrns")
        return dependencies

    def validate(self, data):
        data = super().validate(data)
        if self.instance is not None and self.instance.identity_locked:
            for field in ("packager", "ref_id"):
                if field in data and data[field] != getattr(self.instance, field):
                    raise serializers.ValidationError(
                        {field: "identityFrozenAfterPublication"}
                    )
        return data

    def create(self, validated_data):
        # Authored libraries: the packager is the provider unless stated
        # otherwise. Plain editable metadata, not a domain rule — adopted
        # libraries keep their source's provider (adopt bypasses this).
        if not validated_data.get("provider"):
            validated_data["provider"] = validated_data.get("packager")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._check_object_perm(instance, "change")
        # Deliberately not calling BaseModelSerializer.update: its urn-based
        # immutability guard targets imported live objects, whereas a draft's
        # urn records an adopted identity and the draft stays editable.
        new_packager = validated_data.get("packager", instance.packager)
        new_ref_id = validated_data.get("ref_id", instance.ref_id)
        if (new_packager, new_ref_id) != (instance.packager, instance.ref_id):
            # Renaming a draft regenerates its URN family across the document.
            content = validated_data.get("content", instance.content)
            validated_data["content"] = builder.rebase_document(
                content, new_packager, new_ref_id
            )
        return serializers.ModelSerializer.update(self, instance, validated_data)
