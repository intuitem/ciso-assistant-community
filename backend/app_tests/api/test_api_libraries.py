import json
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from app_tests.test_vars import TEST_FRAMEWORK_URN, TEST_RISK_MATRIX_URN
from core.models import (
    Framework,
    LoadedLibrary,
    ReferenceControl,
    RequirementNode,
    Threat,
)
from core.models import RiskMatrix
from iam.models import Folder
from rest_framework import status

from test_utils import EndpointTestsQueries, EndpointTestsUtils


@pytest.mark.django_db
class TestLibrariesUnauthenticated:
    """Perform tests on Libraries API endpoint without authentication"""

    client = APIClient()

    def test_get_libraries(self):
        """test to get libraries from the API without authentication"""

        EndpointTestsQueries.get_object(self.client, "Stored libraries")

    def test_import_frameworks(self):
        """test to import libraries with the API without authentication"""

        EndpointTestsQueries.import_object(self.client, "Framework")

    def test_delete_frameworks(self, authenticated_client):
        """test to delete libraries with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Framework")
        EndpointTestsQueries.delete_object(self.client, "Frameworks", Framework)

    def test_import_risk_matrix(self):
        """test to import libraries with the API without authentication"""

        EndpointTestsQueries.import_object(self.client, "Risk matrix")

    def test_delete_risk_matrix(self, authenticated_client):
        """test to delete libraries with the API without authentication"""

        EndpointTestsQueries.Auth.import_object(authenticated_client, "Risk matrix")
        EndpointTestsQueries.delete_object(self.client, "Risk matrices", RiskMatrix)


@pytest.mark.django_db
class TestLibrariesAuthenticated:
    """Perform tests on Libraries API endpoint with authentication"""

    def test_get_libraries(self, test):
        """test to get libraries from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client, "Stored libraries", base_count=-1, user_group=test.user_group
        )

    def test_import_frameworks(self, test):
        """test to import frameworks with the API with authentication"""

        # Uses the API endpoint to get library details with the admin client
        lib_detail_response = test.admin_client.get(
            EndpointTestsUtils.get_stored_library_content(
                test.client, TEST_FRAMEWORK_URN
            )
        )
        lib_detail_response = lib_detail_response.content
        lib_detail_response = json.loads(lib_detail_response)
        lib_detail_response = lib_detail_response["framework"]

        # Asserts that the library is not already loaded
        assert Framework.objects.all().count() == 0, (
            "libraries are already loaded in the database"
        )
        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Frameworks",
            user_group=test.user_group,
        )

        EndpointTestsQueries.Auth.import_object(
            test.client, "Framework", user_group=test.user_group
        )

        assert Framework.objects.all().count() == (
            1
            if not EndpointTestsUtils.expected_request_response(
                "add", "loadedlibrary", str(test.folder), test.user_group
            )[0]
            else 0
        ), "Frameworks are not correctly imported in the database"

        # Uses the API endpoint to assert that the library was properly loaded
        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Frameworks",
            test_params={
                "name": lib_detail_response["name"],
                "description": lib_detail_response["description"],
                "urn": lib_detail_response["urn"],
                "folder": {
                    "id": str(Folder.get_root_folder().id),
                    "str": Folder.get_root_folder().name,
                },
            },
            base_count=1,
            user_group=test.user_group,
            fails=EndpointTestsUtils.expected_request_response(
                "add", "loadedlibrary", str(test.folder), test.user_group
            )[0],
        )

    def test_delete_frameworks(self, test):
        """test to delete frameworks with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Framework")
        assert Framework.objects.all().count() == 1, (
            "Frameworks are not correctly imported in the database"
        )

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Frameworks",
            Framework,
            user_group=test.user_group,
            scope="Global",
            **(
                {"fails": True, "expected_status": status.HTTP_403_FORBIDDEN}
                if test.user_group == "BI-UG-DMA"
                else {}  # Domain Manager can't delete Global frameworks (i.e. imported frameworks)
            ),
        )

    def test_import_risk_matrix(self, test):
        """test to import risk matrix with the API with authentication"""

        # Uses the API endpoint to get library details with the admin client
        lib_detail_response = test.admin_client.get(
            EndpointTestsUtils.get_stored_library_content(
                test.client, TEST_RISK_MATRIX_URN
            )
        )
        lib_detail_response = lib_detail_response.content
        lib_detail_response = json.loads(lib_detail_response)
        lib_detail_response = lib_detail_response["risk_matrix"][0]

        # Asserts that the library is not already loaded
        assert RiskMatrix.objects.all().count() == 0, (
            "libraries are already loaded in the database"
        )
        EndpointTestsQueries.Auth.get_object(
            test.client, "Risk matrices", user_group=test.user_group
        )

        EndpointTestsQueries.Auth.import_object(
            test.client, "Risk matrix", user_group=test.user_group
        )

        assert RiskMatrix.objects.all().count() == (
            1
            if not EndpointTestsUtils.expected_request_response(
                "add", "loadedlibrary", str(test.folder), test.user_group
            )[0]
            else 0
        ), "Risk matrices are not correctly imported in the database"

        # Uses the API endpoint to assert that the library was properly loaded
        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Risk matrices",
            test_params={
                "name": lib_detail_response["name"],
                "description": lib_detail_response["description"],
                "urn": lib_detail_response["urn"],
                "folder": {
                    "id": str(Folder.get_root_folder().id),
                    "str": Folder.get_root_folder().name,
                },
                #                                 'json_definition': lib_detail_response  # TODO: restore this test
            },
            base_count=1,
            user_group=test.user_group,
            fails=EndpointTestsUtils.expected_request_response(
                "add", "loadedlibrary", str(test.folder), test.user_group
            )[0],
        )

    def test_delete_matrix(self, test):
        """test to delete risk matrix with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Risk matrices",
            RiskMatrix,
            user_group=test.user_group,
            scope="Global",
            **(
                {"fails": True, "expected_status": status.HTTP_403_FORBIDDEN}
                if test.user_group == "BI-UG-DMA"
                else {}  # Domain Manager can't delete Global risk matrices (i.e. imported matrices)
            ),
        )


