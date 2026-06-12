from typing import Final, cast

import pytest
from django.http import HttpResponse
from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    Framework,
    LoadedLibrary,
    ReferenceControl,
    RequirementNode,
    StoredLibrary,
    Threat,
)
from iam.models import User, UserGroup


class TestData:
    LIBRARY_URN: Final[str] = "urn:intuitem:test:library:test-custom-library-update"
    FRAMEWORK_URN: Final[str] = "urn:intuitem:test:framework:asf-baseline-v2"
    FRAMEWORK_NAME: Final[str] = "Test custom library update"
    THREAT_URN: Final[str] = "urn:intuitem:test:threat:asf-baseline-v2:t1055.013"
    THREAT_V2_ANNOTATION: Final[str] = "Threat V2 annotation."
    REQUIREMENT_NODE_URN: Final[str] = "urn:intuitem:test:req_node:asf-baseline-v2:01"

    LIBRARY_YAML_CONTENT_V1: Final[str] = f"""
urn: {LIBRARY_URN}
locale: en
ref_id: TEST-CUSTOM-LIBRARY-UPDATE
name: Test Library(test_custom_library_update.py) Name
description: Test Library(test_custom_library_update.py) Description
  custom framework
copyright: Test
version: 1
publication_date: 2025-01-01
provider: test-provider
packager: test-packager
objects:
  threats:
  - urn: urn:intuitem:test:threat:asf-baseline-v2:t1055.011
    ref_id: T1055.011
    name: Extra Window Memory InjectionXXXXXXXXX
    description: Extra Window Memory InjectionnnXXXXXXXXX
    annotation: "AAA"
  - urn: urn:intuitem:test:threat:asf-baseline-v2:t1055.012
    ref_id: T1055.012
    name: Socket Filters
    description: Socket Filtersss
    annotation: "BBB"
  - urn: {THREAT_URN}
    ref_id: T1055.013
    name: Scheduled Task
    description: Scheduled Taskkk
  reference_controls:
  - urn: urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-01
    ref_id: asf-rec-01
    category: process
    description: Risk assessment frameworkXXXXXXXXXXXXXXXX
  - urn: urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-02
    ref_id: asf-rec-02
    category: technical
    description: EDR deployment
  - urn: urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-03
    ref_id: asf-rec-03
    category: physical
    description: Facility surveillance
  - urn: urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-04
    ref_id: asf-rec-04
    category: policy
    description: IAM/PAM Policy
  - urn: urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-05
    ref_id: asf-rec-05
    category: technical
    description: Immutable backups
  - urn: urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-06
    ref_id: asf-rec-06
    category: technical
    description: SAST
  framework:
    urn: {FRAMEWORK_URN}
    ref_id: ASF-Baseline
    name: {FRAMEWORK_NAME}
    description: Test custom library update DESCRIPTION
      for custom framework
    requirement_nodes:
    - urn: {REQUIREMENT_NODE_URN}
      assessable: true
      depth: 1
      ref_id: '01'
      name: Risk, Governance and Regulation
      description: Risk analysis, assigned personnel, management involvement, regulatory
        framework identification, independent audit
      reference_controls:
      - urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-01
      - urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-02
      threats:
      - urn:intuitem:test:threat:asf-baseline-v2:t1055.011
      - urn:intuitem:test:threat:asf-baseline-v2:t1055.012
    - urn: urn:intuitem:test:req_node:asf-baseline-v2:02
      assessable: true
      depth: 1
      ref_id: '02'
      name: Inventory
      description: Hardware and software components listed, regular controls and audits,
        lifecycle management, categorization, visibility, and continuous improvement
      reference_controls:
      - urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-02
    - urn: urn:intuitem:test:req_node:asf-baseline-v2:03
      assessable: true
      depth: 1
      ref_id: '03'
      name: IAM/PAM
      description: Identity federation, SSO and MFA, group-based access management,
        secrets management, AD hardening, IAM aligned with onboarding and offboarding
        processes
      reference_controls:
      - urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-04
""".lstrip()

    LIBRARY_YAML_CONTENT_V2: Final[str] = f"""
urn: {LIBRARY_URN}
locale: en
ref_id: TEST-CUSTOM-LIBRARY-UPDATE
name: Test Library(test_custom_library_update.py) Name XXX
description: Test Library(test_custom_library_update.py) Description XXX
copyright: Test
version: 2
publication_date: 2025-01-01
provider: test-provider
packager: test-packager
objects:
  threats:
  - urn: urn:intuitem:test:threat:asf-baseline-v2:t1055.011
    ref_id: T1055.011
    name: Extra Window Memory InjectionXXXXXXXXX
    description: Extra Window Memory InjectionnnXXXXXXXXX
    annotation: "AAA"
  - urn: urn:intuitem:test:threat:asf-baseline-v2:t1055.012
    ref_id: T1055.012
    name: Socket Filters
    description: Socket Filtersss
    annotation: "BBB"
  - urn: {THREAT_URN}
    ref_id: T1055.013
    name: Scheduled Task
    description: Scheduled Taskkk
    annotation: {THREAT_V2_ANNOTATION}
  reference_controls:
  - urn: urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-01
    ref_id: asf-rec-01
    category: process
    description: Risk assessment frameworkXXXXXXXXXXXXXXXX
  - urn: urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-02
    ref_id: asf-rec-02
    category: technical
    description: EDR deployment
  - urn: urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-03
    ref_id: asf-rec-03
    category: physical
    description: Facility surveillance
  framework:
    urn: {FRAMEWORK_URN}
    ref_id: ASF-Baseline
    name: {FRAMEWORK_NAME}
    description: Test custom library update DESCRIPTION
      for custom framework
    requirement_nodes:
    - urn: {REQUIREMENT_NODE_URN}
      assessable: true
      depth: 1
      ref_id: '01'
      name: Risk, Governance and Regulation
      description: Risk analysis, assigned personnel, management involvement, regulatory
        framework identification, independent audit
      reference_controls:
      - urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-01
      threats:
      - urn:intuitem:test:threat:asf-baseline-v2:t1055.012
    - urn: urn:intuitem:test:req_node:asf-baseline-v2:02
      assessable: true
      depth: 1
      ref_id: '02'
      name: Inventory
      description: Hardware and software components listed, regular controls and audits,
        lifecycle management, categorization, visibility, and continuous improvement
      reference_controls:
      - urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-02
    - urn: urn:intuitem:test:req_node:asf-baseline-v2:03
      assessable: true
      depth: 1
      ref_id: '03'
      name: IAM/PAM
      description: Identity federation, SSO and MFA, group-based access management,
        secrets management, AD hardening, IAM aligned with onboarding and offboarding
        processes
      reference_controls:
      - urn:intuitem:test:reference_control:asf-baseline-v2:asf-rec-03
""".lstrip()


