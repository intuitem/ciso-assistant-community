import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient
from core.models import Asset, Perimeter, RiskMatrix, StoredLibrary
from iam.models import Folder, Permission, Role, RoleAssignment, User
from resilience.models import AssetAssessment, BusinessImpactAnalysis


def domain(name):
    return Folder.objects.create(
        name=name,
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )


def primary(name, folder, availability):
    return Asset.objects.create(
        name=name,
        type=Asset.Type.PRIMARY,
        folder=folder,
        security_objectives={
            "objectives": {"availability": {"value": availability, "is_enabled": True}}
        },
    )


def support(name, folder, availability, *parents):
    asset = Asset.objects.create(
        name=name,
        type=Asset.Type.SUPPORT,
        folder=folder,
        security_capabilities={
            "objectives": {"availability": {"value": availability, "is_enabled": True}}
        },
    )
    asset.parent_assets.add(*parents)
    return asset


@pytest.fixture
def bia():
    folder = domain("infra")
    StoredLibrary.objects.get(
        urn="urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm"
    ).load()
    return BusinessImpactAnalysis.objects.create(
        name="bia",
        perimeter=Perimeter.objects.create(name="p", folder=folder),
        folder=folder,
        risk_matrix=RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:risk-matrix-4x4-ebios-rm"
        ),
    )


@pytest.mark.django_db
def test_dependency_graph_separates_cause_from_impacted(authenticated_client, bia):
    folder = bia.folder
    service = primary("service", Folder.get_root_folder(), 3)
    app = support("app", folder, 4, service)
    db = support("db", folder, 1, app)
    backup = support("backup", folder, 4)
    aa = AssetAssessment.objects.create(bia=bia, asset=service, folder=folder)
    aa.dependencies.add(backup)

    response = authenticated_client.get(
        f"/api/resilience/asset-assessments/{aa.id}/dependency-graph/"
    )

    assert response.status_code == 200
    nodes = {n["label"]: n for n in response.json()["nodes"]}
    assert nodes["db"]["status"] == "cause"
    assert nodes["db"]["gaps"] == [
        {"objective": "availability", "expected": 3, "actual": 1}
    ]
    assert nodes["db"]["domain"] == str(folder.id)
    assert nodes["db"]["domain_name"] == "infra"
    assert nodes["app"]["status"] == "impacted"
    assert nodes["service"]["status"] == "impacted"
    assert nodes["service"]["causes"] == [str(db.id)]
    assert nodes["db"]["depth"] == 2
    assert nodes["backup"]["depth"] == 1
    links = response.json()["links"]
    assert sorted(link["extra"] for link in links) == [False, False, True]

    bia_response = authenticated_client.get(
        f"/api/resilience/business-impact-analysis/{bia.id}/dependency-graph/"
    )
    assert bia_response.status_code == 200
    assert bia_response.json()["roots"] == [str(service.id)]
    assert len(bia_response.json()["nodes"]) == 4


@pytest.mark.django_db
def test_primary_meeting_its_objective_lists_no_causes(authenticated_client, bia):
    demanding = primary("demanding", bia.folder, 3)
    relaxed = primary("relaxed", bia.folder, 1)
    shared = support("shared", bia.folder, 2, demanding, relaxed)
    for asset in (demanding, relaxed):
        AssetAssessment.objects.create(bia=bia, asset=asset, folder=bia.folder)

    response = authenticated_client.get(
        f"/api/resilience/business-impact-analysis/{bia.id}/dependency-graph/"
    )

    nodes = {n["label"]: n for n in response.json()["nodes"]}
    assert nodes["shared"]["status"] == "cause"
    assert nodes["demanding"]["causes"] == [str(shared.id)]
    assert nodes["relaxed"]["status"] == "ok"
    assert nodes["relaxed"]["causes"] == []


@pytest.mark.django_db
def test_dependency_graph_hides_assessed_asset_user_cannot_view(bia):
    hidden = domain("hidden")
    service = primary("service", hidden, 3)
    support("app", bia.folder, 1, service)
    aa = AssetAssessment.objects.create(bia=bia, asset=service, folder=bia.folder)
    user = User.objects.create_user("viewer@test.com")
    role = Role.objects.create(name="viewer", folder=Folder.get_root_folder())
    role.permissions.set(
        Permission.objects.filter(
            codename__in=["view_folder", "view_asset", "view_assetassessment"]
        )
    )
    assignment = RoleAssignment.objects.create(
        user=user, role=role, folder=Folder.get_root_folder(), is_recursive=True
    )
    assignment.perimeter_folders.add(bia.folder)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )

    response = client.get(
        f"/api/resilience/asset-assessments/{aa.id}/dependency-graph/"
    )

    assert response.status_code == 200
    assert [n["label"] for n in response.json()["nodes"]] == ["app"]
    assert response.json()["roots"] == []
    assert response.json()["nodes"][0]["depth"] == 1
