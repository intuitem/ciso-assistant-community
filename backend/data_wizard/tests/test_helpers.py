"""
Unit tests for data_wizard top-level helper functions.
No database access required.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from data_wizard.views import (
    _parse_date,
    _parse_datetime,
    _parse_time_to_seconds,
    _parse_security_objectives,
    _parse_recovery_objectives,
    _reverse_scale_value,
    normalize_datetime_columns,
    resolve_container_name,
)


# ─────────────────────────────────────────────────────────────────────────────
# _parse_date
# ─────────────────────────────────────────────────────────────────────────────


class TestParseDate:
    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_date("") is None

    def test_datetime_object_returns_date_string(self):
        dt = datetime(2024, 6, 15, 10, 30)
        assert _parse_date(dt) == "2024-06-15"

    def test_iso_string_with_time_strips_time(self):
        assert _parse_date("2024-06-15T10:30:00") == "2024-06-15"

    def test_plain_date_string_passthrough(self):
        assert _parse_date("2024-06-15") == "2024-06-15"

    def test_zero_value_returns_none(self):
        assert _parse_date(0) is None


# ─────────────────────────────────────────────────────────────────────────────
# _parse_datetime
# ─────────────────────────────────────────────────────────────────────────────


class TestParseDatetime:
    def test_none_returns_none(self):
        assert _parse_datetime(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_datetime("") is None

    def test_datetime_object_returns_iso(self):
        dt = datetime(2024, 6, 15, 10, 30, 0)
        result = _parse_datetime(dt)
        assert "2024-06-15" in result
        assert "10:30" in result

    def test_string_passthrough(self):
        assert _parse_datetime("2024-06-15T10:30:00Z") == "2024-06-15T10:30:00Z"


# ─────────────────────────────────────────────────────────────────────────────
# _parse_time_to_seconds
# ─────────────────────────────────────────────────────────────────────────────


class TestParseTimeToSeconds:
    def test_empty_returns_none(self):
        assert _parse_time_to_seconds("") is None

    def test_none_returns_none(self):
        assert _parse_time_to_seconds(None) is None

    def test_plain_integer_string(self):
        assert _parse_time_to_seconds("3600") == 3600

    def test_hours_only(self):
        assert _parse_time_to_seconds("4h") == 4 * 3600

    def test_minutes_only(self):
        assert _parse_time_to_seconds("30m") == 30 * 60

    def test_seconds_only(self):
        assert _parse_time_to_seconds("45s") == 45

    def test_hours_and_minutes(self):
        assert _parse_time_to_seconds("2h30m") == 2 * 3600 + 30 * 60

    def test_hours_minutes_seconds(self):
        assert _parse_time_to_seconds("1h10m30s") == 3600 + 600 + 30

    def test_invalid_string_returns_none(self):
        assert _parse_time_to_seconds("invalid") is None

    def test_leading_zeros(self):
        assert _parse_time_to_seconds("01m30s") == 90


# ─────────────────────────────────────────────────────────────────────────────
# _reverse_scale_value
# ─────────────────────────────────────────────────────────────────────────────


class TestReverseScaleValue:
    NUMERIC_SCALE = [1, 2, 3, 4]
    STRING_SCALE = ["Low", "Medium", "High", "Critical"]

    def test_numeric_match(self):
        assert _reverse_scale_value("2", self.NUMERIC_SCALE) == 1  # index 1

    def test_exact_numeric_match_int(self):
        assert _reverse_scale_value("4", self.NUMERIC_SCALE) == 3  # index 3

    def test_string_match_case_insensitive(self):
        assert _reverse_scale_value("medium", self.STRING_SCALE) == 1

    def test_string_match_exact_case(self):
        assert _reverse_scale_value("High", self.STRING_SCALE) == 2

    def test_no_match_returns_none(self):
        assert _reverse_scale_value("Extreme", self.STRING_SCALE) is None

    def test_numeric_string_not_in_scale_returns_none(self):
        assert _reverse_scale_value("99", self.NUMERIC_SCALE) is None


# ─────────────────────────────────────────────────────────────────────────────
# _parse_security_objectives
# ─────────────────────────────────────────────────────────────────────────────


class TestParseSecurityObjectives:
    SCALE = [1, 2, 3, 4]  # indices 0-3 map to values 1-4

    def test_empty_string_returns_empty_dict(self):
        assert _parse_security_objectives("", self.SCALE) == {}

    def test_none_returns_empty_dict(self):
        assert _parse_security_objectives(None, self.SCALE) == {}

    def test_single_objective(self):
        result = _parse_security_objectives("confidentiality: 2", self.SCALE)
        assert "confidentiality" in result
        assert result["confidentiality"]["is_enabled"] is True

    def test_multiple_objectives(self):
        result = _parse_security_objectives(
            "confidentiality: 1, integrity: 2, availability: 3", self.SCALE
        )
        assert len(result) == 3
        assert "integrity" in result

    def test_unknown_value_excluded(self):
        result = _parse_security_objectives("confidentiality: 99", self.SCALE)
        assert result == {}

    def test_malformed_entry_skipped(self):
        result = _parse_security_objectives("confidentiality_no_colon", self.SCALE)
        assert result == {}


# ─────────────────────────────────────────────────────────────────────────────
# _parse_recovery_objectives
# ─────────────────────────────────────────────────────────────────────────────


class TestParseRecoveryObjectives:
    def test_empty_returns_empty(self):
        assert _parse_recovery_objectives("") == {}

    def test_none_returns_empty(self):
        assert _parse_recovery_objectives(None) == {}

    def test_rto_rpo_mtd(self):
        result = _parse_recovery_objectives("rto: 4h, rpo: 2h, mtd: 6h")
        assert result["rto"]["value"] == 4 * 3600
        assert result["rpo"]["value"] == 2 * 3600
        assert result["mtd"]["value"] == 6 * 3600

    def test_mixed_time_formats(self):
        result = _parse_recovery_objectives("rto: 1h30m, rpo: 45m")
        assert result["rto"]["value"] == 90 * 60
        assert result["rpo"]["value"] == 45 * 60

    def test_invalid_value_excluded(self):
        result = _parse_recovery_objectives("rto: invalid_time")
        assert result == {}

    def test_entry_without_colon_skipped(self):
        result = _parse_recovery_objectives("rto_no_colon")
        assert result == {}


# ─────────────────────────────────────────────────────────────────────────────
# resolve_container_name
# ─────────────────────────────────────────────────────────────────────────────


class TestResolveContainerName:
    def test_uses_x_name_header_when_present(self):
        request = MagicMock()
        request.headers = {"X-Name": "My Assessment"}
        assert resolve_container_name(request, "prefix") == "My Assessment"

    def test_strips_whitespace_from_header(self):
        request = MagicMock()
        request.headers = {"X-Name": "  My Assessment  "}
        assert resolve_container_name(request, "prefix") == "My Assessment"

    def test_falls_back_to_timestamp_when_header_absent(self):
        request = MagicMock()
        request.headers = {}
        name = resolve_container_name(request, "import")
        assert name.startswith("import_")
        assert len(name) == len("import_") + len("20240101_120000")

    def test_falls_back_to_timestamp_when_header_empty(self):
        request = MagicMock()
        request.headers = {"X-Name": "  "}
        name = resolve_container_name(request, "audit")
        assert name.startswith("audit_")

    def test_none_request_uses_timestamp(self):
        name = resolve_container_name(None, "test")
        assert name.startswith("test_")


# ─────────────────────────────────────────────────────────────────────────────
# normalize_datetime_columns
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeDatetimeColumns:
    def test_date_only_column_converted_to_date_string(self):
        import pandas as pd

        df = pd.DataFrame({"dt": pd.to_datetime(["2024-06-15"])})
        result = normalize_datetime_columns(df)
        assert result["dt"].iloc[0] == "2024-06-15"

    def test_nat_becomes_empty_string(self):
        import pandas as pd

        df = pd.DataFrame({"dt": pd.to_datetime([None])})
        result = normalize_datetime_columns(df)
        assert result["dt"].iloc[0] == ""

    def test_non_datetime_column_unchanged(self):
        import pandas as pd

        df = pd.DataFrame({"name": ["Alice"], "age": [30]})
        result = normalize_datetime_columns(df)
        assert list(result["name"]) == ["Alice"]
        assert list(result["age"]) == [30]
