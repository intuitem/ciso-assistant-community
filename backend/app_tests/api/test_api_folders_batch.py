import pytest
from rest_framework.test import APIClient

from iam.models import Folder, User

URL = "/api/folders/batch-action/"


@pytest.fixture
def nested_domains(db) -> dict:
    """A three-level chain under the root: parent > child > grandchild."""
    root = Folder.get_root_folder()
    parent = Folder.objects.create(
        parent_folder=root, name="Parent", content_type=Folder.ContentType.DOMAIN
    )
    child = Folder.objects.create(
        parent_folder=parent, name="Child", content_type=Folder.ContentType.DOMAIN
    )
    grandchild = Folder.objects.create(
        parent_folder=child, name="Grandchild", content_type=Folder.ContentType.DOMAIN
    )
    admin = User.objects.create_superuser("folders-admin@tests.com")
    client = APIClient()
    client.force_authenticate(admin)
    return {
        "client": client,
        "parent": parent,
        "child": child,
        "grandchild": grandchild,
    }


def test_deleting_a_parent_before_its_children_reports_them_all_as_deleted(
    nested_domains: dict,
) -> None:
    """The parent's cascade removes the rows the batch has yet to reach; they must
    not come back as a permission denial, which is what the caller sees otherwise.
    """
    ordered = [
        nested_domains["parent"],
        nested_domains["child"],
        nested_domains["grandchild"],
    ]
    res = nested_domains["client"].post(
        URL, {"action": "delete", "ids": [str(f.id) for f in ordered]}, format="json"
    )

    assert res.status_code == 200, res.json()
    body = res.json()
    assert body["failed"] == []
    assert {entry["id"] for entry in body["succeeded"]} == {str(f.id) for f in ordered}
    assert not Folder.objects.filter(id__in=[f.id for f in ordered]).exists()


def test_deleting_a_parent_alone_cascades_onto_its_sub_domains(
    nested_domains: dict,
) -> None:
    parent = nested_domains["parent"]
    res = nested_domains["client"].post(
        URL, {"action": "delete", "ids": [str(parent.id)]}, format="json"
    )

    assert res.status_code == 200, res.json()
    assert res.json()["failed"] == []
    assert not Folder.objects.filter(
        id__in=[parent.id, nested_domains["child"].id, nested_domains["grandchild"].id]
    ).exists()


def test_the_root_folder_is_never_deleted(nested_domains: dict) -> None:
    root = Folder.get_root_folder()
    res = nested_domains["client"].post(
        URL, {"action": "delete", "ids": [str(root.id)]}, format="json"
    )

    assert res.status_code == 200, res.json()
    assert res.json()["succeeded"] == []
    assert Folder.objects.filter(id=root.id).exists()
