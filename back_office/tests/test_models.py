from uuid import UUID
from core.models import *
from back_office.models import *
from iam.models import *
from library.utils import *
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def root_folder_fixture():
    Folder.objects.create(
                name="Global", content_type=Folder.ContentType.ROOT, builtin=True)


@pytest.mark.django_db
class TestAsset:
    pytestmark = pytest.mark.django_db

    def test_asset_creation(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        asset = Asset.objects.create(name="Asset", folder=root_folder)
        assert asset.name == "Asset"
        assert asset.folder == root_folder
        assert asset.type == Asset.Type.PRIMARY

    def test_asset_creation_same_name(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        Asset.objects.create(name="Asset", folder=root_folder)
        with pytest.raises(ValidationError):
            Asset.objects.create(name="Asset", folder=root_folder)

    def test_asset_creation_same_name_different_folder(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(name="Parent", folder=root_folder)

        asset1 = Asset.objects.create(name="Asset", folder=root_folder)
        asset2 = Asset.objects.create(name="Asset", folder=folder)
        assert asset1.name == "Asset"
        assert asset2.name == "Asset"
        assert asset1.type == Asset.Type.PRIMARY
        assert asset2.type == Asset.Type.PRIMARY
        assert asset1.folder == root_folder
        assert asset2.folder == folder

    def test_asset_primary_does_not_have_parent_asset(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        asset = Asset.objects.create(name="Asset", folder=root_folder, type=Asset.Type.PRIMARY)
        parent_asset = Asset.objects.create(name="Parent", folder=root_folder)
        with pytest.raises(ValidationError):
            asset.parent_asset = parent_asset
            asset.save()

    def test_asset_support_must_have_parent_asset(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        parent_asset = Asset.objects.create(name="Parent", folder=root_folder)
        with pytest.raises(ValidationError):
            Asset.objects.create(name="Asset", folder=root_folder, type=Asset.Type.SUPPORT, parent_asset=None)

    def test_asset_can_not_be_its_own_parent(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        parent_asset = Asset.objects.create(name="Parent", folder=root_folder)
        asset = Asset.objects.create(name="Asset", folder=root_folder, type=Asset.Type.SUPPORT, parent_asset=parent_asset)
        with pytest.raises(ValidationError):
            asset.parent_asset = asset
            asset.save()

    def test_asset_root_asset_must_be_primary(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        parent_asset = Asset.objects.create(name="Parent", folder=root_folder)
        asset1 = Asset.objects.create(name="Asset1", folder=root_folder, type=Asset.Type.SUPPORT, parent_asset=parent_asset)
        asset2 = Asset.objects.create(name="Asset2", folder=root_folder, type=Asset.Type.SUPPORT, parent_asset=asset1)
        with pytest.raises(ValidationError):
            asset1.parent_asset = asset2
            asset1.save()

    def test_asset_graph_has_no_cycles(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        parent_asset = Asset.objects.create(name="Parent", folder=root_folder)
        asset1 = Asset.objects.create(name="Asset1", folder=root_folder, type=Asset.Type.SUPPORT, parent_asset=parent_asset)
        asset2 = Asset.objects.create(name="Asset2", folder=root_folder, type=Asset.Type.SUPPORT, parent_asset=asset1)
        with pytest.raises(ValidationError):
            asset1.parent_asset = asset2
            asset1.save()

    def test_asset_graph_has_no_cycles_2(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        parent_asset = Asset.objects.create(name="Parent", folder=root_folder)
        asset1 = Asset.objects.create(name="Asset1", folder=root_folder, type=Asset.Type.SUPPORT, parent_asset=parent_asset)
        asset2 = Asset.objects.create(name="Asset2", folder=root_folder, type=Asset.Type.SUPPORT, parent_asset=asset1)
        asset3 = Asset.objects.create(name="Asset3", folder=root_folder, type=Asset.Type.SUPPORT, parent_asset=asset2)
        with pytest.raises(ValidationError):
            asset1.parent_asset = asset3
            asset1.save()
