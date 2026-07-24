import pytest
from core.models import Asset, Perimeter, RiskMatrix, StoredLibrary
from iam.models import Folder
from resilience.models import AssetAssessment, BusinessImpactAnalysis

BATCH_CREATE_URL = "/api/resilience/asset-assessments/batch-create/"


@pytest.mark.django_db
class TestAssetAssessmentsBatchCreate:
    @pytest.fixture
    def setup(self):
        folder = Folder.objects.create(
            name="test-domain",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=Folder.get_root_folder(),
        )
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
