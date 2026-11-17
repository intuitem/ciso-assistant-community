"""The instance time zone used to print times in reports and exports."""

import pytest
from django.db.backends.base.base import BaseDatabaseWrapper
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from global_settings.models import GlobalSettings
from global_settings.serializers import GeneralSettingsSerializer
from global_settings.tests.test_global_settings_api import (  # noqa: F401
    app_config,
    domain,
    reader_client,
)


@pytest.fixture
def general_settings(db: BaseDatabaseWrapper) -> GlobalSettings:
    settings, _ = GlobalSettings.objects.get_or_create(name="general")
    settings.value = settings.value or {}
    settings.save()
    return settings


def _save(general_settings: GlobalSettings, value: object) -> None:
    GeneralSettingsSerializer().update(
        general_settings, {"value": {"report_timezone": value}}
    )


@pytest.mark.django_db
class TestReportTimezoneSetting:
    def test_a_region_is_stored(self, general_settings: GlobalSettings) -> None:
        _save(general_settings, "Europe/Kyiv")
        general_settings.refresh_from_db()
        assert general_settings.value["report_timezone"] == "Europe/Kyiv"

    @pytest.mark.parametrize(
        "value",
        [
            "Mars/Olympus_Mons",
            "",
            "UTC+02:00",
            "../../etc/passwd",
            2,
            "Europe/Kiev",
            "US/Eastern",
            "Factory",
        ],
    )
    def test_anything_but_a_current_region_is_rejected(
        self, general_settings: GlobalSettings, value: object
    ) -> None:
        with pytest.raises(ValidationError):
            _save(general_settings, value)

    def test_an_already_stored_legacy_name_does_not_block_saving(
        self, general_settings: GlobalSettings
    ) -> None:
        general_settings.value = {
            **general_settings.value,
            "report_timezone": "Europe/Kiev",
        }
        general_settings.save()

        _save(general_settings, "Europe/Kiev")

        general_settings.refresh_from_db()
        assert general_settings.value["report_timezone"] == "Europe/Kiev"

    def test_an_already_stored_unknown_name_is_not_kept(
        self, general_settings: GlobalSettings
    ) -> None:
        general_settings.value = {
            **general_settings.value,
            "report_timezone": "Mars/Olympus_Mons",
        }
        general_settings.save()

        with pytest.raises(ValidationError):
            _save(general_settings, "Mars/Olympus_Mons")

    def test_the_offered_zones_include_a_stored_legacy_name(
        self,
        general_settings: GlobalSettings,
        reader_client: APIClient,  # noqa: F811
    ) -> None:
        general_settings.value = {
            **general_settings.value,
            "report_timezone": "Europe/Kiev",
        }
        general_settings.save()

        response = reader_client.get("/api/settings/general/report_timezone/")

        assert "Europe/Kiev" in response.json()
