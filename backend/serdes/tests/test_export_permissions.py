"""
Guard the contract between the domain export scope and the built-in roles.

``export_domain`` requires view access on every model (or its permission owner) returned by
``get_domain_export_objects`` — a single key without a matching permission in
the role definitions breaks domain export for everyone holding that role,
including global administrators.
"""

import pytest

from core.startup import (
    ADMINISTRATOR_PERMISSIONS_LIST,
    ANALYST_PERMISSIONS_LIST,
    DOMAIN_MANAGER_PERMISSIONS_LIST,
    READER_PERMISSIONS_LIST,
)
from iam.models import Folder
from serdes.utils import domain_permission_model, get_domain_export_objects

EXPORTING_ROLES = {
    "reader": READER_PERMISSIONS_LIST,
    "analyst": ANALYST_PERMISSIONS_LIST,
    "domain_manager": DOMAIN_MANAGER_PERMISSIONS_LIST,
    "administrator": ADMINISTRATOR_PERMISSIONS_LIST,
}


@pytest.mark.django_db
@pytest.mark.parametrize("role_name", sorted(EXPORTING_ROLES))
def test_roles_can_view_every_exported_model(role_name):
    domain = Folder.objects.create(
        name="export-perms", content_type=Folder.ContentType.DOMAIN
    )
    permissions = set(EXPORTING_ROLES[role_name])
    missing = sorted(
        model
        for model in get_domain_export_objects(domain)
        if f"view_{domain_permission_model(model)}" not in permissions
    )
    assert not missing, (
        f"{role_name} lacks view permission on exported models: {missing}"
    )
