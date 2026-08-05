"""Asset classes in domain export / import: carried as canonical paths."""

import io

import pytest

from serdes.domain_io import export_domain, import_asset_class, import_objects
from serdes.domain_io import process_uploaded_file
from core.models import Asset, AssetClass
from iam.models import Folder, Role, RoleAssignment, User, UserGroup


@pytest.fixture
def root_folder():
    return Folder.get_root_folder()


@pytest.fixture
def admin_user(root_folder):
    user = User.objects.create_user("asset-class-export@test.com")
    group = UserGroup.objects.create(name="acx-admins", folder=root_folder)
    group.user_set.add(user)
    RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-ADM"),
        folder=root_folder,
        is_recursive=True,
    ).perimeter_folders.add(root_folder)
    return user


@pytest.fixture
def domain_with_classed_assets(root_folder):
    domain = Folder.objects.create(
        name="ACX Source",
        parent_folder=root_folder,
        content_type=Folder.ContentType.DOMAIN,
    )
    custom_root = AssetClass.objects.create(name="ACXRoot")
    custom_leaf = AssetClass.objects.create(name="ACXLeaf", parent=custom_root)
    # Names are unique only per parent, so pick a known-unique one.
    builtin = AssetClass.objects.get(name="assetClassServers")

    Asset.objects.create(name="ACX Custom", folder=domain, asset_class=custom_leaf)
    Asset.objects.create(name="ACX Builtin", folder=domain, asset_class=builtin)
    Asset.objects.create(name="ACX Unclassified", folder=domain)
    return {"domain": domain, "custom_leaf": custom_leaf, "builtin": builtin}


@pytest.mark.django_db
class TestImportAssetClass:
    def test_existing_path_is_reused_not_duplicated(self):
        parent = AssetClass.objects.create(name="ACXKeep")
        leaf = AssetClass.objects.create(name="ACXLeaf", parent=parent)

        assert import_asset_class("ACXKeep/ACXLeaf") == leaf
        assert AssetClass.objects.filter(name="ACXLeaf").count() == 1

    def test_missing_segments_are_created_as_non_builtin(self):
        resolved = import_asset_class("ACXNew/ACXChild")

        assert resolved.name == "ACXChild"
        assert resolved.full_path == "ACXNew/ACXChild"
        assert resolved.builtin is False
        assert resolved.parent.builtin is False

    def test_builtin_path_resolves_without_creating_a_duplicate(self):
        builtin = AssetClass.objects.filter(builtin=True, parent__isnull=False).first()
        before = AssetClass.objects.count()

        assert import_asset_class(builtin.full_path) == builtin
        assert AssetClass.objects.count() == before

    def test_blank_and_none_resolve_to_none(self):
        assert import_asset_class(None) is None
        assert import_asset_class("") is None
        assert import_asset_class("   ") is None


@pytest.mark.django_db
class TestAssetClassRoundTrip:
    def test_classes_survive_export_import_onto_a_stripped_instance(
        self, domain_with_classed_assets, admin_user
    ):
        builtin_pk = domain_with_classed_assets["builtin"].pk
        builtin_path = domain_with_classed_assets["builtin"].full_path

        response = export_domain(domain_with_classed_assets["domain"], admin_user)
        assert response.status_code == 200
        json_dump = process_uploaded_file(io.BytesIO(response.content))

        # Simulate a target instance that never had the custom tree.
        Folder.objects.filter(name="ACX Source").delete()
        AssetClass.objects.filter(name="ACXRoot", parent=None).delete()
        assert not AssetClass.objects.filter(name="ACXLeaf").exists()
        classes_before = AssetClass.objects.count()

        result = import_objects(
            json_dump,
            domain_name="ACX Imported",
            load_missing_libraries=True,
            user=admin_user,
        )
        assert result["message"] == "Import successful"

        imported = Folder.objects.get(
            name="ACX Imported", content_type=Folder.ContentType.DOMAIN
        )
        assets = {a.name: a for a in Asset.objects.filter(folder=imported)}

        custom = assets["ACX Custom"].asset_class
        assert custom is not None
        assert custom.full_path == "ACXRoot/ACXLeaf"
        assert custom.builtin is False

        rebound = assets["ACX Builtin"].asset_class
        assert rebound.pk == builtin_pk
        assert rebound.full_path == builtin_path
        assert rebound.builtin is True

        assert AssetClass.objects.count() == classes_before + 2

        assert assets["ACX Unclassified"].asset_class is None
