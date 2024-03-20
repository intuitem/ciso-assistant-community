import pytest
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_400_BAD_REQUEST
from rest_framework.test import APIClient
from core.models import Threat
from iam.models import Folder

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries

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
                "is_published": True,
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
                "is_published": True,
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

    def test_get_threats(self, test):
        """test to get threats from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "provider": THREAT_PROVIDER,
                "urn": THREAT_URN,
                "is_published": True,
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
            },
            user_group=test.user_group,
            scope="Global",
        )

    def test_create_threats(self, test):
        """test to create threats with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "provider": THREAT_PROVIDER,
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "urn": None,
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_threats_with_urn(self, test):
        """test to update imported threat (with URN) with the API with authentication"""
        folder = Folder.objects.create(name="test2")

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "provider": THREAT_PROVIDER,
                "urn": THREAT_URN,
                "is_published": True,
            },
            {
                "ref_id": "new " + THREAT_REF_ID,
                "name": "new " + THREAT_NAME,
                "description": "new " + THREAT_DESCRIPTION,
                "provider": "new " + THREAT_PROVIDER,
                "urn": THREAT_URN,
                "folder": str(folder.id),
            },
            user_group=test.user_group,
            scope="Global",
            fails=True,
            expected_status=HTTP_403_FORBIDDEN,  # Imported objects cannot be modified
        )

    def test_update_threats(self, test):
        """test to update threats with the API with authentication"""

        folder = Folder.objects.create(name="test2")

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Threats",
            Threat,
            {
                "ref_id": THREAT_REF_ID,
                "name": THREAT_NAME,
                "description": THREAT_DESCRIPTION,
                "provider": THREAT_PROVIDER,
                "folder": test.folder,
            },
            {
                "ref_id": "new " + THREAT_REF_ID,
                "name": "new " + THREAT_NAME,
                "description": "new " + THREAT_DESCRIPTION,
                "provider": "new " + THREAT_PROVIDER,
                "folder": str(folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
            },
            user_group=test.user_group,
        )

    def test_delete_threats(self, test):
        """test to delete threats with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Threats",
            Threat,
            {"name": THREAT_NAME, "folder": test.folder},
            user_group=test.user_group,
            scope=str(test.folder),
        )
