import pytest
from rest_framework.test import APIClient
from core.models import Framework
from core.models import RiskMatrix
from iam.models import Folder

from test_utils import EndpointTestsQueries, EndpointTestsUtils


@pytest.mark.django_db
class TestLibrariesUnauthenticated:
    """Perform tests on Libraries API endpoint without authentication"""

    client = APIClient()

    def test_get_libraries(self):
        """test to get libraries from the API without authentication"""

        EndpointTestsQueries.get_object(self.client, "Libraries")

    def test_import_frameworks(self):
        """test to import libraries with the API without authentication"""

        EndpointTestsQueries.import_object(self.client, "Framework")

    def test_delete_frameworks(self, authenticated_client):
        """test to delete libraries with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.delete_object(self.client, "Frameworks", Framework)

    def test_import_risk_matrix(self):
        """test to import libraries with the API without authentication"""

        EndpointTestsQueries.import_object(self.client, "Risk matrix")

    def test_delete_risk_matrix(self, authenticated_client):
        """test to delete libraries with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Risk matrix")
        EndpointTestsQueries.delete_object(self.client, "Risk matrices", RiskMatrix)


@pytest.mark.django_db
class TestLibrariesAuthenticated:
    """Perform tests on Libraries API endpoint with authentication"""

    def test_get_libraries(self, authenticated_client):
        """test to get libraries from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            authenticated_client, "Libraries", base_count=-1
        )

    def test_import_frameworks(self, authenticated_client):
        """test to import frameworks with the API with authentication"""

        # Uses the API endpoint to get library details with the authenticated client
        lib_detail_response = authenticated_client.get(
            EndpointTestsUtils.get_object_urn("Framework")
        ).json()["objects"]["framework"]

        # Asserts that the library is not already imported
        assert (
            Framework.objects.all().count() == 0
        ), "libraries are already imported in the database"
        EndpointTestsQueries.Auth.get_object(authenticated_client, "Frameworks")

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")

        # Uses the API endpoint to assert that the library was properly imported
        assert (
            Framework.objects.all().count() == 1
        ), "frameworks are not correctly imported in the database"
        EndpointTestsQueries.Auth.get_object(
            authenticated_client,
            "Frameworks",
            test_params={
                "name": lib_detail_response["name"],
                "description": lib_detail_response["description"],
                "urn": lib_detail_response["urn"],
                "folder": {"str": Folder.get_root_folder().name},
            },
            base_count=1,
        )

    def test_delete_frameworks(self, authenticated_client):
        """test to delete frameworks with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.Auth.delete_object(
            authenticated_client, "Frameworks", Framework
        )

    def test_import_risk_matrix(self, authenticated_client):
        """test to import risk matrix with the API with authentication"""

        # Uses the API endpoint to get library details with the authenticated client
        lib_detail_response = authenticated_client.get(
            EndpointTestsUtils.get_object_urn("Risk matrix")
        ).json()["objects"]["risk_matrix"][0]

        # Asserts that the library is not already imported
        assert (
            RiskMatrix.objects.all().count() == 0
        ), "libraries are already imported in the database"
        EndpointTestsQueries.Auth.get_object(authenticated_client, "Risk matrices")
        EndpointTestsQueries.Auth.import_object(authenticated_client, "Risk matrix")

        # Uses the API endpoint to assert that the library was properly imported
        assert (
            RiskMatrix.objects.all().count() == 1
        ), "Risk matrices are not correctly imported in the database"
        EndpointTestsQueries.Auth.get_object(
            authenticated_client,
            "Risk matrices",
            test_params={
                "name": lib_detail_response["name"],
                "description": lib_detail_response["description"],
                "urn": lib_detail_response["urn"],
                "folder": {"str": Folder.get_root_folder().name},
                #                                 'json_definition': lib_detail_response  # TODO: restore this test
            },
            base_count=1,
        )

    def test_delete_matrix(self, authenticated_client):
        """test to delete risk matrix with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Risk matrix")
        EndpointTestsQueries.Auth.delete_object(
            authenticated_client, "Risk matrices", RiskMatrix
        )
