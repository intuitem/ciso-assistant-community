import pytest
from iam.models import Folder, User, UserGroup
from knox.models import AuthToken
from rest_framework.test import APIClient
from crq.models import QuantitativeRiskStudy
from tprm.models import Entity

from core.apps import startup
from core.models import AppliedControl, Asset, FilteringLabel


@pytest.fixture
def admin_client():
    startup(sender=None)
    admin = User.objects.create_superuser(
        "admin@label-usage-tests.com", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


@pytest.fixture
def labels():
    root = Folder.get_root_folder()
    pci, pci_alias, unused = (
        FilteringLabel.objects.create(label=name, folder=root)
        for name in ("pci-dss", "PCI_DSS", "legacy")
    )
    control = AppliedControl.objects.create(name="Firewall review", folder=root)
    asset = Asset.objects.create(name="POS hub", folder=root)
    entity = Entity.objects.create(name="Acquirer", folder=root)
    control.filtering_labels.add(pci, pci_alias)
    asset.filtering_labels.add(pci_alias)
    entity.filtering_labels.add(pci)
    return {"pci": pci, "alias": pci_alias, "unused": unused, "asset": asset}


def _labels(client, **params):
    res = client.get("/api/filtering-labels/", {"offset": 0, **params})
    assert res.status_code == 200
    return {r["label"]: r["usage_count"] for r in res.json()["results"]}


@pytest.mark.django_db
def test_usage_count_spans_object_types(admin_client, labels):
    assert _labels(admin_client) == {"PCI_DSS": 2, "legacy": 0, "pci-dss": 2}


@pytest.mark.django_db
def test_usage_filters(admin_client, labels):
    assert set(_labels(admin_client, usage="unused")) == {"legacy"}
    assert set(_labels(admin_client, usage="rare")) == {"PCI_DSS", "pci-dss"}
    assert set(_labels(admin_client, usage="lookalike")) == {"PCI_DSS", "pci-dss"}


@pytest.mark.django_db
def test_merge_relabels_and_deletes_sources(admin_client, labels):
    res = admin_client.post(
        "/api/filtering-labels/merge/",
        {"target": str(labels["pci"].id), "sources": [str(labels["alias"].id)]},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["merged"] == 1
    assert res.json()["relabelled"] == 1
    assert not FilteringLabel.objects.filter(id=labels["alias"].id).exists()
    assert labels["pci"] in labels["asset"].filtering_labels.all()
    assert _labels(admin_client) == {"legacy": 0, "pci-dss": 3}


@pytest.mark.django_db
def test_merge_rejects_unknown_source(admin_client, labels):
    res = admin_client.post(
        "/api/filtering-labels/merge/",
        {
            "target": str(labels["pci"].id),
            "sources": ["00000000-0000-0000-0000-000000000000"],
        },
        format="json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_usage_per_type(admin_client, labels):
    res = admin_client.get(f"/api/filtering-labels/{labels['alias'].id}/usage/")
    assert res.status_code == 200
    counts = {k: v for k, v in res.json().items() if v}
    assert counts == {"appliedcontrol": 1, "asset": 1}


@pytest.mark.django_db
def test_assessment_level_objects_take_labels(admin_client, labels):
    study = QuantitativeRiskStudy.objects.create(
        name="Card fraud", folder=Folder.get_root_folder()
    )
    study.filtering_labels.add(labels["unused"])
    assert _labels(admin_client)["legacy"] == 1
    res = admin_client.get(f"/api/filtering-labels/{labels['unused'].id}/usage/")
    assert res.json()["quantitativeriskstudy"] == 1
    res = admin_client.get(
        "/api/crq/quantitative-risk-studies/",
        {"filtering_labels": str(labels["unused"].id)},
    )
    assert [r["name"] for r in res.json()["results"]] == ["Card fraud"]
    assert res.json()["results"][0]["filtering_labels"][0]["str"] == "legacy"


@pytest.mark.django_db
def test_merge_rejects_non_list_sources(admin_client, labels):
    res = admin_client.post(
        "/api/filtering-labels/merge/",
        {"target": str(labels["pci"].id), "sources": 5},
        format="json",
    )
    assert res.status_code == 400


@pytest.mark.django_db
def test_retrieve_includes_usage_count(admin_client, labels):
    res = admin_client.get(f"/api/filtering-labels/{labels['alias'].id}/")
    assert res.json()["usage_count"] == 2
