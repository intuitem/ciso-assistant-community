import pytest
from rest_framework.status import HTTP_403_FORBIDDEN, HTTP_400_BAD_REQUEST
from rest_framework.test import APIClient
from core.models import ReferenceControl
from iam.models import Folder

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries

# Generic reference control data for tests
REFERENCE_CONTROL_REF_ID = "Test-Reference-Control"
REFERENCE_CONTROL_NAME = "Test Reference Control"
REFERENCE_CONTROL_DESCRIPTION = "Test Description"
REFERENCE_CONTROL_PROVIDER = "Test Provider"
REFERENCE_CONTROL_URN = "test:reference-control:1.0"


@pytest.mark.django_db
class TestReferenceControlsUnauthenticated:
    """Perform tests on Reference Controls API endpoint without authentication"""

    client = APIClient()

    def test_get_reference_controls(self):
        """test to get reference controls from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Reference controls",
            ReferenceControl,
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "description": REFERENCE_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
                "is_published": True,
            },
        )

    def test_create_reference_controls(self):
        """test to create reference controls with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Reference controls",
            ReferenceControl,
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "description": REFERENCE_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_reference_controls(self):
        """test to update reference controls with the API without authentication"""
        EndpointTestsQueries.update_object(
            self.client,
            "Reference controls",
            ReferenceControl,
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "description": REFERENCE_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
                "is_published": True,
            },
            {
                "ref_id": "new " + REFERENCE_CONTROL_REF_ID,
                "name": "new " + REFERENCE_CONTROL_NAME,
                "description": "new " + REFERENCE_CONTROL_DESCRIPTION,
            },
        )

    def test_delete_reference_controls(self):
        """test to delete reference controls with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Reference controls",
            ReferenceControl,
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "folder": Folder.objects.create(name="test"),
                "is_published": True,
            },
        )


@pytest.mark.django_db
class TestReferenceControlsAuthenticated:
    """Perform tests on Reference Controls API endpoint with authentication"""

    def test_get_reference_controls(self, test):
        """test to get reference controls from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Reference controls",
            ReferenceControl,
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "description": REFERENCE_CONTROL_DESCRIPTION,
                "urn": REFERENCE_CONTROL_URN,
                "provider": REFERENCE_CONTROL_PROVIDER,
                "is_published": True,
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
            },
            user_group=test.user_group,
            scope="Global",
        )

    def test_create_reference_controls(self, test):
        """test to create reference controls with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Reference controls",
            ReferenceControl,
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "description": REFERENCE_CONTROL_DESCRIPTION,
                "urn": REFERENCE_CONTROL_URN,
                "provider": REFERENCE_CONTROL_PROVIDER,
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_reference_control_with_urn(self, test):
        """test to update an imported reference control (with a URN) with the API with authentication"""
        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Reference controls",
            ReferenceControl,
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "description": REFERENCE_CONTROL_DESCRIPTION,
                "urn": REFERENCE_CONTROL_URN,
                "provider": REFERENCE_CONTROL_PROVIDER,
                "is_published": True,
            },
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "description": "new " + REFERENCE_CONTROL_DESCRIPTION,
                "urn": REFERENCE_CONTROL_URN,
                "provider": "new " + REFERENCE_CONTROL_PROVIDER,
            },
            {
                "folder": {"str": Folder.get_root_folder().name},
            },
            user_group=test.user_group,
            scope="Global",
            fails=True,
            expected_status=HTTP_403_FORBIDDEN,  # Imported objects cannot be updated
        )

    def test_update_reference_control(self, test):
        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Reference controls",
            ReferenceControl,
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "description": REFERENCE_CONTROL_DESCRIPTION,
                "provider": REFERENCE_CONTROL_PROVIDER,
                "folder": test.folder,
            },
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "description": "new " + REFERENCE_CONTROL_DESCRIPTION,
                "provider": "new " + REFERENCE_CONTROL_PROVIDER,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
            },
            {"folder": str(test.folder.id)},
            user_group=test.user_group,
        )

    def test_delete_reference_controls(self, test):
        """test to delete reference controls with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Reference controls",
            ReferenceControl,
            {
                "ref_id": REFERENCE_CONTROL_REF_ID,
                "name": REFERENCE_CONTROL_NAME,
                "folder": test.folder,
            },
            user_group=test.user_group,
        )
