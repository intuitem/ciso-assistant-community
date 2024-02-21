import pytest
from rest_framework.test import APIClient
from core.models import Project
from iam.models import Folder, User, UserGroup

from test_vars import GROUPS_PERMISSIONS
from test_api import EndpointTestsQueries, EndpointTestsUtils

# Generic project data for tests
PROJECT_NAME = "Test Project"
PROJECT_DESCRIPTION = "Test Description"
PROJECT_STATUS = ("in_prod", "Production")
PROJECT_REFERENCE = "test:project"


@pytest.mark.django_db
class TestProjectsUnauthenticated:
    """Perform tests on Projects API endpoint without authentication"""

    client = APIClient()

    def test_get_projects(self):
        """test to get projects from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Projects",
            Project,
            {
                "name": PROJECT_NAME,
                "description": PROJECT_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_projects(self):
        """test to create projects with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Projects",
            Project,
            {
                "name": PROJECT_NAME,
                "description": PROJECT_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_projects(self):
        """test to update projects with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Projects",
            Project,
            {
                "name": PROJECT_NAME,
                "description": PROJECT_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + PROJECT_NAME,
                "description": "new " + PROJECT_DESCRIPTION,
            },
        )

    def test_delete_projects(self):
        """test to delete projects with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Projects",
            Project,
            {"name": PROJECT_NAME, "folder": Folder.objects.create(name="test")},
        )


@pytest.mark.django_db
@pytest.mark.parametrize("test", GROUPS_PERMISSIONS.keys(), ids=[GROUPS_PERMISSIONS[key]["name"] for key in GROUPS_PERMISSIONS.keys()], indirect=True)
class TestProjectsAuthenticated:
    """Perform tests on Projects API endpoint with authentication"""

    def test_get_projects(self, test):
        """test to get projects from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Projects",
            Project,
            {
                "name": PROJECT_NAME,
                "description": PROJECT_DESCRIPTION,
                "folder": test.folder,
                "internal_reference": PROJECT_REFERENCE,
                "lc_status": PROJECT_STATUS[0],
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "lc_status": PROJECT_STATUS[1],
            },
        )
        

    def test_create_projects(self, authenticated_client, test):
        """test to create projects with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            authenticated_client,
            "Projects",
            Project,
            {
                "name": PROJECT_NAME,
                "description": PROJECT_DESCRIPTION,
                "folder": str(Folder.get_root_folder().id),
                "internal_reference": PROJECT_REFERENCE,
                "lc_status": PROJECT_STATUS[0],
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
                "lc_status": PROJECT_STATUS[1],
            },
        )

    def test_update_projects(self, authenticated_client, test):
        """test to update projects with the API with authentication"""

        status = ("in_dev", "Development")
        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.Auth.update_object(
            authenticated_client,
            "Projects",
            Project,
            {
                "name": PROJECT_NAME,
                "description": PROJECT_DESCRIPTION,
                "folder": Folder.get_root_folder(),
                "internal_reference": PROJECT_REFERENCE,
                "lc_status": PROJECT_STATUS[0],
            },
            {
                "name": "new " + PROJECT_NAME,
                "description": "new " + PROJECT_DESCRIPTION,
                "folder": str(folder.id),
                "internal_reference": "new " + PROJECT_REFERENCE,
                "lc_status": status[0],
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
                "lc_status": PROJECT_STATUS[1],
            },
        )

    def test_delete_projects(self, authenticated_client, test):
        """test to delete projects with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            authenticated_client,
            "Projects",
            Project,
            {"name": PROJECT_NAME, "folder": Folder.get_root_folder()},
        )

    def test_get_status_choices(self, authenticated_client, test):
        """test to get projects status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            authenticated_client, "Projects", "lc_status", Project.PRJ_LC_STATUS
        )
