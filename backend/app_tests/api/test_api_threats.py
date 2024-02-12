import pytest
from rest_framework.status import HTTP_400_BAD_REQUEST
from rest_framework.test import APIClient
from core.models import Threat
from iam.models import Folder

from test_api import EndpointTestsQueries

# Generic threat data for tests
THREAT_REF_ID = "Test-Threat-ID"
THREAT_NAME = "Test Threat"
THREAT_DESCRIPTION = "Test Description"
THREAT_PROVIDER = "Test Provider"
THREAT_URN = "test:threat:1.0"


@pytest.mark.django_db
class TestThreatsUnauthenticated:
    """Perform tests on Threats API endpoint without authentication"""

    client = APIClient()

    def test_get_threats(self):
        """test to get threats from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_threats(self):
        """test to create threats with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_threats(self):
        """test to update threats with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "provider": THREAT_PROVIDER,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "ref_id": "new " + THREAT_REF_ID,
                "name": "new " + THREAT_NAME,
                "description": "new " + THREAT_DESCRIPTION,
                "provider": "new " + THREAT_PROVIDER,
            },
        )

    def test_delete_threats(self):
        """test to delete threats with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
class TestThreatsAuthenticated:
    """Perform tests on Threats API endpoint with authentication"""

    def test_get_threats(self, authenticated_client):
        """test to get threats from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            authenticated_client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "provider": THREAT_PROVIDER,
                "urn": THREAT_URN,
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
            },
        )

    def test_create_threats(self, authenticated_client):
        """test to create threats with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            authenticated_client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "provider": THREAT_PROVIDER,
                "folder": str(Folder.get_root_folder().id),
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
                "urn": None,
            },
        )

    def test_update_threats_with_url(self, authenticated_client):
        """test to update imported threat (with URN) with the API with authentication"""
        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.Auth.update_object(
            authenticated_client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "provider": THREAT_PROVIDER,
                "urn": THREAT_URN,
            },
            {
                "ref_id": "new " + THREAT_REF_ID,
                "name": "new " + THREAT_NAME,
                "description": "new " + THREAT_DESCRIPTION,
                "provider": "new " + THREAT_PROVIDER,
                "urn": THREAT_URN,
                "folder": str(folder.id),
            },
            fails=True,
            expected_status=HTTP_400_BAD_REQUEST,
        )

    def test_update_threats(self, authenticated_client):
        """test to update threats with the API with authentication"""

        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.Auth.update_object(
            authenticated_client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "provider": THREAT_PROVIDER,
            },
            {
                "ref_id": "new " + THREAT_REF_ID,
                "name": "new " + THREAT_NAME,
                "description": "new " + THREAT_DESCRIPTION,
                "provider": "new " + THREAT_PROVIDER,
                "folder": str(folder.id),
            },
        )

    def test_delete_threats(self, authenticated_client):
        """test to delete threats with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            authenticated_client,
            "Threats",
            Threat,
            {"name": THREAT_NAME, "folder": Folder.objects.create(name="test")},
        )
