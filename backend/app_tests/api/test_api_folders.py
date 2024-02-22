import pytest
from rest_framework.test import APIClient
from iam.models import Folder

from test_utils import EndpointTestsQueries

# Generic folder data for tests
FOLDER_NAME = "Test Folder"
FOLDER_DESCRIPTION = "Test Description"
FOLDER_CONTENT_TYPE = "DOMAIN"


@pytest.mark.django_db
class TestFoldersUnauthenticated:
    """Perform tests on Folders API endpoint without authentication"""

    client = APIClient()

    def test_get_folders(self):
        """test to get folders from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Folders",
            Folder,
            {"name": FOLDER_NAME, "description": FOLDER_DESCRIPTION},
        )

    def test_create_folders(self):
        """test to create folders with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Folders",
            Folder,
            {"name": FOLDER_NAME, "description": FOLDER_DESCRIPTION},
        )

    def test_update_folders(self):
        """test to update folders with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Folders",
            Folder,
            {"name": FOLDER_NAME, "description": FOLDER_DESCRIPTION},
            {"name": "new " + FOLDER_NAME, "description": "new " + FOLDER_DESCRIPTION},
        )

    def test_delete_folders(self):
        """test to delete folders with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Folders",
            Folder,
            {
                "name": FOLDER_NAME,
            },
        )


@pytest.mark.django_db
class TestFoldersAuthenticated:
    """Perform tests on Folders API endpoint with authentication"""

    def test_get_folders(self, authenticated_client):
        """test to get folders from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            authenticated_client,
            "Folders",
            Folder,
            {"name": FOLDER_NAME, "description": FOLDER_DESCRIPTION},
            {
                "parent_folder": {"str": Folder.get_root_folder().name},
                "content_type": FOLDER_CONTENT_TYPE,
            },
        )

    def test_create_folders(self, authenticated_client):
        """test to create folders with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            authenticated_client,
            "Folders",
            Folder,
            {
                "name": FOLDER_NAME,
                "description": FOLDER_DESCRIPTION,
                "parent_folder": str(Folder.get_root_folder().id),
            },
            {
                "parent_folder": {"str": Folder.get_root_folder().name},
                "content_type": FOLDER_CONTENT_TYPE,
            },
        )

    def test_update_folders(self, authenticated_client):
        """test to update folders with the API with authentication"""

        EndpointTestsQueries.Auth.update_object(
            authenticated_client,
            "Folders",
            Folder,
            {
                "name": FOLDER_NAME,
                "description": FOLDER_DESCRIPTION,
            },
            {
                "name": "new " + FOLDER_NAME,
                "description": "new " + FOLDER_DESCRIPTION,
                "parent_folder": str(Folder.objects.create(name="test").id),
            },
        )

    def test_delete_folders(self, authenticated_client):
        """test to delete folders with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            authenticated_client,
            "Folders",
            Folder,
            {
                "name": FOLDER_NAME,
            },
        )
