import pytest
from rest_framework import status
from rest_framework.test import APIClient
from core.models import SecurityFunction
from iam.models import Folder

from test_api import EndpointTestsQueries

# Generic security function data for tests
SECURITY_FUNCTION_REF_ID = "Test-Security-Function"
SECURITY_FUNCTION_NAME = "Test Security Function"
SECURITY_FUNCTION_DESCRIPTION = "Test Description"
SECURITY_FUNCTION_PROVIDER = "Test Provider"
SECURITY_FUNCTION_URN = "test:security-function:1.0"


@pytest.mark.django_db
class TestSecurityFunctionsUnauthenticated:
    """Perform tests on Security Functions API endpoint without authentication"""

    client = APIClient()

    def test_get_security_functions(self):
        """test to get security functions from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Security functions",
            SecurityFunction,
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "description": SECURITY_FUNCTION_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_security_functions(self):
        """test to create security functions with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Security functions",
            SecurityFunction,
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "description": SECURITY_FUNCTION_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_security_functions(self):
        """test to update security functions with the API without authentication"""
        EndpointTestsQueries.update_object(
            self.client,
            "Security functions",
            SecurityFunction,
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "description": SECURITY_FUNCTION_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "ref_id": "new " + SECURITY_FUNCTION_REF_ID,
                "name": "new " + SECURITY_FUNCTION_NAME,
                "description": "new " + SECURITY_FUNCTION_DESCRIPTION,
            },
        )

    def test_delete_security_functions(self):
        """test to delete security functions with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Security functions",
            SecurityFunction,
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
class TestSecurityFunctionsAuthenticated:
    """Perform tests on Security Functions API endpoint with authentication"""

    def test_get_security_functions(self, authenticated_client):
        """test to get security functions from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            authenticated_client,
            "Security functions",
            SecurityFunction,
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "description": SECURITY_FUNCTION_DESCRIPTION,
                "urn": SECURITY_FUNCTION_URN,
                "provider": SECURITY_FUNCTION_PROVIDER,
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
            },
        )

    def test_create_security_functions(self, authenticated_client):
        """test to create security functions with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            authenticated_client,
            "Security functions",
            SecurityFunction,
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "description": SECURITY_FUNCTION_DESCRIPTION,
                "urn": SECURITY_FUNCTION_URN,
                "provider": SECURITY_FUNCTION_PROVIDER,
                "folder": str(Folder.get_root_folder().id),
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
            },
        )

    def test_update_security_function_with_url(self, authenticated_client):
        """test to update an imported security function (with a URN) with the API with authentication"""
        EndpointTestsQueries.Auth.update_object(
            authenticated_client,
            "Security functions",
            SecurityFunction,
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "description": SECURITY_FUNCTION_DESCRIPTION,
                "urn": SECURITY_FUNCTION_URN,
                "provider": SECURITY_FUNCTION_PROVIDER,
            },
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "description": "new " + SECURITY_FUNCTION_DESCRIPTION,
                "urn": SECURITY_FUNCTION_URN,
                "provider": "new " + SECURITY_FUNCTION_PROVIDER,
                "folder": str(Folder.objects.create(name="test").id),
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
            },
            fails=True,
            expected_status=status.HTTP_400_BAD_REQUEST,
        )

    def test_update_security_function(self, authenticated_client):
        EndpointTestsQueries.Auth.update_object(
            authenticated_client,
            "Security functions",
            SecurityFunction,
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "description": SECURITY_FUNCTION_DESCRIPTION,
                "provider": SECURITY_FUNCTION_PROVIDER,
            },
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "description": "new " + SECURITY_FUNCTION_DESCRIPTION,
                "provider": "new " + SECURITY_FUNCTION_PROVIDER,
                "folder": str(Folder.objects.create(name="test").id),
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
            },
        )

    def test_delete_security_functions(self, authenticated_client):
        """test to delete security functions with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            authenticated_client,
            "Security functions",
            SecurityFunction,
            {
                "ref_id": SECURITY_FUNCTION_REF_ID,
                "name": SECURITY_FUNCTION_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )
