"""The enterprise permissions offered when building a custom role."""

import pytest

from enterprise_core.apps import ADMINISTRATOR_PERMISSIONS
from iam.models import get_permission_catalog


@pytest.mark.django_db
def test_enterprise_administrator_permissions_are_offered() -> None:
    assert set(ADMINISTRATOR_PERMISSIONS) <= set(
        get_permission_catalog().values_list("codename", flat=True)
    )


@pytest.mark.django_db
@pytest.mark.parametrize("codename", ["add_clientsettings", "delete_clientsettings"])
def test_client_settings_cannot_be_created_or_deleted_through_a_role(
    codename: str,
) -> None:
    assert not get_permission_catalog().filter(codename=codename).exists()
