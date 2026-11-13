"""The enterprise permissions offered when building a custom role."""

import pytest

from iam.models import get_permission_catalog


@pytest.mark.django_db
@pytest.mark.parametrize(
    "codename",
    [
        "add_clientsettings",
        "change_clientsettings",
        "delete_clientsettings",
        "view_clientsettings",
    ],
)
def test_client_settings_stay_administrator_only(codename: str) -> None:
    assert not get_permission_catalog().filter(codename=codename).exists()
