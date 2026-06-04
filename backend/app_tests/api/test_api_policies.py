import pytest
from rest_framework import status
from rest_framework.test import APIClient
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    Framework,
    Policy,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder

from test_utils import EndpointTestsQueries

# Generic policy data for tests
POLICY_NAME = "Test Policy"
POLICY_DESCRIPTION = "Test Description"
POLICY_STATUS = Policy.Status.TO_DO
POLICY_STATUS2 = Policy.Status.ACTIVE
POLICY_EFFORT = ("L", "Large")
POLICY_EFFORT2 = ("M", "Medium")
POLICY_LINK = "https://example.com"
POLICY_ETA = "2024-01-01"


def _make_requirement_assessment(folder, suffix):
    framework = Framework.objects.create(
        urn=f"urn:test:policy-control-catalogue:{suffix}",
        name=f"Catalogue framework {suffix}",
        folder=folder,
    )
    requirement = RequirementNode.objects.create(
        urn=f"urn:test:policy-control-catalogue:{suffix}:requirement",
        folder=folder,
        framework=framework,
        assessable=True,
    )
    compliance_assessment = ComplianceAssessment.objects.create(
        name=f"Catalogue assessment {suffix}",
        folder=folder,
        framework=framework,
    )
    return RequirementAssessment.objects.create(
        compliance_assessment=compliance_assessment,
        requirement=requirement,
        folder=folder,
    )


def _get_results(response):
    data = response.json()
    return data["results"] if isinstance(data, dict) and "results" in data else data


@pytest.mark.django_db
class TestPolicysUnauthenticated:
    """Perform tests on policies API endpoint without authentication"""

    client = APIClient()

    def test_get_policies(self):
        """test to get policies from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_policies(self):
        """test to create policies with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_policies(self):
        """test to update policies with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + POLICY_NAME,
                "description": "new " + POLICY_DESCRIPTION,
                "folder": Folder.objects.create(name="test2").id,
            },
        )

    def test_delete_policies(self):
        """test to delete policies with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
