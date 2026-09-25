import pytest
from rest_framework.test import APIClient

from core.models import ClassificationLevel, FilteringLabel, ObjectClassification
from doc_management.models import DocumentContainer, ManagedDocument
from iam.models import Folder, User

URL = "/api/document-containers/batch-action/"


@pytest.fixture
def setup(db):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        parent_folder=root, name="Docs", content_type=Folder.ContentType.DOMAIN
    )
    other_domain = Folder.objects.create(
        parent_folder=root, name="Other", content_type=Folder.ContentType.DOMAIN
    )
    containers = [
        DocumentContainer.objects.create(name=f"Doc {i}", folder=domain)
        for i in range(3)
    ]
    admin = User.objects.create_superuser("docs-admin@tests.com")
    client = APIClient()
    client.force_authenticate(admin)
    return {
        "domain": domain,
        "other_domain": other_domain,
        "containers": containers,
        "ids": [str(c.id) for c in containers],
        "client": client,
    }


def post(setup, **payload):
    res = setup["client"].post(URL, {"ids": setup["ids"], **payload}, format="json")
    assert res.status_code == 200, res.json()
    assert not res.json().get("failed"), res.json()
    return res


def test_change_document_type(setup):
    post(setup, action="change_field", field="document_type", value="procedure")
    for c in setup["containers"]:
        c.refresh_from_db()
        assert c.document_type == "procedure"


def test_change_and_clear_classification(setup):
    oc = ObjectClassification.objects.create(name="Sensitivity")
    level = ClassificationLevel.objects.create(
        name="Confidential", object_classification=oc, folder=Folder.get_root_folder()
    )
    post(setup, action="change_field", field="classification", value=str(level.id))
    for c in setup["containers"]:
        c.refresh_from_db()
        assert c.classification == level

    post(setup, action="change_field", field="classification", value=None)
    for c in setup["containers"]:
        c.refresh_from_db()
        assert c.classification is None


def test_add_and_remove_labels(setup):
    a = FilteringLabel.objects.create(label="a")
    b = FilteringLabel.objects.create(label="b")
    setup["containers"][0].filtering_labels.add(a)

    post(setup, action="add_m2m", field="filtering_labels", value=[str(b.id)])
    assert set(setup["containers"][0].filtering_labels.all()) == {a, b}
    assert set(setup["containers"][1].filtering_labels.all()) == {b}

    post(setup, action="remove_m2m", field="filtering_labels", value=[str(b.id)])
    assert set(setup["containers"][0].filtering_labels.all()) == {a}
    assert not setup["containers"][1].filtering_labels.exists()


def test_change_domain_moves_documents(setup):
    doc = ManagedDocument.objects.create(
        container=setup["containers"][0], folder=setup["domain"]
    )
    post(setup, action="change_folder", value=str(setup["other_domain"].id))
    for c in setup["containers"]:
        c.refresh_from_db()
        assert c.folder == setup["other_domain"]
    doc.refresh_from_db()
    assert doc.folder == setup["other_domain"]


def test_delete(setup):
    post(setup, action="delete")
    assert not DocumentContainer.objects.filter(id__in=setup["ids"]).exists()