# URNs used by the custom-library update regression tests below. A dedicated
# namespace keeps these objects from colliding with the built-in test fixtures.
_UPDATE_LIBRARY_URN = "urn:intuitem:test:library:test-api-libraries-update"
_UPDATE_FRAMEWORK_URN = "urn:intuitem:test:framework:test-api-libraries-update"
_UPDATE_REQUIREMENT_NODE_URN = "urn:intuitem:test:req_node:test-api-libraries-update:01"
_UPDATE_THREAT_KEPT_URN = "urn:intuitem:test:threat:test-api-libraries-update:t01"
_UPDATE_THREAT_REMOVED_URN = "urn:intuitem:test:threat:test-api-libraries-update:t02"
_UPDATE_RC_KEPT_URN = (
    "urn:intuitem:test:reference_control:test-api-libraries-update:rc01"
)
_UPDATE_RC_REMOVED_URN = (
    "urn:intuitem:test:reference_control:test-api-libraries-update:rc02"
)
_UPDATE_RC_REMOVED_2_URN = (
    "urn:intuitem:test:reference_control:test-api-libraries-update:rc03"
)
_UPDATE_THREAT_ANNOTATION = "Annotation added in version 2"

# Version 1: the requirement node references two threats and two reference
# controls; the library carries three reference controls in total.
_UPDATE_LIBRARY_YAML_V1 = f"""
urn: {_UPDATE_LIBRARY_URN}
locale: en
ref_id: TEST-API-LIBRARIES-UPDATE
name: Test API Libraries Update
description: Custom library used by the library update regression tests
copyright: Test
version: 1
publication_date: 2025-01-01
provider: test-provider
packager: test-packager
objects:
  threats:
  - urn: {_UPDATE_THREAT_KEPT_URN}
    ref_id: T01
    name: Kept threat
    description: Threat that stays linked after the update
  - urn: {_UPDATE_THREAT_REMOVED_URN}
    ref_id: T02
    name: Removed threat
    description: Threat that is unlinked after the update
  reference_controls:
  - urn: {_UPDATE_RC_KEPT_URN}
    ref_id: rc01
    category: process
    description: Reference control that stays in the library
  - urn: {_UPDATE_RC_REMOVED_URN}
    ref_id: rc02
    category: technical
    description: Reference control dropped from the library in version 2
  - urn: {_UPDATE_RC_REMOVED_2_URN}
    ref_id: rc03
    category: physical
    description: Reference control dropped from the library in version 2
  framework:
    urn: {_UPDATE_FRAMEWORK_URN}
    ref_id: TEST-API-LIBRARIES-UPDATE
    name: Test API Libraries Update
    description: Framework used by the library update regression tests
    requirement_nodes:
    - urn: {_UPDATE_REQUIREMENT_NODE_URN}
      assessable: true
      depth: 1
      ref_id: '01'
      name: Sole requirement
      description: Requirement node linked to threats and reference controls
      reference_controls:
      - {_UPDATE_RC_KEPT_URN}
      - {_UPDATE_RC_REMOVED_URN}
      threats:
      - {_UPDATE_THREAT_KEPT_URN}
      - {_UPDATE_THREAT_REMOVED_URN}
""".lstrip()

