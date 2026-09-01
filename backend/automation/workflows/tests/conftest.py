"""The workflows API, webhook ingress, scheduler and event dispatch are all
gated behind the `workflows` feature flag. The suite exercises them with the
flag on; flag-off behavior has its own tests (test_feature_flag.py), which
turn it back off explicitly."""

import pytest

from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache


@pytest.fixture(autouse=True)
def _workflows_feature_flag(db):
    ff_settings, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS
    )
    ff_settings.value = {**(ff_settings.value or {}), "workflows": True}
    ff_settings.save()
    # Direct ORM write: bypasses the serializer, the single invalidation point.
    clear_feature_flags_cache()
    yield
    clear_feature_flags_cache()
