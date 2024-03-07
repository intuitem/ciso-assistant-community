import pytest
from rest_framework.test import APIClient
from core.models import ReferenceControl, AppliedControl
from iam.models import Folder

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries

# Generic applied control data for tests
APPLIED_CONTROL_NAME = "Test Applied Control"
APPLIED_CONTROL_DESCRIPTION = "Test Description"
APPLIED_CONTROL_CATEGORY = ("technical", "Technical")
APPLIED_CONTROL_CATEGORY2 = ("process", "Process")
APPLIED_CONTROL_STATUS = ("planned", "Planned")
APPLIED_CONTROL_STATUS2 = ("active", "Active")
APPLIED_CONTROL_EFFORT = ("L", "Large")
APPLIED_CONTROL_EFFORT2 = ("M", "Medium")
APPLIED_CONTROL_LINK = "https://example.com"
APPLIED_CONTROL_ETA = "2024-01-01"


@pytest.mark.django_db
class TestAppliedControlsUnauthenticated:
    """Perform tests on Applied Controls API endpoint without authentication"""

    client = APIClient()

    def test_get_applied_controls(self):
        """test to get applied controls from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_applied_controls(self):
        """test to create applied controls with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_applied_controls(self):
        """test to update applied controls with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + APPLIED_CONTROL_NAME,
                "description": "new " + APPLIED_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test2").id,
            },
        )

    def test_delete_applied_controls(self):
        """test to delete applied controls with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
class TestAppliedControlsAuthenticated:
    """Perform tests on Applied Controls API endpoint with authentication"""

    def test_get_applied_controls(self, test):
        """test to get applied controls from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "category": APPLIED_CONTROL_CATEGORY[0],
                "status": APPLIED_CONTROL_STATUS[0],
                "link": APPLIED_CONTROL_LINK,
                "eta": APPLIED_CONTROL_ETA,
                "effort": APPLIED_CONTROL_EFFORT[0],
                "folder": test.folder,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "reference_control": None,
                "category": APPLIED_CONTROL_CATEGORY[1],
                "status": APPLIED_CONTROL_STATUS[1],
                "effort": APPLIED_CONTROL_EFFORT[1],
            },
            user_group=test.user_group,
        )

    def test_create_applied_controls(self, test):
        """test to create applied controls with the API with authentication"""

        reference_control = ReferenceControl.objects.create(
            name="test", typical_evidence={}, folder=Folder.objects.create(name="test2")
        )

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "category": APPLIED_CONTROL_CATEGORY[0],
                "status": APPLIED_CONTROL_STATUS[0],
                "link": APPLIED_CONTROL_LINK,
                "eta": APPLIED_CONTROL_ETA,
                "effort": APPLIED_CONTROL_EFFORT[0],
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "category": APPLIED_CONTROL_CATEGORY[1],
                "status": APPLIED_CONTROL_STATUS[1],
                "effort": APPLIED_CONTROL_EFFORT[1],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_applied_controls(self, test):
        """test to update applied controls with the API with authentication"""

        folder = Folder.objects.create(name="test2")
        reference_control = ReferenceControl.objects.create(
            name="test", typical_evidence={}, folder=folder
        )

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "category": APPLIED_CONTROL_CATEGORY[0],
                "status": APPLIED_CONTROL_STATUS[0],
                "link": APPLIED_CONTROL_LINK,
                "eta": APPLIED_CONTROL_ETA,
                "effort": APPLIED_CONTROL_EFFORT[0],
                "folder": test.folder,
            },
            {
                "name": "new " + APPLIED_CONTROL_NAME,
                "description": "new " + APPLIED_CONTROL_DESCRIPTION,
                "category": APPLIED_CONTROL_CATEGORY2[0],
                "status": APPLIED_CONTROL_STATUS2[0],
                "link": "new " + APPLIED_CONTROL_LINK,
                "eta": "2025-01-01",
                "effort": APPLIED_CONTROL_EFFORT2[0],
                "folder": str(folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "category": APPLIED_CONTROL_CATEGORY[1],
                "status": APPLIED_CONTROL_STATUS[1],
                "effort": APPLIED_CONTROL_EFFORT[1],
            },
            user_group=test.user_group,
        )

    def test_delete_applied_controls(self, test):
        """test to delete applied controls with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "folder": test.folder,
            },
            user_group=test.user_group,
        )

    def test_get_effort_choices(self, test):
        """test to get applied controls effort choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Applied controls",
            "effort",
            AppliedControl.EFFORT,
            user_group=test.user_group,
        )

    def test_get_status_choices(self, test):
        """test to get applied controls status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Applied controls",
            "status",
            AppliedControl.Status.choices,
            user_group=test.user_group,
        )

    def test_get_type_choices(self, test):
        """test to get applied controls type choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Applied controls",
            "category",
            AppliedControl.CATEGORY,
            user_group=test.user_group,
        )
