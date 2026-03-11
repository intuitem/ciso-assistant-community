import pytest
import json
from rest_framework import serializers as drf_serializers
from django.test import TestCase

from crq.serializers import ImpactField, QuantitativeRiskStudyWriteSerializer


class TestImpactField:
    """Tests for ImpactField custom serializer field"""

    def setup_method(self):
        """Setup for each test method"""
        self.field = ImpactField()

    def test_to_representation(self):
        """Test serialization of impact data"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 1000,
            "ub": 10000
        }
        result = self.field.to_representation(data)
        assert result == data

    def test_to_internal_value_valid_dict(self):
        """Test deserialization with valid dictionary"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 1000,
            "ub": 10000
        }
        result = self.field.to_internal_value(data)
        assert result == data

    def test_to_internal_value_valid_json_string(self):
        """Test deserialization with valid JSON string"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 1000,
            "ub": 10000
        }
        json_string = json.dumps(data)
        result = self.field.to_internal_value(json_string)
        assert result == data

    def test_to_internal_value_null(self):
        """Test deserialization with null value"""
        result = self.field.to_internal_value(None)
        assert result is None

    def test_to_internal_value_empty_string(self):
        """Test deserialization with empty string"""
        result = self.field.to_internal_value("")
        assert result is None

    def test_to_internal_value_empty_dict(self):
        """Test deserialization with empty dictionary (all fields missing)"""
        data = {}
        result = self.field.to_internal_value(data)
        assert result is None

    def test_to_internal_value_invalid_json_string(self):
        """Test deserialization with invalid JSON string"""
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value("invalid json {")
        assert "must be valid JSON" in str(exc_info.value)

    def test_to_internal_value_not_dict(self):
        """Test deserialization with non-dictionary value"""
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value("not a dict")

        # After parsing, if it's still not a dict, should error
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(["list", "value"])
        assert "must be a dictionary" in str(exc_info.value)

    def test_to_internal_value_missing_distribution(self):
        """Test deserialization with missing distribution"""
        data = {
            "lb": 1000,
            "ub": 10000
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "requires 'distribution'" in str(exc_info.value)

    def test_to_internal_value_missing_lb(self):
        """Test deserialization with missing lower bound"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "ub": 10000
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "requires 'distribution'" in str(exc_info.value) or "'lb'" in str(exc_info.value)

    def test_to_internal_value_missing_ub(self):
        """Test deserialization with missing upper bound"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 1000
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "requires 'distribution'" in str(exc_info.value) or "'ub'" in str(exc_info.value)

    def test_to_internal_value_invalid_distribution(self):
        """Test deserialization with unsupported distribution type"""
        data = {
            "distribution": "NORMAL",
            "lb": 1000,
            "ub": 10000
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "LOGNORMAL-CI90" in str(exc_info.value)

    def test_to_internal_value_non_numeric_lb(self):
        """Test deserialization with non-numeric lower bound"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": "not a number",
            "ub": 10000
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "must be numeric" in str(exc_info.value)

    def test_to_internal_value_non_numeric_ub(self):
        """Test deserialization with non-numeric upper bound"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 1000,
            "ub": "not a number"
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "must be numeric" in str(exc_info.value)

    def test_to_internal_value_negative_lb(self):
        """Test deserialization with negative lower bound"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": -1000,
            "ub": 10000
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "must be positive" in str(exc_info.value)

    def test_to_internal_value_zero_lb(self):
        """Test deserialization with zero lower bound"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 0,
            "ub": 10000
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "must be positive" in str(exc_info.value)

    def test_to_internal_value_ub_less_than_lb(self):
        """Test deserialization when upper bound is less than lower bound"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 10000,
            "ub": 1000
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "must be greater than" in str(exc_info.value)

    def test_to_internal_value_ub_equal_to_lb(self):
        """Test deserialization when upper bound equals lower bound"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 5000,
            "ub": 5000
        }
        with pytest.raises(drf_serializers.ValidationError) as exc_info:
            self.field.to_internal_value(data)
        assert "must be greater than" in str(exc_info.value)

    def test_to_internal_value_float_values(self):
        """Test deserialization with float values"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 1000.5,
            "ub": 10000.75
        }
        result = self.field.to_internal_value(data)
        assert result == data

    def test_to_internal_value_very_small_positive_lb(self):
        """Test deserialization with very small positive lower bound"""
        data = {
            "distribution": "LOGNORMAL-CI90",
            "lb": 0.001,
            "ub": 10000
        }
        result = self.field.to_internal_value(data)
        assert result == data


class TestQuantitativeRiskStudyWriteSerializer:
    """Tests for QuantitativeRiskStudyWriteSerializer"""

    def test_validate_risk_tolerance_strips_curve_data(self):
        """Test that curve_data is stripped from risk_tolerance during validation"""
        serializer = QuantitativeRiskStudyWriteSerializer()

        risk_tolerance = {
            "points": {
                "point1": {"probability": 0.1, "acceptable_loss": 10000},
                "point2": {"probability": 0.01, "acceptable_loss": 100000}
            },
            "curve_data": {
                "loss_values": [1000, 2000, 3000],
                "probability_values": [0.5, 0.3, 0.1]
            }
        }

        validated = serializer.validate_risk_tolerance(risk_tolerance)

        # curve_data should be removed
        assert "curve_data" not in validated
        # points should remain
        assert "points" in validated
        assert validated["points"] == risk_tolerance["points"]

    def test_validate_risk_tolerance_no_curve_data(self):
        """Test validation when risk_tolerance has no curve_data"""
        serializer = QuantitativeRiskStudyWriteSerializer()

        risk_tolerance = {
            "points": {
                "point1": {"probability": 0.1, "acceptable_loss": 10000}
            }
        }

        validated = serializer.validate_risk_tolerance(risk_tolerance)

        # Should return the same data
        assert validated == risk_tolerance

    def test_validate_risk_tolerance_null(self):
        """Test validation with null risk_tolerance"""
        serializer = QuantitativeRiskStudyWriteSerializer()

        validated = serializer.validate_risk_tolerance(None)
        assert validated is None

    def test_validate_risk_tolerance_not_dict(self):
        """Test validation when risk_tolerance is not a dictionary"""
        serializer = QuantitativeRiskStudyWriteSerializer()

        # Non-dict values should be returned as-is
        # (actual validation happens at model level)
        validated = serializer.validate_risk_tolerance("not a dict")
        assert validated == "not a dict"

    def test_validate_risk_tolerance_preserves_other_fields(self):
        """Test that other fields in risk_tolerance are preserved"""
        serializer = QuantitativeRiskStudyWriteSerializer()

        risk_tolerance = {
            "points": {
                "point1": {"probability": 0.1, "acceptable_loss": 10000}
            },
            "curve_data": {"should": "be removed"},
            "custom_field": "should remain",
            "another_field": 12345
        }

        validated = serializer.validate_risk_tolerance(risk_tolerance)

        assert "curve_data" not in validated
        assert validated["points"] == risk_tolerance["points"]
        assert validated["custom_field"] == "should remain"
        assert validated["another_field"] == 12345