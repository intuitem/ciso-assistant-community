import pytest
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Perimeter
from iam.models import Folder

from test_utils import EndpointTestsQueries, EndpointTestsUtils

# Generic perimeter data for tests
PERIMETER_NAME = "Test Perimeter"
PERIMETER_DESCRIPTION = "Test Description"
PERIMETER_STATUS = ("in_prod", "Production")
PERIMETER_REFERENCE = "test:perimter"


@pytest.mark.django_db
class TestPerimetersUnauthenticated:
    """Perform tests on Perimeters API endpoint without authentication"""

    client = APIClient()

    def test_get_perimeters(self):
        """test to get perimeters from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Perimeters",
            Perimeter,
            {
                "name": PERIMETER_NAME,
                "description": PERIMETER_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_perimeters(self):
        """test to create perimeters with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Perimeters",
            Perimeter,
            {
                "name": PERIMETER_NAME,
                "description": PERIMETER_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_perimeters(self):
        """test to update perimeters with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Perimeters",
            Perimeter,
            {
                "name": PERIMETER_NAME,
                "description": PERIMETER_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + PERIMETER_NAME,
                "description": "new " + PERIMETER_DESCRIPTION,
            },
        )

    def test_delete_perimeters(self):
        """test to delete perimeters with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Perimeters",
            Perimeter,
            {"name": PERIMETER_NAME, "folder": Folder.objects.create(name="test")},
        )


@pytest.mark.django_db
class TestPerimetersAuthenticated:
    """Perform tests on Perimeters API endpoint with authentication"""

    def test_get_perimeters(self, test):
        """test to get perimeters from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Perimeters",
            Perimeter,
            {
                "name": PERIMETER_NAME,
                "description": PERIMETER_DESCRIPTION,
                "folder": test.folder,
                "ref_id": PERIMETER_REFERENCE,
                "lc_status": PERIMETER_STATUS[0],
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "lc_status": PERIMETER_STATUS[1],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_create_perimeters(self, test):
        """test to create perimeters with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Perimeters",
            Perimeter,
            {
                "name": PERIMETER_NAME,
                "description": PERIMETER_DESCRIPTION,
                "folder": str(test.folder.id),
                "ref_id": PERIMETER_REFERENCE,
                "lc_status": PERIMETER_STATUS[0],
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "lc_status": PERIMETER_STATUS[1],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_perimeters(self, test):
        """test to update perimeters with the API with authentication"""

        status = ("in_dev", "Development")

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Perimeters",
            Perimeter,
            {
                "name": PERIMETER_NAME,
                "description": PERIMETER_DESCRIPTION,
                "folder": test.folder,
                "ref_id": PERIMETER_REFERENCE,
                "lc_status": PERIMETER_STATUS[0],
            },
            {
                "name": "new " + PERIMETER_NAME,
                "description": "new " + PERIMETER_DESCRIPTION,
                "ref_id": "new " + PERIMETER_REFERENCE,
                "lc_status": status[0],
            },
            {
                "folder": {"id": str(test.folder.id), "str": str(test.folder)},
                "lc_status": PERIMETER_STATUS[1],
            },
            test_params={
                "folder": str(test.folder.id),
            },
            user_group=test.user_group,
        )

    def test_update_perimeters_folder_forbidden(self, authenticated_client):
        """test to ensure perimeter folder cannot be updated with the API"""

        folder = Folder.objects.create(name="test")
        perimeter = Perimeter.objects.create(
            name=PERIMETER_NAME,
            description=PERIMETER_DESCRIPTION,
            folder=folder,
            ref_id=PERIMETER_REFERENCE,
            lc_status=PERIMETER_STATUS[0],
        )
        new_folder = Folder.objects.create(name="test2")
        url = (
            EndpointTestsUtils.get_endpoint_url("Perimeters") + str(perimeter.id) + "/"
        )
        response = authenticated_client.patch(
            url, {"folder": str(new_folder.id)}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        perimeter.refresh_from_db()
        assert perimeter.folder_id == folder.id

    def test_delete_perimeters(self, test):
        """test to delete perimeters with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Perimeters",
            Perimeter,
            {"name": PERIMETER_NAME, "folder": test.folder},
            user_group=test.user_group,
        )

    def test_get_status_choices(self, test):
        """test to get perimeters status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client, "Perimeters", "lc_status", Perimeter.PRJ_LC_STATUS
        )
