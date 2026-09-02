import uuid

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import Evidence
from core.utils import UserGroupCodename
from iam.models import Folder, User, UserGroup


@pytest.fixture
def app_ready(db):
    startup(sender=None)
    return Folder.get_root_folder()


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _domain(root, name):
    folder = Folder.objects.create(
        name=name,
        parent_folder=root,
        content_type=Folder.ContentType.DOMAIN,
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(folder)
    return folder


@pytest.fixture
def readable_domain(app_ready):
    return _domain(app_ready, "Readable")


@pytest.fixture
def hidden_domain(app_ready):
    return _domain(app_ready, "Hidden")


@pytest.fixture
def reader_client(app_ready, readable_domain):
    user = User.objects.create_user("reader@multi-uuid.test", is_published=True)
    user.folder = app_ready
    user.save()
    group = UserGroup.objects.get(
        name=str(UserGroupCodename.READER), folder=readable_domain
    )
    group.user_set.add(user)
    return _client(user)


@pytest.fixture
def readable_evidence(readable_domain):
    return Evidence.objects.create(name="readable", folder=readable_domain)


@pytest.fixture
def hidden_evidence(hidden_domain):
    return Evidence.objects.create(name="hidden", folder=hidden_domain)


def test_single_readable_object_is_returned(reader_client, readable_evidence):
    resp = reader_client.get(f"/api/evidences/{readable_evidence.id}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(readable_evidence.id)


def test_single_hidden_object_is_not_found(reader_client, hidden_evidence):
    resp = reader_client.get(f"/api/evidences/{hidden_evidence.id}/")
    assert resp.status_code == 404


def test_comma_separated_uuids_in_path_is_not_found(
    reader_client, readable_evidence, hidden_evidence
):
    """A comma-separated UUID list is not a valid pk and must yield a 404, not a 500."""
    resp = reader_client.get(
        f"/api/evidences/{readable_evidence.id},{hidden_evidence.id}/"
    )
    assert resp.status_code == 404
    assert "readable" not in resp.content.decode()
    assert "hidden" not in resp.content.decode()


def test_comma_separated_uuids_in_path_with_two_readable_ids_is_not_found(
    reader_client, readable_domain, readable_evidence
):
    other = Evidence.objects.create(name="other", folder=readable_domain)
    resp = reader_client.get(f"/api/evidences/{readable_evidence.id},{other.id}/")
    assert resp.status_code == 404


def test_comma_separated_uuids_in_nested_path_is_not_found(reader_client):
    resp = reader_client.get(f"/api/ebios-rm/studies/{uuid.uuid4()},{uuid.uuid4()}/")
    assert resp.status_code == 404


def test_comma_separated_uuids_in_id_query_param_only_returns_readable(
    reader_client, readable_evidence, hidden_evidence
):
    """The frontend fetches several objects at once with ?id=<uuid>,<uuid>."""
    resp = reader_client.get(
        f"/api/evidences/?id={readable_evidence.id},{hidden_evidence.id}"
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert [r["id"] for r in results] == [str(readable_evidence.id)]
