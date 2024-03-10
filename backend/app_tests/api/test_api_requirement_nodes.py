import pytest
from rest_framework.test import APIClient
from core.models import RequirementNode, Framework
from iam.models import Folder

from test_vars import GROUPS_PERMISSIONS
from test_utils import EndpointTestsQueries, EndpointTestsUtils

# Generic requirement data for tests
REQUIREMENT_NODE_NAME = "Test Requirement Node"
REQUIREMENT_NODE_DESCRIPTION = "Test Description"
REQUIREMENT_NODE_URN = "urn:test:req_node.t:1"
REQUIREMENT_NODE_PARENT_URN = "urn:test:req_node.t"
REQUIREMENT_NODE_ORDER_ID = 1
REQUIREMENT_NODE_LEVEL = 2
REQUIREMENT_NODE_REFERENCE = "test ref"


@pytest.mark.django_db
class TestRequirementNodesUnauthenticated:
    """Perform tests on RequirementNodes API endpoint without authentication"""

    client = APIClient()

    def test_get_requirement_nodes(self, authenticated_client):
        """test to get requirement nodes from the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.get_object(
            self.client,
            "Requirement nodes",
            RequirementNode,
            {
                "name": REQUIREMENT_NODE_NAME,
                "description": REQUIREMENT_NODE_DESCRIPTION,
                "assessable": True,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
class TestRequirementNodesAuthenticated:
    """Perform tests on RequirementNodes API endpoint with authentication"""

    def test_get_requirement_nodes(self, test):
        """test to get requirement nodes from the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Requirement nodes",
            RequirementNode,
            {
                "name": REQUIREMENT_NODE_NAME,
                "description": REQUIREMENT_NODE_DESCRIPTION,
                "urn": REQUIREMENT_NODE_URN,
                "parent_urn": REQUIREMENT_NODE_PARENT_URN,
                "order_id": REQUIREMENT_NODE_ORDER_ID,
                "level": REQUIREMENT_NODE_LEVEL,
                "assessable": True,
                "folder": test.folder,
                "framework": Framework.objects.all()[0],
            },
            {
                "folder": str(test.folder.id),
                "framework": str(Framework.objects.all()[0].id),
            },
            base_count=-1,
            user_group=test.user_group,
        )

    def test_import_requirement_nodes(self, test):
        """test that the requirements values imported from a library are correct"""
        EndpointTestsQueries.Auth.import_object(
            test.client, "Framework", user_group=test.user_group
        )
        EndpointTestsQueries.Auth.compare_results(
            test.client,
            "Requirement nodes",
            EndpointTestsUtils.get_endpoint_url("Requirement nodes"),
            EndpointTestsUtils.get_object_urn("Framework"),
            [
                "name",
                "description",
                "urn",
                "parent_urn",
            ],
        )
