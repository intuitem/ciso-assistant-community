import pytest
from rest_framework.test import APIClient
from core.models import Asset
from iam.models import Folder

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries

# Generic asset data for tests
ASSET_NAME = "Test Asset"
ASSET_DESCRIPTION = "Test Description"
ASSET_BUSINESS_VALUE = "test"
ASSET_TYPE = ("PR", "Primary")
ASSET_TYPE2 = ("SP", "Support")
ASSET_PARENT_ASSETS = []


@pytest.mark.django_db
class TestAssetsUnauthenticated:
    """Perform tests on Assets API endpoint without authentication"""

    client = APIClient()

    def test_get_assets(self):
        """test to get assets from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_assets(self):
        """test to create assets with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_assets(self):
        """test to update assets with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + ASSET_NAME,
                "description": "new " + ASSET_DESCRIPTION,
            },
        )

    def test_delete_assets(self):
        """test to delete assets with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Assets",
            Asset,
            {"name": ASSET_NAME, "folder": Folder.objects.create(name="test")},
        )


@pytest.mark.django_db
class TestAssetsAuthenticated:
    """Perform tests on Assets API endpoint with authentication"""

    def test_get_assets(self, test):
        """test to get assets from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "business_value": ASSET_BUSINESS_VALUE,
                "type": ASSET_TYPE[0],
                "folder": test.folder,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "type": ASSET_TYPE[1],
            },
            user_group=test.user_group,
        )

    def test_create_assets(self, test):
        """test to create assets without a parent asset the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "business_value": ASSET_BUSINESS_VALUE,
                "type": ASSET_TYPE[0],
                "parent_assets": [],
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "type": ASSET_TYPE[1],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_create_assets_with_parent(self, test):
        """test to create assets with a parent asset with the API with authentication"""

        root_asset = Asset.objects.create(
            name="root",
            description=ASSET_DESCRIPTION,
            type=ASSET_TYPE[0],
            folder=test.folder,
        )

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "business_value": ASSET_BUSINESS_VALUE,
                "type": ASSET_TYPE2[0],
                "parent_assets": [str(root_asset.id)],
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "type": ASSET_TYPE2[1],
                "parent_assets": [{"id": str(root_asset.id), "str": root_asset.name}],
            },
            base_count=1,
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_assets(self, test):
        """test to update assets with the API with authentication"""

        folder = Folder.objects.create(name="test2")

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "business_value": ASSET_BUSINESS_VALUE,
                "type": ASSET_TYPE[0],
                "folder": test.folder,
            },
            {
                "name": "new " + ASSET_NAME,
                "description": "new " + ASSET_DESCRIPTION,
                "business_value": "new " + ASSET_BUSINESS_VALUE,
                "type": ASSET_TYPE2[0],
                "folder": str(folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "type": ASSET_TYPE[1],
            },
            user_group=test.user_group,
        )

    def test_delete_assets(self, test):
        """test to delete assets with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Assets",
            Asset,
            {"name": ASSET_NAME, "folder": test.folder},
            user_group=test.user_group,
        )

    def test_get_type_choices(self, test):
        """test to get type choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client, "Assets", "type", Asset.Type.choices
        )
