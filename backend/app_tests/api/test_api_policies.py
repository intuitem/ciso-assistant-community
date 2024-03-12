import pytest
from rest_framework.test import APIClient
from core.models import Policy
from iam.models import Folder

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries

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
            "Policies",
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
            "Policies",
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
            "Policies",
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
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
class TestPolicysAuthenticated:
    """Perform tests on policies API endpoint with authentication"""

    def test_get_policies(self, test):
        """test to get policies from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "status": POLICY_STATUS[0],
                "link": POLICY_LINK,
                "eta": POLICY_ETA,
                "effort": POLICY_EFFORT[0],
                "folder": test.folder,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "reference_control": None,
                "status": POLICY_STATUS[1],
                "effort": POLICY_EFFORT[1],
            },
            user_group=test.user_group,
        )

    def test_create_policies(self, test):
        """test to create policies with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "status": POLICY_STATUS[0],
                "link": POLICY_LINK,
                "eta": POLICY_ETA,
                "effort": POLICY_EFFORT[0],
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "status": POLICY_STATUS[1],
                "effort": POLICY_EFFORT[1],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_policies(self, test):
        """test to update policies with the API with authentication"""

        folder = Folder.objects.create(name="test2")

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "status": POLICY_STATUS[0],
                "link": POLICY_LINK,
                "eta": POLICY_ETA,
                "effort": POLICY_EFFORT[0],
                "folder": test.folder,
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
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "status": POLICY_STATUS[1],
                "effort": POLICY_EFFORT[1],
            },
            user_group=test.user_group,
        )

    def test_delete_policies(self, test):
        """test to delete policies with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "folder": test.folder,
            },
            user_group=test.user_group,
        )

    def test_get_category_choices(self, test):
        """test to get policies category choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Policies",
            "category",
            Policy.CATEGORY,
            user_group=test.user_group,
        )

    def test_get_effort_choices(self, test):
        """test to get policies effort choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client, "Policies", "effort", Policy.EFFORT, user_group=test.user_group
        )

    def test_get_status_choices(self, test):
        """test to get policies status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Policies",
            "status",
            Policy.Status.choices,
            user_group=test.user_group,
        )
