import pytest
from rest_framework import status
from rest_framework.test import APIClient
from iam.models import Folder

from test_utils import EndpointTestsQueries
from test_vars import GROUPS_PERMISSIONS

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

    def test_get_assigned_folder(self, test):
        """test to get the folder assigned to the user's user group"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Folders",
            test_params={
                "name": test.assigned_folder.name,
            },
            item_search_field="name",
            base_count=-1,
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_get_folders(self, test):
        """test to get folders from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Folders",
            Folder,
            {
                "name": FOLDER_NAME,
                "description": FOLDER_DESCRIPTION,
                "parent_folder": test.folder,
            },
            {
                "parent_folder": {"id": str(test.folder.id), "str": test.folder.name},
                "content_type": FOLDER_CONTENT_TYPE,
            },
            base_count=-1,
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_create_folders(self, test):
        """test to create folders with the API with authentication

        Community domains are created at the top level, so creating one is a
        Global-scoped action: a role whose permissions are confined to a single domain
        cannot add a sibling of that domain. This is asserted directly rather than
        through `EndpointTestsQueries`, whose matrix treats the "Global" scope as
        reachable by everyone — true for reads, not for writes at the root.
        """
        root = Folder.get_root_folder()
        response = test.client.post(
            "/api/folders/",
            {"name": FOLDER_NAME, "description": FOLDER_DESCRIPTION},
            format="json",
        )

        group = GROUPS_PERMISSIONS[test.user_group]
        may_create = "add_folder" in group["perms"] and group["folder"] == "Global"

        if may_create:
            assert response.status_code == status.HTTP_201_CREATED
            # Asserted against the stored row rather than the response body: a create
            # is rendered by the *write* serializer, whose shape differs from the read
            # one (bare UUID for parent_folder, raw code for content_type).
            created = Folder.objects.get(name=FOLDER_NAME)
            assert created.parent_folder_id == root.id
            assert created.content_type == Folder.ContentType.DOMAIN
        else:
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert not Folder.objects.filter(name=FOLDER_NAME).exists()

    def test_create_subfolder_requires_pro(self, test):
        """Nesting a domain under another is refused by the community serializer.

        Permission is still resolved first, so this only asserts the gate for callers
        who hold add permission on the destination; everyone else is denied earlier and
        for the usual reason.
        """
        response = test.client.post(
            "/api/folders/",
            {
                "name": FOLDER_NAME,
                "description": FOLDER_DESCRIPTION,
                "parent_folder": str(test.folder.id),
            },
            format="json",
        )

        assert response.status_code in (400, 403, 404), (
            "nesting a domain must never succeed in the community edition"
        )
        if response.status_code == 400:
            assert response.json()["parent_folder"] == ["subDomainsRequirePro"]
        assert not Folder.objects.filter(
            name=FOLDER_NAME, parent_folder=test.folder
        ).exists()

    def test_update_folders(self, test):
        """test to update folders with the API with authentication"""

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Folders",
            Folder,
            {
                "name": FOLDER_NAME,
                "description": FOLDER_DESCRIPTION,
                "parent_folder": test.folder,
            },
            {
                "name": "new " + FOLDER_NAME,
                "description": "new " + FOLDER_DESCRIPTION,
                "parent_folder": str(test.folder.id),
            },
            {
                "parent_folder": {"id": str(test.folder.id), "str": test.folder.name},
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_delete_folders(self, test):
        """test to delete folders with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Folders",
            Folder,
            {
                "name": FOLDER_NAME,
                "parent_folder": test.folder,
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )
