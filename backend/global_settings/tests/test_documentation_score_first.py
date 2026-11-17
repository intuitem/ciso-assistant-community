"""The general setting that shows documentation scores before implementation
scores, as in the CCB CyFun self-assessment tools."""

import pytest

from global_settings.models import GlobalSettings
from global_settings.serializers import GeneralSettingsSerializer


@pytest.fixture
def general_settings(db):
    settings, _ = GlobalSettings.objects.get_or_create(name="general")
    settings.value = settings.value or {}
    settings.save()
    return settings


@pytest.mark.django_db
class TestDocumentationScoreFirst:
    def test_off_by_default(self):
        assert (
            GlobalSettings.GENERAL_DEFAULT_VALUE["documentation_score_first"] is False
        )

    def test_update_is_stored_and_returned(self, general_settings):
        GeneralSettingsSerializer().update(
            general_settings, {"value": {"documentation_score_first": True}}
        )
        general_settings.refresh_from_db()
        assert general_settings.value["documentation_score_first"] is True
        data = GeneralSettingsSerializer(general_settings).data
        assert data["value"]["documentation_score_first"] is True
