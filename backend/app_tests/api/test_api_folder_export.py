"""The domains export only reveals what the caller may view."""

import csv
import io
import uuid

import pytest
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.models import FilteringLabel
from core.utils import RoleCodename
from iam.models import Folder, Permission, Role, RoleAssignment, User


def _client_with_role(role: Role) -> APIClient:
    user = User.objects.create_user(f"export-{uuid.uuid4().hex[:6]}@test.test")
    root = Folder.get_root_folder()
    assignment = RoleAssignment.objects.create(
        user=user, role=role, folder=root, is_recursive=True
    )
    assignment.perimeter_folders.add(root)
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _exported_labels(client) -> dict[str, str]:
    resp = client.get("/api/folders/export_csv/")
    assert resp.status_code == status.HTTP_200_OK, resp.content
    rows = csv.DictReader(io.StringIO(resp.content.decode("utf-8-sig")), delimiter=";")
    return {row["name"]: row["labels"] for row in rows}


@pytest.fixture
def labelled_domain():
    domain = Folder.objects.create(
        name=f"export-{uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    domain.filtering_labels.set([FilteringLabel.objects.create(label="Confidential")])
    return domain


@pytest.mark.django_db
class TestFolderExportLabelVisibility:
    def test_labels_hidden_without_label_view_permission(self, labelled_domain):
        role = Role.objects.create(name=f"folders-only-{uuid.uuid4().hex[:6]}")
        role.permissions.set([Permission.objects.get(codename="view_folder")])

        exported = _exported_labels(_client_with_role(role))

        assert exported[labelled_domain.name] == ""

    def test_labels_exported_with_label_view_permission(self, labelled_domain):
        reader = Role.objects.get(name=RoleCodename.READER.value)

        exported = _exported_labels(_client_with_role(reader))

        assert exported[labelled_domain.name] == "Confidential"
