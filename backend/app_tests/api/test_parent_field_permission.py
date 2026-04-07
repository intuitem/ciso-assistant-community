"""
Tests for parent field change permission validation.

This ensures users cannot bypass folder permissions by changing parent relationships
for models that inherit folder from a parent (Folder, RiskScenario, Representative, Solution).
"""

import pytest
from rest_framework import status

from api.test_utils import EndpointTestsUtils
from iam.models import Folder
from core.models import Perimeter, RiskAssessment, RiskMatrix, RiskScenario
from tprm.models import Entity, Representative, Solution
from test_fixtures import RISK_MATRIX_JSON_DEFINITION


def _build_risk_assessment(name: str, folder: Folder) -> RiskAssessment:
    perimeter = Perimeter.objects.create(name=f"{name} perimeter", folder=folder)
    risk_matrix = RiskMatrix.objects.create(
        name=f"{name} matrix",
        folder=folder,
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    return RiskAssessment.objects.create(
        name=name,
        perimeter=perimeter,
        risk_matrix=risk_matrix,
    )


def _expected_parent_change_status(
    user_group: str,
    scope_folder: Folder,
    model_verbose_name: str,
    immutable_parent: bool = True,
    client=None,
    object_url: str | None = None,
    target_folder: Folder | None = None,
) -> int:
    if immutable_parent and client and object_url:
        response = client.get(object_url)
        if response.status_code == status.HTTP_404_NOT_FOUND:
            return status.HTTP_404_NOT_FOUND

    view_fails, view_status, view_reason = EndpointTestsUtils.expected_request_response(
        "view",
        model_verbose_name,
        str(scope_folder),
        user_group,
    )
    if view_reason == "outside_scope":
        return status.HTTP_404_NOT_FOUND
    if view_fails:
        return status.HTTP_404_NOT_FOUND

    change_fails, change_status, change_reason = (
        EndpointTestsUtils.expected_request_response(
            "change",
            model_verbose_name,
            str(scope_folder),
            user_group,
        )
    )
    if change_reason == "outside_scope":
        return status.HTTP_404_NOT_FOUND
    if change_fails:
        return change_status
    if immutable_parent:
        return status.HTTP_403_FORBIDDEN
    if target_folder:
        add_fails, _, _ = EndpointTestsUtils.expected_request_response(
            "add",
            model_verbose_name,
            str(target_folder),
            user_group,
        )
        if add_fails:
            return status.HTTP_403_FORBIDDEN
    return status.HTTP_200_OK


@pytest.mark.django_db
class TestParentFieldPermissionValidation:
    """Test that changing parent fields validates target folder permissions"""

    def test_folder_parent_folder_change_blocked(self, test):
        """Test that changing parent_folder of a Folder validates permissions"""
        root = Folder.get_root_folder()
        folder_b = Folder.objects.create(name="Folder B Outside", parent_folder=root)
        subfolder = Folder.objects.create(name="Subfolder", parent_folder=test.folder)

        response = test.client.patch(
            f"/api/folders/{subfolder.id}/",
            {"parent_folder": str(folder_b.id)},
            format="json",
        )

        expected_status = _expected_parent_change_status(
            test.user_group,
            subfolder.parent_folder,
            "Folders",
            immutable_parent=False,
            client=test.client,
            object_url=f"/api/folders/{subfolder.id}/",
            target_folder=folder_b,
        )
        assert response.status_code == expected_status
        if expected_status == status.HTTP_200_OK:
            subfolder.refresh_from_db()
            assert subfolder.parent_folder_id == folder_b.id

    def test_risk_scenario_risk_assessment_change_blocked(self, test):
        """Test that changing risk_assessment of RiskScenario validates permissions"""
        root = Folder.get_root_folder()
        folder_b = Folder.objects.create(name="Folder B Outside", parent_folder=root)

        ra_accessible = _build_risk_assessment("RA accessible", test.folder)
        ra_blocked = _build_risk_assessment("RA blocked", folder_b)

        risk_scenario = RiskScenario.objects.create(
            name="Test Scenario", risk_assessment=ra_accessible
        )

        response = test.client.patch(
            f"/api/risk-scenarios/{risk_scenario.id}/",
            {"risk_assessment": str(ra_blocked.id)},
            format="json",
        )

        expected_status = _expected_parent_change_status(
            test.user_group,
            ra_accessible.folder,
            "Risk Scenarios",
            client=test.client,
            object_url=f"/api/risk-scenarios/{risk_scenario.id}/",
        )
        assert response.status_code == expected_status
        if expected_status == status.HTTP_200_OK:
            risk_scenario.refresh_from_db()
            assert risk_scenario.risk_assessment_id == ra_blocked.id

    def test_representative_entity_change_blocked(self, test):
        """Test that changing entity of Representative validates permissions"""
        root = Folder.get_root_folder()
        folder_b = Folder.objects.create(name="Folder B Outside", parent_folder=root)

        entity_accessible = Entity.objects.create(name="Entity A", folder=test.folder)
        entity_blocked = Entity.objects.create(name="Entity B", folder=folder_b)

        rep = Representative.objects.create(
            entity=entity_accessible,
            email="rep@test.com",
            first_name="Test",
            last_name="Rep",
        )

        response = test.client.patch(
            f"/api/representatives/{rep.id}/",
            {"entity": str(entity_blocked.id)},
            format="json",
        )

        expected_status = _expected_parent_change_status(
            test.user_group,
            entity_accessible.folder,
            "Representatives",
            client=test.client,
            object_url=f"/api/representatives/{rep.id}/",
        )
        assert response.status_code == expected_status
        if expected_status == status.HTTP_200_OK:
            rep.refresh_from_db()
            assert rep.entity_id == entity_blocked.id

    def test_solution_provider_entity_change_blocked(self, test):
        """Test that changing provider_entity of Solution validates permissions"""
        root = Folder.get_root_folder()
        folder_b = Folder.objects.create(name="Folder B Outside", parent_folder=root)

        entity_accessible = Entity.objects.create(name="Entity A", folder=test.folder)
        entity_blocked = Entity.objects.create(name="Entity B", folder=folder_b)

        solution = Solution.objects.create(
            name="Test Solution", provider_entity=entity_accessible
        )

        response = test.client.patch(
            f"/api/solutions/{solution.id}/",
            {"provider_entity": str(entity_blocked.id)},
            format="json",
        )

        expected_status = _expected_parent_change_status(
            test.user_group,
            entity_accessible.folder,
            "Solutions",
            client=test.client,
            object_url=f"/api/solutions/{solution.id}/",
        )
        assert response.status_code == expected_status
        if expected_status == status.HTTP_200_OK:
            solution.refresh_from_db()
            assert solution.provider_entity_id == entity_blocked.id

    def test_parent_field_not_changing_allowed(self, test):
        """Test that updating other fields without changing parent is allowed"""
        ra = _build_risk_assessment("RA in User Folder", test.folder)
        risk_scenario = RiskScenario.objects.create(
            name="Test Scenario",
            risk_assessment=ra,
            description="Original description",
        )

        response = test.client.patch(
            f"/api/risk-scenarios/{risk_scenario.id}/",
            {"description": "Updated description"},
            format="json",
        )

        change_fails, change_status, change_reason = (
            EndpointTestsUtils.expected_request_response(
                "change",
                "Risk Scenarios",
                str(ra.folder),
                test.user_group,
            )
        )

        if change_reason == "outside_scope":
            assert response.status_code == status.HTTP_404_NOT_FOUND
            return
        if change_fails:
            assert response.status_code == change_status
            return

        assert response.status_code == status.HTTP_200_OK
        risk_scenario.refresh_from_db()
        assert risk_scenario.description == "Updated description"
