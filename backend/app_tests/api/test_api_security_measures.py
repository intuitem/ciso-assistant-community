import pytest
from rest_framework.test import APIClient
from core.models import SecurityFunction, SecurityMeasure
from iam.models import Folder

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries

# Generic security measure data for tests
SECURITY_MEASURE_NAME = "Test Security Measure"
SECURITY_MEASURE_DESCRIPTION = "Test Description"
SECURITY_MEASURE_CATEGORY = ("technical", "Technical")
SECURITY_MEASURE_CATEGORY2 = ("process", "Process")
SECURITY_MEASURE_STATUS = ("planned", "Planned")
SECURITY_MEASURE_STATUS2 = ("active", "Active")
SECURITY_MEASURE_EFFORT = ("L", "Large")
SECURITY_MEASURE_EFFORT2 = ("M", "Medium")
SECURITY_MEASURE_LINK = "https://example.com"
SECURITY_MEASURE_ETA = "2024-01-01"


@pytest.mark.django_db
class TestSecurityMeasuresUnauthenticated:
    """Perform tests on Security Measures API endpoint without authentication"""

    client = APIClient()

    def test_get_security_measures(self):
        """test to get security measures from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Security measures",
            SecurityMeasure,
            {
                "name": SECURITY_MEASURE_NAME,
                "description": SECURITY_MEASURE_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_security_measures(self):
        """test to create security measures with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Security measures",
            SecurityMeasure,
            {
                "name": SECURITY_MEASURE_NAME,
                "description": SECURITY_MEASURE_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_security_measures(self):
        """test to update security measures with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Security measures",
            SecurityMeasure,
            {
                "name": SECURITY_MEASURE_NAME,
                "description": SECURITY_MEASURE_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + SECURITY_MEASURE_NAME,
                "description": "new " + SECURITY_MEASURE_DESCRIPTION,
                "folder": Folder.objects.create(name="test2").id,
            },
        )

    def test_delete_security_measures(self):
        """test to delete security measures with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Security measures",
            SecurityMeasure,
            {
                "name": SECURITY_MEASURE_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
@pytest.mark.parametrize("test", GROUPS_PERMISSIONS.keys(), ids=[GROUPS_PERMISSIONS[key]["name"] for key in GROUPS_PERMISSIONS.keys()], indirect=True)
class TestSecurityMeasuresAuthenticated:
    """Perform tests on Security Measures API endpoint with authentication"""

    def test_get_security_measures(self, test):
        """test to get security measures from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Security measures",
            SecurityMeasure,
            {
                "name": SECURITY_MEASURE_NAME,
                "description": SECURITY_MEASURE_DESCRIPTION,
                "category": SECURITY_MEASURE_CATEGORY[0],
                "status": SECURITY_MEASURE_STATUS[0],
                "link": SECURITY_MEASURE_LINK,
                "eta": SECURITY_MEASURE_ETA,
                "effort": SECURITY_MEASURE_EFFORT[0],
                "folder": test.folder,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "security_function": None,
                "category": SECURITY_MEASURE_CATEGORY[1],
                "status": SECURITY_MEASURE_STATUS[1],
                "effort": SECURITY_MEASURE_EFFORT[1],
            },
            user_group=test.user_group,
        )

    def test_create_security_measures(self, test):
        """test to create security measures with the API with authentication"""

        security_function = SecurityFunction.objects.create(
            name="test", typical_evidence={}, folder=Folder.objects.create(name="test2")
        )

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Security measures",
            SecurityMeasure,
            {
                "name": SECURITY_MEASURE_NAME,
                "description": SECURITY_MEASURE_DESCRIPTION,
                "category": SECURITY_MEASURE_CATEGORY[0],
                "status": SECURITY_MEASURE_STATUS[0],
                "link": SECURITY_MEASURE_LINK,
                "eta": SECURITY_MEASURE_ETA,
                "effort": SECURITY_MEASURE_EFFORT[0],
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "category": SECURITY_MEASURE_CATEGORY[1],
                "status": SECURITY_MEASURE_STATUS[1],
                "effort": SECURITY_MEASURE_EFFORT[1],
            },
            user_group=test.user_group,
        )

    def test_update_security_measures(self, test):
        """test to update security measures with the API with authentication"""

        folder = Folder.objects.create(name="test2")
        security_function = SecurityFunction.objects.create(
            name="test", typical_evidence={}, folder=folder
        )

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Security measures",
            SecurityMeasure,
            {
                "name": SECURITY_MEASURE_NAME,
                "description": SECURITY_MEASURE_DESCRIPTION,
                "category": SECURITY_MEASURE_CATEGORY[0],
                "status": SECURITY_MEASURE_STATUS[0],
                "link": SECURITY_MEASURE_LINK,
                "eta": SECURITY_MEASURE_ETA,
                "effort": SECURITY_MEASURE_EFFORT[0],
                "folder": test.folder,
            },
            {
                "name": "new " + SECURITY_MEASURE_NAME,
                "description": "new " + SECURITY_MEASURE_DESCRIPTION,
                "category": SECURITY_MEASURE_CATEGORY2[0],
                "status": SECURITY_MEASURE_STATUS2[0],
                "link": "new " + SECURITY_MEASURE_LINK,
                "eta": "2025-01-01",
                "effort": SECURITY_MEASURE_EFFORT2[0],
                "folder": str(folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "category": SECURITY_MEASURE_CATEGORY[1],
                "status": SECURITY_MEASURE_STATUS[1],
                "effort": SECURITY_MEASURE_EFFORT[1],
            },
            user_group=test.user_group,
        )

    def test_delete_security_measures(self, test):
        """test to delete security measures with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Security measures",
            SecurityMeasure,
            {
                "name": SECURITY_MEASURE_NAME,
                "folder": test.folder,
            },
            user_group=test.user_group,
        )

    def test_get_effort_choices(self, test):
        """test to get security measures effort choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client, 
            "Security measures", 
            "effort", 
            SecurityMeasure.EFFORT, 
            user_group=test.user_group
        )

    def test_get_status_choices(self, test):
        """test to get security measures status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Security measures",
            "status",
            SecurityMeasure.Status.choices,
            user_group=test.user_group,
        )

    def test_get_type_choices(self, test):
        """test to get security measures type choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Security measures",
            "category",
            SecurityMeasure.CATEGORY,
            user_group=test.user_group,
        )