# Version 2: one threat and one reference control are dropped from the node,
# two reference controls are dropped from the library, and the kept threat
# gains an annotation.
_UPDATE_LIBRARY_YAML_V2 = f"""
urn: {_UPDATE_LIBRARY_URN}
locale: en
ref_id: TEST-API-LIBRARIES-UPDATE
name: Test API Libraries Update
description: Custom library used by the library update regression tests
copyright: Test
version: 2
publication_date: 2025-01-02
provider: test-provider
packager: test-packager
objects:
  threats:
  - urn: {_UPDATE_THREAT_KEPT_URN}
    ref_id: T01
    name: Kept threat
    description: Threat that stays linked after the update
    annotation: {_UPDATE_THREAT_ANNOTATION}
  - urn: {_UPDATE_THREAT_REMOVED_URN}
    ref_id: T02
    name: Removed threat
    description: Threat that is unlinked after the update
  reference_controls:
  - urn: {_UPDATE_RC_KEPT_URN}
    ref_id: rc01
    category: process
    description: Reference control that stays in the library
  framework:
    urn: {_UPDATE_FRAMEWORK_URN}
    ref_id: TEST-API-LIBRARIES-UPDATE
    name: Test API Libraries Update
    description: Framework used by the library update regression tests
    requirement_nodes:
    - urn: {_UPDATE_REQUIREMENT_NODE_URN}
      assessable: true
      depth: 1
      ref_id: '01'
      name: Sole requirement
      description: Requirement node linked to threats and reference controls
      reference_controls:
      - {_UPDATE_RC_KEPT_URN}
      threats:
      - {_UPDATE_THREAT_KEPT_URN}
""".lstrip()


@pytest.mark.django_db
class TestLibraryUpdateRegression:
    """Regression tests for custom library updates (CA-1661).

    These exercise the upload + update API flow and lock in three behaviours:
    reference controls dropped from a new library version are detached rather
    than left attached, requirement-node threats/reference-controls are
    replaced (stale links removed) instead of only appended, and threat
    annotations are imported.
    """

    @staticmethod
    def _upload_library(client: APIClient, content: str) -> None:
        """Upload a YAML library through the FileUploadParser endpoint."""
        response = client.post(
            reverse("stored-libraries-upload-library"),
            data=content.encode("utf-8"),
            content_type="application/yaml",
            HTTP_CONTENT_DISPOSITION="attachment; filename=test-library.yaml",
        )
        assert response.status_code == status.HTTP_201_CREATED, (
            f"Library YAML upload failed: {response.content}"
        )

    def _load_v1_then_v2(self, client: APIClient) -> LoadedLibrary:
        """Load version 1, then upload version 2 so it is ready to update."""
        self._upload_library(client, _UPDATE_LIBRARY_YAML_V1)
        self._upload_library(client, _UPDATE_LIBRARY_YAML_V2)

        loaded_library = LoadedLibrary.objects.filter(urn=_UPDATE_LIBRARY_URN).first()
        assert loaded_library is not None, "LoadedLibrary was not created"
        return loaded_library

    @staticmethod
    def _update_library(client: APIClient, loaded_library: LoadedLibrary) -> None:
        response = client.get(f"/api/loaded-libraries/{loaded_library.pk}/update/")
        assert response.status_code == status.HTTP_200_OK, (
            f"Library update failed: {response.content}"
        )

    def test_update_detaches_removed_reference_controls(self, authenticated_client):
        """Reference controls absent from the new version are detached, not kept."""
        loaded_library = self._load_v1_then_v2(authenticated_client)

        assert ReferenceControl.objects.filter(library=loaded_library.pk).count() == 3

        self._update_library(authenticated_client, loaded_library)

        # The two dropped controls are detached (library=None) but still exist.
        assert (
            ReferenceControl.objects.filter(library=loaded_library.pk).count() == 1
        ), "Removed reference controls should be detached from the library"
        for removed_urn in (_UPDATE_RC_REMOVED_URN, _UPDATE_RC_REMOVED_2_URN):
            detached = ReferenceControl.objects.get(urn=removed_urn)
            assert detached.library is None, (
                f"Reference control {removed_urn} should be detached, not deleted"
            )

    def test_update_replaces_requirement_node_links(self, authenticated_client):
        """Requirement-node threats/reference-controls are replaced, not appended."""
        loaded_library = self._load_v1_then_v2(authenticated_client)

        requirement_node = RequirementNode.objects.get(urn=_UPDATE_REQUIREMENT_NODE_URN)
        assert requirement_node.threats.count() == 2
        assert requirement_node.reference_controls.count() == 2

        self._update_library(authenticated_client, loaded_library)

        requirement_node.refresh_from_db()
        assert requirement_node.threats.count() == 1, (
            "Stale threat links should be removed on update"
        )
        assert requirement_node.reference_controls.count() == 1, (
            "Stale reference control links should be removed on update"
        )
        assert set(requirement_node.threats.values_list("urn", flat=True)) == {
            _UPDATE_THREAT_KEPT_URN
        }
        assert set(
            requirement_node.reference_controls.values_list("urn", flat=True)
        ) == {_UPDATE_RC_KEPT_URN}

    def test_update_imports_threat_annotation(self, authenticated_client):
        """Threat annotations introduced in the new version are imported."""
        loaded_library = self._load_v1_then_v2(authenticated_client)

        threat = Threat.objects.get(urn=_UPDATE_THREAT_KEPT_URN)
        assert threat.annotation in (None, ""), (
            "Annotation should be empty before the update"
        )

        self._update_library(authenticated_client, loaded_library)

        threat.refresh_from_db()
        assert threat.annotation == _UPDATE_THREAT_ANNOTATION
