import pytest
from datetime import datetime

from serdes.serializers import ExportSerializer


@pytest.fixture
def valid_export_data():
    return {
        "meta": {"media_version": "1.0.0", "exported_at": datetime.now().isoformat()},
        "objects": [
            {
                "model": "folder",
                "id": "1",
                "fields": {
                    "name": "R&D",
                    "type": "DO",
                    "created_at": "2025-01-12T10:00:00Z",
                    "updated_at": "2025-01-12T10:00:00Z",
                },
            },
            {
                "model": "project",
                "id": "2",
                "fields": {
                    "name": "ISMS",
                    "folder": "1",
                    "created_at": "2025-01-12T10:00:00Z",
                    "updated_at": "2025-01-12T10:00:00Z",
                },
            },
        ],
    }


class TestExportSerializer:
    def test_valid_data(self, valid_export_data):
        """Test serializer with valid data"""
        serializer = ExportSerializer(data=valid_export_data)
        assert serializer.is_valid()
        assert serializer.errors == {}

    def test_missing_required_fields(self):
        """Test serializer with missing required fields"""
        invalid_data = {
            "meta": {
                "media_version": "1.0.0"
                # missing exported_at
            },
            "objects": [],
        }
        serializer = ExportSerializer(data=invalid_data)
        assert not serializer.is_valid()
        assert "meta" in serializer.errors
        assert "exported_at" in serializer.errors["meta"]

    def test_invalid_field_name_pattern(self, valid_export_data):
        """Test serializer with invalid field names in objects"""
        # Modify the valid data to include an invalid field name
        valid_export_data["objects"][0]["fields"]["Invalid_Name"] = "test"

        serializer = ExportSerializer(data=valid_export_data)
        assert not serializer.is_valid()
        assert "objects" in serializer.errors
        assert "fields" in serializer.errors["objects"][0]

    def test_empty_objects_list(self):
        """Test serializer with empty objects list"""
        data = {
            "meta": {
                "media_version": "1.0.0",
                "exported_at": datetime.now().isoformat(),
            },
            "objects": [],
        }
        serializer = ExportSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.errors == {}

    def test_invalid_fields_data(self, valid_export_data):
        """Test serializer with invalid data types in fields"""
        # Try to pass bytes as a field value, which is not JSON serializable
        valid_export_data["objects"][0]["fields"]["bytes_field"] = bytes([1, 2, 3])

        serializer = ExportSerializer(data=valid_export_data)
        assert not serializer.is_valid()
        assert "objects" in serializer.errors
        assert "fields" in serializer.errors["objects"][0]

    def test_invalid_json_string_in_fields(self, valid_export_data):
        """Test serializer with malformed JSON string in fields"""
        valid_export_data["objects"][0]["fields"] = "{"  # Malformed JSON string

        serializer = ExportSerializer(data=valid_export_data)
        assert not serializer.is_valid()
        assert "objects" in serializer.errors
        assert "fields" in serializer.errors["objects"][0]

    def test_none_values(self):
        """Test serializer with None values"""
        data = {"meta": None, "objects": None}
        serializer = ExportSerializer(data=data)
        assert not serializer.is_valid()
        assert "meta" in serializer.errors
        assert "objects" in serializer.errors

    def test_extra_fields(self, valid_export_data):
        """Test serializer with extra unexpected fields"""
        valid_export_data["extra_field"] = "unexpected"
        serializer = ExportSerializer(data=valid_export_data)
        # DRF ignores extra fields by default
        assert serializer.is_valid()
        assert "extra_field" not in serializer.validated_data

    def test_nested_objects_validation(self):
        """Test serializer with deeply nested objects in fields"""
        data = {
            "meta": {
                "media_version": "1.0.0",
                "exported_at": datetime.now().isoformat(),
            },
            "objects": [
                {
                    "model": "complex",
                    "id": "789",
                    "fields": {
                        "nested_data": {
                            "level1": {"level2": {"value": "deeply nested"}}
                        },
                        "array_data": [1, 2, 3, {"key": "value"}],
                    },
                }
            ],
        }
        serializer = ExportSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.errors == {}
