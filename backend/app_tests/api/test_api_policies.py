import pytest
from rest_framework.test import APIClient
from core.models import Policy
from iam.models import Folder

from test_api import EndpointTestsQueries

# Generic policy data for tests
POLICY_NAME = "Test Policy"
POLICY_DESCRIPTION = "Test Description"
POLICY_STATUS = ("planned", "Planned")
POLICY_STATUS2 = ("active", "Active")
POLICY_EFFORT = ("L", "Large")
POLICY_EFFORT2 = ("M", "Medium")
POLICY_LINK = "https://example.com"
POLICY_ETA = "2024-01-01"


@pytest.mark.django_db
class TestPolicysUnauthenticated:
    """Perform tests on policies API endpoint without authentication"""

    client = APIClient()

    def test_get_policies(self):
        """test to get policies from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_policies(self):
        """test to create policies with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_policies(self):
        """test to update policies with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + POLICY_NAME,
                "description": "new " + POLICY_DESCRIPTION,
                "folder": Folder.objects.create(name="test2").id,
            },
        )

    def test_delete_policies(self):
        """test to delete policies with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "policies",
            Policy,
            {
                "name": POLICY_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
class TestPolicysAuthenticated:
    """Perform tests on policies API endpoint with authentication"""

    def test_get_policies(self, authenticated_client):
        """test to get policies from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            authenticated_client,
            "policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "status": POLICY_STATUS[0],
                "link": POLICY_LINK,
                "eta": POLICY_ETA,
                "effort": POLICY_EFFORT[0],
                "folder": Folder.get_root_folder(),
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
                "security_function": None,
                "status": POLICY_STATUS[1],
                "effort": POLICY_EFFORT[1],
            },
        )

    def test_create_policies(self, authenticated_client):
        """test to create policies with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            authenticated_client,
            "policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "status": POLICY_STATUS[0],
                "link": POLICY_LINK,
                "eta": POLICY_ETA,
                "effort": POLICY_EFFORT[0],
                "folder": str(Folder.get_root_folder().id),
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
                "status": POLICY_STATUS[1],
                "effort": POLICY_EFFORT[1],
            },
        )

    def test_update_policies(self, authenticated_client):
        """test to update policies with the API with authentication"""

        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.Auth.update_object(
            authenticated_client,
            "policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "status": POLICY_STATUS[0],
                "link": POLICY_LINK,
                "eta": POLICY_ETA,
                "effort": POLICY_EFFORT[0],
                "folder": Folder.get_root_folder(),
            },
            {
                "name": "new " + POLICY_NAME,
                "description": "new " + POLICY_DESCRIPTION,
                "status": POLICY_STATUS2[0],
                "link": "new " + POLICY_LINK,
                "eta": "2025-01-01",
                "effort": POLICY_EFFORT2[0],
                "folder": str(folder.id),
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
                "status": POLICY_STATUS[1],
                "effort": POLICY_EFFORT[1],
            },
        )

    def test_delete_policies(self, authenticated_client):
        """test to delete policies with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            authenticated_client,
            "policies",
            Policy,
            {
                "name": POLICY_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )
    
    def test_get_category_choices(self, authenticated_client):
        """test to get policies category choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            authenticated_client, "policies", "category", Policy.CATEGORY
        )

    def test_get_effort_choices(self, authenticated_client):
        """test to get policies effort choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            authenticated_client, "policies", "effort", Policy.EFFORT
        )

    def test_get_status_choices(self, authenticated_client):
        """test to get policies status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            authenticated_client,
            "policies",
            "status",
            Policy.Status.choices,
        )
