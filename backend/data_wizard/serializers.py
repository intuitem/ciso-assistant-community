from rest_framework import serializers


class LoadFileSerializer(serializers.Serializer):
    file = serializers.FileField(
        allow_empty_file=False,
        max_length=None,
        required=True,
        help_text="Excel file to be processed (.xlsx, .xls)",
    )

    def validate_file(self, value):
        # Check if file extension is valid
        file_extension = value.name.split(".")[-1].lower()
        if file_extension not in ["xlsx", "xls"]:
            raise serializers.ValidationError(
                "Unsupported file format. Please upload an Excel file (.xlsx, .xls)."
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
