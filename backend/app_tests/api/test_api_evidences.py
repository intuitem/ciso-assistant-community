from os import path
import pytest
from rest_framework.test import APIClient
from core.models import SecurityMeasure
from core.models import Evidence
from iam.models import Folder

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries

# Generic evidence data for tests
EVIDENCE_NAME = "Test Evidence"
EVIDENCE_DESCRIPTION = "Test Description"
EVIDENCE_LINK = "https://example.com"
EVIDENCE_ATTACHMENT = "test_image.jpg"


@pytest.mark.django_db
class TestEvidencesUnauthenticated:
    """Perform tests on Evidences API endpoint without authentication"""

    client = APIClient()

    def test_get_evidences(self):
        """test to get evidences from the API without authentication"""

        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.get_object(
            self.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "folder": folder,
                "security_measures": [
                    SecurityMeasure.objects.create(name="test", folder=folder)
                ],
            },
        )

    def test_create_evidences(self):
        """test to create evidences with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Evidences",
            Evidence,
            {"name": EVIDENCE_NAME, "folder": Folder.objects.create(name="test").id},
        )

    def test_update_evidences(self):
        """test to update evidences with the API without authentication"""

        folder = Folder.objects.create(name="test")
        folder2 = Folder.objects.create(name="test2")

        EndpointTestsQueries.update_object(
            self.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "folder": folder,
                "security_measures": [
                    SecurityMeasure.objects.create(name="test", folder=folder)
                ],
            },
            {
                "name": "new " + EVIDENCE_NAME,
                "folder": str(folder2.id),
            },
        )

    def test_delete_evidences(self):
        """test to delete evidences with the API without authentication"""

        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.delete_object(
            self.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "folder": folder,
                "security_measures": [
                    SecurityMeasure.objects.create(name="test", folder=folder)
                ],
            },
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "test",
    GROUPS_PERMISSIONS.keys(),
    ids=[GROUPS_PERMISSIONS[key]["name"] for key in GROUPS_PERMISSIONS.keys()],
    indirect=True,
)
class TestEvidencesAuthenticated:
    """Perform tests on Evidences API endpoint with authentication"""

    def test_get_evidences(self, test):
        """test to get evidences from the API with authentication"""

        security_measure = SecurityMeasure.objects.create(
            name="test", folder=test.folder
        )

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "description": EVIDENCE_DESCRIPTION,
                "link": EVIDENCE_LINK,
                "folder": test.folder,
                "security_measures": [security_measure],
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "security_measures": [
                    {
                        "id": str(security_measure.id),
                        "str": security_measure.name,
                    }
                ],
            },
            user_group=test.user_group,
        )

    def test_create_evidences(self, test):
        """test to create evidences with the API with authentication"""

        security_measure = SecurityMeasure.objects.create(
            name="test", folder=test.folder
        )

        with open(
            path.join(path.dirname(path.dirname(__file__)), EVIDENCE_ATTACHMENT), "rb"
        ) as file:
            EndpointTestsQueries.Auth.create_object(
                test.client,
                "Evidences",
                Evidence,
                {
                    "name": EVIDENCE_NAME,
                    "description": EVIDENCE_DESCRIPTION,
                    "link": EVIDENCE_LINK,
                    "folder": str(test.folder.id),
                    "security_measures": [str(security_measure.id)],
                    "attachment": file,
                },
                {
                    "folder": {"id": str(test.folder.id), "str": test.folder.name},
                    "security_measures": [
                        {
                            "id": str(security_measure.id),
                            "str": security_measure.name,
                        }
                    ],
                    "attachment": EVIDENCE_ATTACHMENT,
                },
                query_format="multipart",
                user_group=test.user_group,
            )

    def test_update_evidences(self, test):
        """test to update evidences with the API with authentication"""

        folder = Folder.objects.create(name="test2")
        security_measure = SecurityMeasure.objects.create(
            name="test", folder=test.folder
        )
        security_measure2 = SecurityMeasure.objects.create(name="test2", folder=folder)

        with open(
            path.join(path.dirname(path.dirname(__file__)), EVIDENCE_ATTACHMENT), "rb"
        ) as file:
            EndpointTestsQueries.Auth.update_object(
                test.client,
                "Evidences",
                Evidence,
                {
                    "name": EVIDENCE_NAME,
                    "description": EVIDENCE_DESCRIPTION,
                    "link": EVIDENCE_LINK,
                    "folder": test.folder,
                    "security_measures": [security_measure],
                },
                {
                    "name": "new " + EVIDENCE_NAME,
                    "description": "new " + EVIDENCE_DESCRIPTION,
                    "link": EVIDENCE_LINK + "/new",
                    "folder": str(folder.id),
                    "security_measures": [str(security_measure2.id)],
                    "attachment": file,
                },
                {
                    "folder": {"id": str(test.folder.id), "str": test.folder.name},
                    "security_measures": [
                        {
                            "id": str(security_measure.id),
                            "str": security_measure.name,
                        }
                    ],
                },
                {
                    "attachment": EVIDENCE_ATTACHMENT,
                },
                query_format="multipart",
                user_group=test.user_group,
            )

    def test_delete_evidences(self, test):
        """test to delete evidences with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Evidences",
            Evidence,
            {
                "name": EVIDENCE_NAME,
                "folder": test.folder,
                "security_measures": [
                    SecurityMeasure.objects.create(name="test", folder=test.folder)
                ],
            },
            user_group=test.user_group,
        )
