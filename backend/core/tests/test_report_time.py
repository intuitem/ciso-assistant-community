"""Times printed in reports: the instance zone, with each time's UTC offset."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from core.utils import (
    format_report_timestamp,
    get_report_timezone,
    get_report_timezone_choices,
)
from global_settings.models import GlobalSettings


@pytest.mark.parametrize(
    "instant,zone,expected",
    [
        (datetime(2026, 7, 1, 8, 0), "Europe/Paris", "2026-07-01 10:00:00 (UTC+02:00)"),
        (
            datetime(2026, 12, 1, 8, 0),
            "Europe/Paris",
            "2026-12-01 09:00:00 (UTC+01:00)",
        ),
        (datetime(2026, 7, 1, 8, 0), "UTC", "2026-07-01 08:00:00 (UTC)"),
        (
            datetime(2026, 7, 1, 8, 0),
            "America/New_York",
            "2026-07-01 04:00:00 (UTC-04:00)",
        ),
        (datetime(2026, 7, 1, 8, 0), "Asia/Kolkata", "2026-07-01 13:30:00 (UTC+05:30)"),
        (
            datetime(2026, 7, 1, 8, 0),
            "America/St_Johns",
            "2026-07-01 05:30:00 (UTC-02:30)",
        ),
        (
            datetime(1900, 1, 1, 12, 0),
            "Europe/Paris",
            "1900-01-01 12:09:21 (UTC+00:09:21)",
        ),
        (
            datetime(1850, 1, 1, 12, 0),
            "America/New_York",
            "1850-01-01 07:03:58 (UTC-04:56:02)",
        ),
    ],
)
def test_each_time_carries_its_own_utc_offset(
    instant: datetime, zone: str, expected: str
) -> None:
    utc_instant = instant.replace(tzinfo=timezone.utc)
    assert format_report_timestamp(utc_instant, ZoneInfo(zone)) == expected


def test_an_unset_time_prints_the_placeholder() -> None:
    assert format_report_timestamp(None, ZoneInfo("Europe/Paris")) == "-"


@pytest.mark.django_db
class TestGetReportTimezone:
    def _set(self, value: object) -> None:
        settings, _ = GlobalSettings.objects.get_or_create(name="general")
        settings.value = {**(settings.value or {}), "report_timezone": value}
        settings.save()

    def test_is_utc_when_the_key_is_missing(self) -> None:
        settings, _ = GlobalSettings.objects.get_or_create(name="general")
        settings.value = {
            k: v for k, v in (settings.value or {}).items() if k != "report_timezone"
        }
        settings.save()
        assert get_report_timezone() == ZoneInfo("UTC")

    def test_follows_the_setting(self) -> None:
        self._set("Europe/Paris")
        assert get_report_timezone() == ZoneInfo("Europe/Paris")

    def test_falls_back_to_utc_on_a_corrupted_value(self) -> None:
        self._set("Mars/Olympus_Mons")
        assert get_report_timezone() == ZoneInfo("UTC")


class TestGetReportTimezoneChoices:
    def test_offers_current_iana_names_only(self) -> None:
        choices = get_report_timezone_choices()
        assert "Europe/Kyiv" in choices
        assert "Asia/Kolkata" in choices
        assert "Europe/Kiev" not in choices
        assert "US/Eastern" not in choices
        assert "Factory" not in choices

    def test_labels_each_region_with_its_current_offset(self) -> None:
        winter = datetime(2026, 12, 1, 8, 0, tzinfo=timezone.utc)
        choices = get_report_timezone_choices(winter)
        assert choices["Europe/Paris"] == "(UTC+01:00) Europe/Paris"
        assert choices["America/New_York"] == "(UTC-05:00) America/New_York"

    def test_starts_from_the_west_with_utc_first_at_offset_zero(self) -> None:
        winter = datetime(2026, 12, 1, 8, 0, tzinfo=timezone.utc)
        names = list(get_report_timezone_choices(winter))
        assert names.index("America/New_York") < names.index("UTC")
        assert names.index("UTC") < names.index("Europe/London")
        assert names.index("Europe/London") < names.index("Europe/Paris")
        assert get_report_timezone_choices(winter)["UTC"] == "(UTC) UTC"
