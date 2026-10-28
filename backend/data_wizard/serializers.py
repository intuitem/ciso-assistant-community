from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from core.serializers import BaseModelSerializer, FieldsRelatedField

from .models import ImportMapping


class LoadFileSerializer(serializers.Serializer):
    ALLOWED_FILE_EXTENSIONS = ["xlsx", "xls", "csv", "xml"]
    file = serializers.FileField(
        allow_empty_file=False,
        max_length=None,
        required=True,
        help_text=f"File to be processed ({', '.join(f'.{ext}' for ext in ALLOWED_FILE_EXTENSIONS)})",
    )

    def validate_file(self, value: UploadedFile):
        # Check if file extension is valid
        file_extension = value.name.split(".")[-1].lower()
        if file_extension not in self.ALLOWED_FILE_EXTENSIONS:
            raise serializers.ValidationError(
                f"Invalid file extension {repr(file_extension)}, valid file extensions are: {repr(self.ALLOWED_FILE_EXTENSIONS)}."
            )

        # Check file size (optional) - for example, limit to 10MB
        if value.size > 10 * 1024 * 1024:  # 10MB in bytes
            raise serializers.ValidationError(
                "File size exceeds the maximum limit (10MB)."
            )

        return value

    def create(self, validated_data):
        # If you need to save the uploaded file record to a model
        # This would be implemented here
        # For example:
        # upload = FileUpload.objects.create(
        #     file=validated_data['file'],
        #     uploaded_by=self.context['request'].user
        # )
        # return upload
        pass

    def update(self, instance, validated_data):
        # If you need to update an existing file record
        # This would be implemented here
        pass


class ImportMappingReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    created_by = FieldsRelatedField(["id", "email"])

    class Meta:
        model = ImportMapping
        fields = "__all__"


class ImportMappingWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ImportMapping
        exclude = ["created_by", "use_count", "last_used_at"]
        extra_kwargs = {"sheets": {"required": True}}

    def validate_sheets(self, sheets):
        from .mapping import error_code, validate_saved_sheets

        try:
            validate_saved_sheets(sheets)
        except (ValueError, TypeError, KeyError) as e:
            raise serializers.ValidationError(error_code(e) or "InvalidSheets") from e
        return sheets

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
