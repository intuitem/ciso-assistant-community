"""Asset lifecycle stages in domain export / import: carried by name."""

import io

import pytest

from core.models import Asset, Terminology
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from serdes.domain_io import export_domain, import_objects, process_uploaded_file

STAGE = Terminology.FieldPath.ASSET_LIFECYCLE_STAGE


@pytest.fixture
def admin_user():
    root = Folder.get_root_folder()
    user = User.objects.create_user("asset-lifecycle-export@test.com")
    group = UserGroup.objects.create(name="alx-admins", folder=root)
    group.user_set.add(user)
    RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-ADM"),
        folder=root,
        is_recursive=True,
    ).perimeter_folders.add(root)
    return user


@pytest.mark.django_db
def test_lifecycle_stage_survives_round_trip(admin_user):
    Terminology.create_default_asset_lifecycle_stages()
    domain = Folder.objects.create(
        name="ALX Source",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    custom = Terminology.objects.create(name="alx_frozen", field_path=STAGE)
    Asset.objects.create(
        name="ALX Active",
        folder=domain,
        lifecycle_stage=Terminology.objects.get(name="active", field_path=STAGE),
    )
    Asset.objects.create(name="ALX Custom", folder=domain, lifecycle_stage=custom)
    Asset.objects.create(name="ALX None", folder=domain)

    response = export_domain(domain, admin_user)
    assert response.status_code == 200
    json_dump = process_uploaded_file(io.BytesIO(response.content))

    # Simulate a target instance that never had the custom stage.
    domain.delete()
    custom.delete()

    result = import_objects(
        json_dump,
        domain_name="ALX Imported",
        load_missing_libraries=True,
        user=admin_user,
    )
    assert result["message"] == "Import successful"

    assets = {
        a.name: a.lifecycle_stage
        for a in Asset.objects.filter(folder__name="ALX Imported")
    }
    assert assets["ALX Active"].name == "active"
    assert assets["ALX Active"].builtin
    assert assets["ALX Custom"].field_path == STAGE
    assert assets["ALX Custom"].name == "alx_frozen"
    assert assets["ALX None"] is None
    assert result["created_referentials"]["terminologies"] == ["alx_frozen"]