class TestPolicysAuthenticated:
    """Perform tests on policies API endpoint with authentication"""

    def test_get_policies(self, test):
        """test to get policies from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "status": POLICY_STATUS._value_,
                "link": POLICY_LINK,
                "eta": POLICY_ETA,
                "effort": POLICY_EFFORT[0],
                "folder": test.folder,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "reference_control": None,
                "status": POLICY_STATUS._value_,
                "effort": POLICY_EFFORT[1],
            },
            user_group=test.user_group,
        )

    def test_create_policies(self, test):
        """test to create policies with the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "status": POLICY_STATUS._value_,
                "link": POLICY_LINK,
                "eta": POLICY_ETA,
                "effort": POLICY_EFFORT[0],
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "status": POLICY_STATUS._value_,
                "effort": POLICY_EFFORT[1],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_policies(self, test):
        """test to update policies with the API with authentication"""

        folder = Folder.objects.create(name="test2")

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "description": POLICY_DESCRIPTION,
                "status": POLICY_STATUS._value_,
                "link": POLICY_LINK,
                "eta": POLICY_ETA,
                "effort": POLICY_EFFORT[0],
                "folder": test.folder,
            },
            {
                "name": "new " + POLICY_NAME,
                "description": "new " + POLICY_DESCRIPTION,
                "status": POLICY_STATUS2._value_,
                "link": "new " + POLICY_LINK,
                "eta": "2025-01-01",
                "effort": POLICY_EFFORT2[0],
                "folder": str(folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "status": POLICY_STATUS._value_,
                "effort": POLICY_EFFORT[1],
            },
            user_group=test.user_group,
        )

    def test_delete_policies(self, test):
        """test to delete policies with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Policies",
            Policy,
            {
                "name": POLICY_NAME,
                "folder": test.folder,
            },
            user_group=test.user_group,
        )

    def test_get_category_choices(self, test):
        """test to get policies category choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Policies",
            "category",
            Policy.CATEGORY,
            user_group=test.user_group,
        )

    def test_get_effort_choices(self, test):
        """test to get policies effort choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client, "Policies", "effort", Policy.EFFORT, user_group=test.user_group
        )

    def test_get_status_choices(self, test):
        """test to get policies status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Policies",
            "status",
            Policy.Status.choices,
            user_group=test.user_group,
        )

    def test_get_control_catalogue(self, authenticated_client):
        """returns deduped non-policy controls linked through policy requirements"""

        folder = Folder.objects.create(name="policy-control-catalogue")
        policy = Policy.objects.create(name="Catalogue Policy", folder=folder)
        other_policy = Policy.objects.create(name="Other Policy", folder=folder)
        policy_category_row = AppliedControl.objects.create(
            name="Policy category row",
            ref_id="POLICY-CAT",
            category="policy",
            folder=folder,
        )
        control_a = AppliedControl.objects.create(
            name="Alpha Control",
            ref_id="CTRL-A",
            category="technical",
            folder=folder,
        )
        control_b = AppliedControl.objects.create(
            name="Beta Control",
            ref_id="CTRL-B",
            category="process",
            folder=folder,
        )
        unrelated_control = AppliedControl.objects.create(
            name="Unrelated Control",
            ref_id="CTRL-UNRELATED",
            folder=folder,
        )

        requirement_assessment_a = _make_requirement_assessment(folder, "a")
        requirement_assessment_b = _make_requirement_assessment(folder, "b")
        requirement_assessment_a.applied_controls.add(
            policy,
            other_policy,
            policy_category_row,
            control_a,
            control_b,
        )
        requirement_assessment_b.applied_controls.add(policy, control_a)

        response = authenticated_client.get(
            f"/api/policies/{policy.id}/control-catalogue/"
        )

        assert response.status_code == status.HTTP_200_OK
        rows = _get_results(response)
        row_ids = [row["id"] for row in rows]
        assert row_ids.count(str(control_a.id)) == 1
        assert set(row_ids) == {str(control_a.id), str(control_b.id)}
        assert str(policy.id) not in row_ids
        assert str(other_policy.id) not in row_ids
        assert str(policy_category_row.id) not in row_ids
        assert str(unrelated_control.id) not in row_ids

        row_a = next(row for row in rows if row["id"] == str(control_a.id))
        assert "linked_models" in row_a
        assert "requirement_assessments" in row_a["linked_models"]
        assert row_a["folder"] == {"id": str(folder.id), "str": folder.name}

    def test_control_catalogue_supports_search_ordering_and_pagination(
        self, authenticated_client
    ):
        """supports Applied Control list filtering behavior on the derived queryset"""

        folder = Folder.objects.create(name="policy-control-catalogue-filtering")
        policy = Policy.objects.create(name="Catalogue Policy", folder=folder)
        requirement_assessment = _make_requirement_assessment(folder, "filtering")
        alpha = AppliedControl.objects.create(
            name="Alpha Control",
            ref_id="CTRL-A",
            category="technical",
            folder=folder,
        )
        beta = AppliedControl.objects.create(
            name="Beta Control",
            ref_id="CTRL-B",
            category="technical",
            folder=folder,
        )
        gamma = AppliedControl.objects.create(
            name="Gamma Control",
            ref_id="CTRL-C",
            category="technical",
            folder=folder,
        )
        requirement_assessment.applied_controls.add(policy, alpha, beta, gamma)

        response = authenticated_client.get(
            f"/api/policies/{policy.id}/control-catalogue/",
            {"search": "Control", "ordering": "-ref_id", "limit": 2, "offset": 1},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        rows = data["results"]
        assert data["count"] == 3
        assert [row["id"] for row in rows] == [str(beta.id), str(alpha.id)]

        response = authenticated_client.get(
            f"/api/policies/{policy.id}/control-catalogue/",
            {"search": "Beta"},
        )

        assert response.status_code == status.HTTP_200_OK
        rows = _get_results(response)
        assert [row["id"] for row in rows] == [str(beta.id)]