def _upload_yaml(
    client: APIClient, url: str, filename: str, content: bytes
) -> HttpResponse:
    """Upload a YAML file using the FileUploadParser-compatible format.

    The StoredLibraryViewSet uses FileUploadParser, which expects the raw
    file content in the request body with a Content-Disposition header.
    """
    response = client.post(
        url,
        data=content,
        content_type="application/yaml",
        HTTP_CONTENT_DISPOSITION=f"attachment; filename={filename}",
    )
    return cast(HttpResponse, response)


@pytest.fixture
def app_config():
    """Initialize the application (creates built-in groups, etc.)."""
    startup(sender=None, **{})


@pytest.fixture
def admin_client(app_config: None) -> APIClient:
    """Return an authenticated API client with admin privileges."""
    admin = User.objects.create_superuser(
        "admin@regression-tests.com", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    _auth_token = AuthToken.objects.create(user=admin)
    auth_token = _auth_token[1]
    client.credentials(HTTP_AUTHORIZATION=f"Token {auth_token}")
    return client


@pytest.fixture
def upload_url() -> str:
    """Return the URL for the library upload endpoint."""
    return reverse("stored-libraries-upload-library")


@pytest.mark.django_db
class TestCustomLibraryImportYAML:
    """Regression tests for custom library update via YAML files."""

    @staticmethod
    def load_library(
        admin_client: APIClient, upload_url: str, library_content: str
    ) -> LoadedLibrary:
        response = _upload_yaml(
            admin_client,
            upload_url,
            "sample_framework.yaml",
            library_content.encode("utf-8"),
        )

        assert response.status_code == status.HTTP_201_CREATED, (
            f"Framework YAML upload failed: {response.content}"
        )

        stored_library = StoredLibrary.objects.filter(urn=TestData.LIBRARY_URN).first()
        assert stored_library is not None, "StoredLibrary not created"
        assert stored_library.is_loaded is True

        loaded_library = LoadedLibrary.objects.filter(urn=TestData.LIBRARY_URN).first()
        assert loaded_library is not None, "LoadedLibrary not created"

        framework = Framework.objects.filter(urn=TestData.FRAMEWORK_URN).first()
        assert framework is not None, "Framework not created"
        assert framework.name == TestData.FRAMEWORK_NAME

        return loaded_library

    def test_upload_framework_yaml(self, admin_client: APIClient, upload_url: str):
        """Test uploading a valid YAML framework library updates all expected objects."""

        for library_content in [
            TestData.LIBRARY_YAML_CONTENT_V1,
            TestData.LIBRARY_YAML_CONTENT_V2,
        ]:
            loaded_library = self.load_library(
                admin_client, upload_url, library_content
            )

        # CHECK LIBRARY OBJECTS BEFORE UPDATE

        threat = Threat.objects.get(urn=TestData.THREAT_URN)
        assert threat.annotation in [None, ""], "Unexpected non-empty annotation value."

        assert ReferenceControl.objects.filter(library=loaded_library.pk).count() == 6

        requirement_node = RequirementNode.objects.filter(
            urn=TestData.REQUIREMENT_NODE_URN
        ).first()
        assert requirement_node is not None, (
            f"Requirement with urn {TestData.REQUIREMENT_NODE_URN!r} not found."
        )

        assert requirement_node.reference_controls.count() == 2
        assert requirement_node.threats.count() == 2

        # PERFORM LIBRARY UPDATE

        update_endpoint = f"/api/loaded-libraries/{loaded_library.pk}/update/"
        response = admin_client.get(update_endpoint)

        assert response.status_code == status.HTTP_200_OK, (
            f"Failed to update library: {response.content}"
        )

        # CHECK LIBRARY OBJECTS AFTER UPDATE

        threat = Threat.objects.get(urn=TestData.THREAT_URN)
        assert threat.annotation == TestData.THREAT_V2_ANNOTATION

        assert (
            ReferenceControl.objects.filter(library=loaded_library.pk).count() == 3
        ), (
            "Unexpected number of reference controls (deletion may have failed during update)."
        )

        requirement_node = RequirementNode.objects.filter(
            urn=TestData.REQUIREMENT_NODE_URN
        ).first()
        assert requirement_node is not None, (
            f"Requirement with urn {TestData.REQUIREMENT_NODE_URN!r} not found."
        )

        assert requirement_node.reference_controls.count() == 1
        assert requirement_node.threats.count() == 1
