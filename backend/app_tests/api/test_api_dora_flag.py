import pytest
from rest_framework.test import APIClient

from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import User

ENDPOINT = "/api/resilience/dora-incident-reports/"


def set_dora(enabled: bool):
    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
    )
    gs.value = {**(gs.value or {}), "dora": enabled}
    gs.save()
    clear_feature_flags_cache()


@pytest.fixture
def admin(db):
    client = APIClient()
    client.force_authenticate(User.objects.create_superuser("dora-admin@tests.com"))
    return client


def test_reports_are_unreachable_when_dora_is_off(admin):
    """The page redirects when the flag is off, so the API must refuse too:
    a UI-only gate leaves the endpoint open."""
    set_dora(False)
    assert admin.get(ENDPOINT).status_code == 403
    assert admin.post(ENDPOINT, {}, format="json").status_code == 403


def test_reports_are_reachable_when_dora_is_on(admin):
    set_dora(True)
    assert admin.get(ENDPOINT).status_code == 200
    # Reaches validation rather than the permission layer.
    assert admin.post(ENDPOINT, {}, format="json").status_code == 400
