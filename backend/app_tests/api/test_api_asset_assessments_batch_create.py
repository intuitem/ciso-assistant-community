import pytest
from django.conf import settings
from knox.models import AuthToken
from rest_framework.test import APIClient
from core.models import Asset, Perimeter, RiskMatrix, StoredLibrary
from iam.models import Folder, Permission, Role, RoleAssignment, User, UserGroup
from resilience.models import (
    AssetAssessment,
    BusinessImpactAnalysis,
    EscalationThreshold,
)

BATCH_CREATE_URL = "/api/resilience/asset-assessments/batch-create/"
BATCH_ACTION_URL = "/api/resilience/asset-assessments/batch-action/"


def client_for(email, group_name, folder):
    user = User.objects.create_user(email, is_published=True)
    group = UserGroup.objects.get(name=group_name, folder=folder)
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    client = APIClient()
    token = AuthToken.objects.create(user=user)[1]
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def client_with_role(email, folder, codenames):
    """Client for a user holding a custom role with exactly *codenames* on *folder*.

    Include "view_folder": the IAM walk skips assignments whose role can't see
    folders at all (see RoleAssignment.get_accessible_object_ids).
    """
    user = User.objects.create_user(email, is_published=True)
    role = Role.objects.create(name=f"role-{email}", folder=Folder.get_root_folder())
    role.permissions.set(Permission.objects.filter(codename__in=codenames))
    ra = RoleAssignment.objects.create(
        user=user, role=role, folder=Folder.get_root_folder(), is_recursive=True
    )
    ra.perimeter_folders.add(folder)
    client = APIClient()
    token = AuthToken.objects.create(user=user)[1]
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.mark.django_db
class TestAssetAssessmentsBatchCreate:
    @pytest.fixture
    def setup(self):
        folder = Folder.objects.create(
            name="test-domain",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=Folder.get_root_folder(),
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(folder)
        perimeter = Perimeter.objects.create(name="test", folder=folder)
        StoredLibrary.objects.get(
            urn="urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm"
        ).load()
        matrix = RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
        )
        bia = BusinessImpactAnalysis.objects.create(
            name="bia", perimeter=perimeter, folder=folder, risk_matrix=matrix
        )
        assets = [
            Asset.objects.create(name=f"asset-{i}", folder=folder) for i in range(3)
        ]
        return folder, bia, assets

    def test_batch_create(self, authenticated_client, setup):
        folder, bia, assets = setup
        AssetAssessment.objects.create(bia=bia, asset=assets[0], folder=folder)

        response = authenticated_client.post(
            BATCH_CREATE_URL,
            {"bia": str(bia.id), "assets": [str(a.id) for a in assets]},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["created"] == 2
        assert data["skipped"] == 1
        assert data["errors"] == []
        assessments = AssetAssessment.objects.filter(bia=bia)
        assert assessments.count() == 3
        assert all(aa.folder == folder for aa in assessments)

    def test_batch_create_all_existing(self, authenticated_client, setup):
        folder, bia, assets = setup
        for asset in assets:
            AssetAssessment.objects.create(bia=bia, asset=asset, folder=folder)

        response = authenticated_client.post(
            BATCH_CREATE_URL,
            {"bia": str(bia.id), "assets": [str(a.id) for a in assets]},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["created"] == 0
        assert response.json()["skipped"] == 3

    def test_batch_create_locked_bia(self, authenticated_client, setup):
        folder, bia, assets = setup
        bia.is_locked = True
        bia.save()

        response = authenticated_client.post(
            BATCH_CREATE_URL,
            {"bia": str(bia.id), "assets": [str(assets[0].id)]},
            format="json",
        )
        assert response.status_code == 400
        assert AssetAssessment.objects.filter(bia=bia).count() == 0

    def test_batch_create_missing_params(self, authenticated_client, setup):
        folder, bia, assets = setup

        response = authenticated_client.post(
            BATCH_CREATE_URL, {"assets": [str(assets[0].id)]}, format="json"
        )
        assert response.status_code == 400

        response = authenticated_client.post(
            BATCH_CREATE_URL, {"bia": str(bia.id), "assets": []}, format="json"
        )
        assert response.status_code == 400

    def test_batch_create_all_errors(self, authenticated_client, setup):
        folder, bia, assets = setup

        response = authenticated_client.post(
            BATCH_CREATE_URL,
            {
                "bia": str(bia.id),
                "assets": ["00000000-0000-0000-0000-000000000000"],
            },
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["created"] == 0
        assert len(data["errors"]) == 1

    def test_batch_create_reader_forbidden(self, authenticated_client, setup):
        folder, bia, assets = setup
        reader = client_for("reader@tests.com", "BI-UG-AUD", folder)

        response = reader.post(
            BATCH_CREATE_URL,
            {"bia": str(bia.id), "assets": [str(a.id) for a in assets]},
            format="json",
        )
        assert response.status_code == 403
        assert AssetAssessment.objects.filter(bia=bia).count() == 0

    def test_batch_create_analyst_cannot_reference_foreign_asset(
        self, authenticated_client, setup
    ):
        folder, bia, assets = setup
        other_folder = Folder.objects.create(
            name="other-domain",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=Folder.get_root_folder(),
        )
        foreign_asset = Asset.objects.create(name="foreign", folder=other_folder)
        analyst = client_for("analyst@tests.com", "BI-UG-ANA", folder)

        response = analyst.post(
            BATCH_CREATE_URL,
            {"bia": str(bia.id), "assets": [str(foreign_asset.id), str(assets[0].id)]},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["created"] == 1
        assert data["errors"] == [
            {"asset": str(foreign_asset.id), "error": "asset not found"}
        ]
        assert not AssetAssessment.objects.filter(asset=foreign_asset).exists()

    def test_batch_create_over_cap(self, authenticated_client, setup):
        folder, bia, assets = setup
        too_many = [str(assets[0].id)] * (settings.PAGINATE_BY + 1)

        response = authenticated_client.post(
            BATCH_CREATE_URL, {"bia": str(bia.id), "assets": too_many}, format="json"
        )
        assert response.status_code == 400
        assert response.json()["max"] == settings.PAGINATE_BY

    def test_exclude_bia_asset_filter(self, authenticated_client, setup):
        folder, bia, assets = setup
        AssetAssessment.objects.create(bia=bia, asset=assets[0], folder=folder)

        response = authenticated_client.get(
            f"/api/assets/autocomplete/?exclude_bia={bia.id}"
        )
        assert response.status_code == 200
        ids = {a["id"] for a in response.json()["results"]}
        assert str(assets[0].id) not in ids
        assert str(assets[1].id) in ids

    def test_batch_create_unknown_bia(self, authenticated_client, setup):
        folder, bia, assets = setup

        response = authenticated_client.post(
            BATCH_CREATE_URL,
            {
                "bia": "00000000-0000-0000-0000-000000000000",
                "assets": [str(assets[0].id)],
            },
            format="json",
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestAssetAssessmentsBatchRemove:
    @pytest.fixture
    def setup(self):
        folder = Folder.objects.create(
            name="test-domain",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=Folder.get_root_folder(),
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(folder)
        perimeter = Perimeter.objects.create(name="test", folder=folder)
        StoredLibrary.objects.get(
            urn="urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm"
        ).load()
        matrix = RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
        )
        bia = BusinessImpactAnalysis.objects.create(
            name="bia", perimeter=perimeter, folder=folder, risk_matrix=matrix
        )
        assessments = [
            AssetAssessment.objects.create(
                bia=bia,
                asset=Asset.objects.create(name=f"asset-{i}", folder=folder),
                folder=folder,
            )
            for i in range(3)
        ]
        return folder, bia, assessments

    def test_batch_delete(self, authenticated_client, setup):
        folder, bia, assessments = setup
        EscalationThreshold.objects.create(
            asset_assessment=assessments[0], point_in_time=3600, folder=folder
        )

        response = authenticated_client.post(
            BATCH_ACTION_URL,
            {
                "action": "delete",
                "ids": [str(assessments[0].id), str(assessments[1].id)],
            },
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["succeeded"]) == 2
        assert data["failed"] == []
        remaining = AssetAssessment.objects.filter(bia=bia)
        assert list(remaining.values_list("id", flat=True)) == [assessments[2].id]
        assert not EscalationThreshold.objects.filter(
            asset_assessment=assessments[0]
        ).exists()

    def test_batch_delete_locked_bia(self, authenticated_client, setup):
        folder, bia, assessments = setup
        bia.is_locked = True
        bia.save()

        response = authenticated_client.post(
            BATCH_ACTION_URL,
            {"action": "delete", "ids": [str(assessments[0].id)]},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == []
        assert len(data["failed"]) == 1
        assert AssetAssessment.objects.filter(bia=bia).count() == 3

    def test_batch_delete_reader_forbidden(self, authenticated_client, setup):
        folder, bia, assessments = setup
        reader = client_for("reader@tests.com", "BI-UG-AUD", folder)

        response = reader.post(
            BATCH_ACTION_URL,
            {"action": "delete", "ids": [str(assessments[0].id)]},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == []
        assert len(data["failed"]) == 1
        assert AssetAssessment.objects.filter(bia=bia).count() == 3

    def test_batch_delete_authorized_by_delete_assetassessment(self, setup):
        folder, bia, assessments = setup
        client = client_with_role(
            "deleter@tests.com",
            folder,
            [
                "view_folder",
                "view_assetassessment",
                "delete_assetassessment",
            ],
        )

        response = client.post(
            BATCH_ACTION_URL,
            {"action": "delete", "ids": [str(assessments[0].id)]},
            format="json",
        )
        assert response.status_code == 200
        assert len(response.json()["succeeded"]) == 1
        assert AssetAssessment.objects.filter(bia=bia).count() == 2

    def test_batch_delete_not_authorized_without_delete_permission(self, setup):
        folder, bia, assessments = setup
        client = client_with_role(
            "adder@tests.com",
            folder,
            [
                "view_folder",
                "view_assetassessment",
                "add_assetassessment",
            ],
        )

        response = client.post(
            BATCH_ACTION_URL,
            {"action": "delete", "ids": [str(assessments[0].id)]},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == []
        assert len(data["failed"]) == 1
        assert AssetAssessment.objects.filter(bia=bia).count() == 3

    def test_single_delete_locked_bia(self, authenticated_client, setup):
        """Deletes bypass serializer validation, so the destroy flow needs its
        own lock check — a locked BIA must block per-row deletion too."""
        folder, bia, assessments = setup
        bia.is_locked = True
        bia.save()

        response = authenticated_client.delete(
            f"/api/resilience/asset-assessments/{assessments[0].id}/"
        )
        assert response.status_code == 400
        assert AssetAssessment.objects.filter(id=assessments[0].id).exists()

        bia.is_locked = False
        bia.save()
        response = authenticated_client.delete(
            f"/api/resilience/asset-assessments/{assessments[0].id}/"
        )
        assert response.status_code == 204
        assert not AssetAssessment.objects.filter(id=assessments[0].id).exists()
