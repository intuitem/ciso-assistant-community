import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from iam.models import Folder, User, UserGroup

enterprise_core = pytest.importorskip(
    "enterprise_core", reason="enterprise backend not on the path"
)
from enterprise_core.apps import startup as enterprise_startup  # noqa: E402
from enterprise_core.models import ClientSettings  # noqa: E402

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def app_ready(db):
    startup(sender=None)
    enterprise_startup(sender=None)
    return ClientSettings.objects.get()


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _in_group(email, group_name):
    user = User.objects.create_user(email, is_published=True)
    group = UserGroup.objects.get(name=group_name, folder=Folder.get_root_folder())
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    return _client(user)


@pytest.fixture
def admin_client(app_ready):
    return _in_group("admin@clientsettings.test", "BI-UG-ADM")


@pytest.fixture
def global_reader_client(app_ready):
    return _in_group("reader@clientsettings.test", "BI-UG-GAD")


@pytest.fixture
def norole_client(app_ready):
    user = User.objects.create_user("norole@clientsettings.test", is_published=True)
    user.folder = Folder.get_root_folder()
    user.save()
    return _client(user)


def _upload(client, settings_id, field, payload=PNG):
    return client.post(
        f"/api/client-settings/{settings_id}/{field}/upload/",
        data=payload,
        content_type="image/png",
        HTTP_CONTENT_DISPOSITION="attachment; filename=x.png",
    )


@pytest.mark.parametrize("field", ["logo", "favicon"])
def test_admin_can_upload(admin_client, app_ready, field):
    assert _upload(admin_client, app_ready.id, field).status_code == 200
    app_ready.refresh_from_db()
    assert getattr(app_ready, field)


@pytest.mark.parametrize("field", ["logo", "favicon"])
def test_global_reader_cannot_upload(global_reader_client, app_ready, field):
    assert _upload(global_reader_client, app_ready.id, field).status_code in (403, 404)
    app_ready.refresh_from_db()
    assert not getattr(app_ready, field)


@pytest.mark.parametrize("field", ["logo", "favicon"])
def test_user_without_role_cannot_upload(norole_client, app_ready, field):
    assert _upload(norole_client, app_ready.id, field).status_code in (403, 404)
    app_ready.refresh_from_db()
    assert not getattr(app_ready, field)


@pytest.mark.parametrize("field", ["logo", "favicon"])
def test_user_without_role_cannot_delete(admin_client, norole_client, app_ready, field):
    # Without an uploaded image handle_file_delete short-circuits to 403 anyway,
    # so the assertion below would hold even with no authorization at all.
    assert _upload(admin_client, app_ready.id, field).status_code == 200

    resp = norole_client.put(f"/api/client-settings/{app_ready.id}/{field}/delete/")
    assert resp.status_code in (403, 404)
    app_ready.refresh_from_db()
    assert getattr(app_ready, field)


def test_non_image_payload_is_rejected(admin_client, app_ready):
    resp = _upload(admin_client, app_ready.id, "logo", payload=b"<?php echo 1; ?>")
    assert resp.status_code == 400
    app_ready.refresh_from_db()
    assert not app_ready.logo
