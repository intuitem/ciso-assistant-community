import pytest
from rest_framework.test import APIClient
from core.models import SecurityFunction, SecurityMeasure
from iam.models import Folder

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
class TestSecurityMeasuresAuthenticated:
    """Perform tests on Security Measures API endpoint with authentication"""

    def test_get_security_measures(self, authenticated_client):
        """test to get security measures from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            authenticated_client,
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
                "folder": Folder.get_root_folder(),
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
                "security_function": None,
                "category": SECURITY_MEASURE_CATEGORY[1],
                "status": SECURITY_MEASURE_STATUS[1],
                "effort": SECURITY_MEASURE_EFFORT[1],
            },
        )

    def test_create_security_measures(self, authenticated_client):
        """test to create security measures with the API with authentication"""

        security_function = SecurityFunction.objects.create(
            name="test", typical_evidence={}, folder=Folder.objects.create(name="test")
        )

        EndpointTestsQueries.Auth.create_object(
            authenticated_client,
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
                "folder": str(Folder.get_root_folder().id),
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
                "category": SECURITY_MEASURE_CATEGORY[1],
                "status": SECURITY_MEASURE_STATUS[1],
                "effort": SECURITY_MEASURE_EFFORT[1],
            },
        )

    def test_update_security_measures(self, authenticated_client):
        """test to update security measures with the API with authentication"""

        folder = Folder.objects.create(name="test")
        security_function = SecurityFunction.objects.create(
            name="test", typical_evidence={}, folder=folder
        )

        EndpointTestsQueries.Auth.update_object(
            authenticated_client,
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
                "folder": Folder.get_root_folder(),
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
                "folder": {"str": Folder.get_root_folder().name},
                "category": SECURITY_MEASURE_CATEGORY[1],
                "status": SECURITY_MEASURE_STATUS[1],
                "effort": SECURITY_MEASURE_EFFORT[1],
            },
        )

    def test_delete_security_measures(self, authenticated_client):
        """test to delete security measures with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            authenticated_client,
            "Security measures",
            SecurityMeasure,
            {
                "name": SECURITY_MEASURE_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_get_effort_choices(self, authenticated_client):
        """test to get security measures effort choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            authenticated_client, "Security measures", "effort", SecurityMeasure.EFFORT
        )

    def test_get_status_choices(self, authenticated_client):
        """test to get security measures status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            authenticated_client,
            "Security measures",
            "status",
            SecurityMeasure.Status.choices,
        )

    def test_get_type_choices(self, authenticated_client):
        """test to get security measures type choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            authenticated_client,
            "Security measures",
            "category",
            SecurityMeasure.CATEGORY,
        )
