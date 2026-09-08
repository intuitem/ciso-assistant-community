"""Multi-file evidence: actual multipart requests, storage and access boundaries."""

import hashlib
import io
import json
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from core.models import Evidence, EvidenceRevision, EvidenceAttachment
from iam.models import Folder, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def client(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_superuser(email="files@example.com", password="test")
    client = APIClient()
    client.force_authenticate(user)
    return client


def upload(name="proof.txt", content=b"proof"):
    return SimpleUploadedFile(name, content, content_type="text/plain")


def create(client, count=1, **metadata):
    data = {"name": "Evidence", "folder": str(Folder.get_root_folder().pk), **metadata}
    return client.post(
        "/api/evidences/",
        {
            "payload": json.dumps(data),
            "attachments": [
                upload(f"file-{i}.txt", str(i).encode()) for i in range(count)
            ],
        },
        format="multipart",
    )


def files(client, evidence_id):
    response = client.get(f"/api/evidences/{evidence_id}/")
    assert response.status_code == 200, response.data
    return response.data["attachments"]


def test_ten_files_one_revision_and_all_downloadable(client):
    response = create(client, 10)
    assert response.status_code == 201, response.data
    evidence = Evidence.objects.get(pk=response.data["id"])
    assert evidence.revisions.count() == 1
    assert evidence.last_revision.additional_attachments.count() == 9
    assert evidence.status == Evidence.Status.IN_REVIEW
    attachments = files(client, evidence.pk)
    assert len(attachments) == 10
    for index, file in enumerate(attachments):
        response = client.get(
            f"/api/evidence-revisions/{file['revision_id']}/attachments/{file['id']}/"
        )
        assert response.status_code == 200
        content = b"".join(response.streaming_content)
        assert content == str(index).encode()
        assert file["attachment_hash"] == hashlib.sha256(content).hexdigest()

    response = client.get(
        "/api/evidence-revisions/", {"evidence": str(evidence.pk)}
    )
    assert response.status_code == 200, response.data
    revision = next(
        item for item in response.data["results"] if item["id"] == str(evidence.last_revision.pk)
    )
    assert [item["filename"] for item in revision["attachments"]] == [
        f"file-{i}.txt" for i in range(10)
    ]


def test_eleven_files_rejected_without_rows_or_files(client, settings):
    response = create(client, 11)
    assert response.status_code == 400, response.data
    assert not Evidence.objects.exists()
    assert not list(settings.MEDIA_ROOT.rglob("*.txt"))


def test_invalid_file_rejects_entire_set(client, settings):
    response = client.post(
        "/api/evidences/",
        {
            "payload": json.dumps(
                {"name": "Bad file", "folder": str(Folder.get_root_folder().pk)}
            ),
            "attachments": [upload(), upload("bad.exe")],
        },
        format="multipart",
    )
    assert response.status_code == 400, response.data
    assert not Evidence.objects.exists()
    assert not list(settings.MEDIA_ROOT.rglob("*.txt"))


def test_append_preserves_primary_and_enforces_total(client):
    response = create(client, 9)
    assert response.status_code == 201, response.data
    evidence = Evidence.objects.get(pk=response.data["id"])
    revision = evidence.last_revision
    original = revision.attachment.name
    endpoint = f"/api/evidence-revisions/{revision.pk}/"
    response = client.patch(
        endpoint, {"payload": "{}", "attachments": [upload()]}, format="multipart"
    )
    assert response.status_code == 200, response.data
    assert len(files(client, evidence.pk)) == 10
    response = client.patch(
        endpoint, {"payload": "{}", "attachments": [upload()]}, format="multipart"
    )
    assert response.status_code == 400, response.data
    revision.refresh_from_db()
    assert revision.attachment.name == original
    assert len(files(client, evidence.pk)) == 10


def test_new_revision_keeps_old_file_set(client):
    result = create(client, 3)
    assert result.status_code == 201, result.data
    evidence = Evidence.objects.get(pk=result.data["id"])
    old = evidence.last_revision
    response = client.post(
        "/api/evidence-revisions/",
        {
            "payload": json.dumps(
                {"evidence": str(evidence.pk), "folder": str(evidence.folder_id)}
            ),
            "attachments": [upload("new.txt")],
        },
        format="multipart",
    )
    assert response.status_code == 201, response.data
    assert evidence.revisions.count() == 2
    assert len(list(old.attachment_items())) == 3
    assert len(files(client, evidence.pk)) == 1
    assert evidence.last_revision.version == 2


def test_legacy_single_upload_still_works(client):
    response = client.post(
        "/api/evidences/",
        {
            "name": "Legacy",
            "folder": str(Folder.get_root_folder().pk),
            "attachment": upload(),
        },
        format="multipart",
    )
    assert response.status_code == 201, response.data
    assert len(files(client, response.data["id"])) == 1


def test_delete_only_selected_and_cross_revision_id_rejected(
    client, django_capture_on_commit_callbacks
):
    from django.core.files.storage import default_storage

    result = create(client, 3)
    assert result.status_code == 201, result.data
    first = files(client, result.data["id"])
    other = create(client, 1, name="Other")
    assert other.status_code == 201, other.data
    second = files(client, other.data["id"])
    base = f"/api/evidence-revisions/{first[0]['revision_id']}/attachments/"
    assert client.get(f"{base}{second[0]['id']}/").status_code == 404
    deleted_name = EvidenceAttachment.objects.get(pk=first[1]["id"]).attachment.name
    assert default_storage.exists(deleted_name)
    with django_capture_on_commit_callbacks(execute=True):
        response = client.delete(f"{base}{first[1]['id']}/")
    assert response.status_code == 204, response.data
    assert not default_storage.exists(deleted_name)
    assert [f["id"] for f in files(client, result.data["id"])] == [
        first[0]["id"],
        first[2]["id"],
    ]


def test_storage_delete_failure_does_not_break_attachment_deletion(
    client, django_capture_on_commit_callbacks, monkeypatch
):
    result = create(client, 2)
    attachment = files(client, result.data["id"])[1]
    item = EvidenceAttachment.objects.get(pk=attachment["id"])

    def fail_delete(name):
        raise OSError("simulated delete failure")

    monkeypatch.setattr(item.attachment.storage, "delete", fail_delete)
    with django_capture_on_commit_callbacks(execute=True):
        response = client.delete(
            f"/api/evidence-revisions/{attachment['revision_id']}/attachments/{attachment['id']}/"
        )
    assert response.status_code == 204, response.data
    assert not EvidenceAttachment.objects.filter(pk=attachment["id"]).exists()


def test_unprivileged_user_cannot_read_or_mutate(client):
    result = create(client, 2)
    assert result.status_code == 201, result.data
    attachment = files(client, result.data["id"])[1]
    client.force_authenticate(
        User.objects.create_user(email="no-access@example.com", password="test")
    )
    endpoint = f"/api/evidence-revisions/{attachment['revision_id']}/attachments/{attachment['id']}/"
    assert client.get(endpoint).status_code in (403, 404)
    assert client.delete(endpoint).status_code in (403, 404)
    response = client.patch(
        f"/api/evidence-revisions/{attachment['revision_id']}/",
        {"attachments": [upload()]},
        format="multipart",
    )
    assert response.status_code in (403, 404)
    assert EvidenceAttachment.objects.count() == 1


def test_storage_failure_rolls_back_whole_upload(client, monkeypatch, settings):
    from django.core.files.storage import default_storage

    original = default_storage.save
    calls = 0

    def save(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated disk failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(default_storage, "save", save)
    with pytest.raises(OSError):
        create(client, 3)
    assert not Evidence.objects.exists()
    assert not list(settings.MEDIA_ROOT.rglob("*.txt"))


def test_same_name_hashes_actual_bytes(client):
    response = client.post(
        "/api/evidences/",
        {
            "payload": json.dumps(
                {"name": "Duplicates", "folder": str(Folder.get_root_folder().pk)}
            ),
            "attachments": [upload(content=b"first"), upload(content=b"second")],
        },
        format="multipart",
    )
    assert response.status_code == 201, response.data
    attachments = files(client, response.data["id"])
    assert len({file["filename"] for file in attachments}) == 2
    assert [file["attachment_hash"] for file in attachments] == [
        hashlib.sha256(x).hexdigest() for x in (b"first", b"second")
    ]


def test_backup_metadata_stream_and_restore_include_every_file(client):
    from django.core.files.storage import default_storage
    from core.evidence_files import get_backup_attachment

    result = create(client, 3)
    assert result.status_code == 201, result.data
    response = client.get("/serdes/attachment-metadata/?limit=2")
    assert response.status_code == 200, response.data
    assert response.data["count"] == 3
    metadata = response.data["results"]
    response = client.get("/serdes/attachment-metadata/?limit=2&offset=2")
    metadata += response.data["results"]
    ids = [item["id"] for item in metadata]
    response = client.post(
        "/serdes/batch-download-attachments/", {"revision_ids": ids}, format="json"
    )
    assert response.status_code == 200
    archive = b"".join(response.streaming_content)
    for pk in ids:
        default_storage.delete(get_backup_attachment(pk).attachment.name)
    response = client.post(
        "/serdes/batch-upload-attachments/",
        archive,
        content_type="application/octet-stream",
    )
    assert response.status_code == 200, response.data
    assert response.data["restored"] == 3, response.data
    assert not response.data["errors"]
    for pk in ids:
        item = get_backup_attachment(pk)
        with item.attachment.open("rb") as file:
            assert hashlib.sha256(file.read()).hexdigest() == item.attachment_hash


def test_domain_zip_round_trip_includes_additional_files(client, tmp_path):
    from serdes.domain_io import export_domain, process_uploaded_file, import_objects

    folder = Folder.objects.create(
        name="Evidence export", content_type=Folder.ContentType.DOMAIN
    )
    result = create(client, 3, folder=str(folder.pk))
    assert result.status_code == 201, result.data
    user = User.objects.get(email="files@example.com")
    response = export_domain(folder, user)
    archive = tmp_path / "domain.zip"
    archive.write_bytes(response.content)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zipped:
        assert (
            len([name for name in zipped.namelist() if name.startswith("attachments/")])
            == 3
        )
    parsed = process_uploaded_file(archive)
    assert (
        len(
            [
                obj
                for obj in parsed["objects"]
                if obj["model"] == "core.evidenceattachment"
            ]
        )
        == 2
    )
    import_objects(parsed, "Restored evidence", False, user)
    restored = Evidence.objects.exclude(folder=folder).get(name="Evidence")
    assert len(list(restored.last_revision.attachment_items())) == 3
    for item in restored.last_revision.attachment_items():
        with item.attachment.open("rb") as file:
            assert hashlib.sha256(file.read()).hexdigest() == item.attachment_hash


def test_domain_import_rejects_tampered_attachment_and_cleans_staged_files(
    client, settings, tmp_path
):
    from django.forms import ValidationError

    from serdes.domain_io import export_domain, process_uploaded_file

    folder = Folder.objects.create(
        name="Tampered evidence export", content_type=Folder.ContentType.DOMAIN
    )
    result = create(client, 3, folder=str(folder.pk))
    assert result.status_code == 201, result.data
    user = User.objects.get(email="files@example.com")
    exported = export_domain(folder, user).content
    source = io.BytesIO(exported)
    tampered = io.BytesIO()
    with zipfile.ZipFile(source) as input_zip, zipfile.ZipFile(
        tampered, "w", zipfile.ZIP_DEFLATED
    ) as output_zip:
        data = json.loads(input_zip.read("data.json"))
        additional = next(
            obj
            for obj in data["objects"]
            if obj["model"] == "core.evidenceattachment"
        )
        additional["fields"]["attachment_hash"] = "0" * 64
        for info in input_zip.infolist():
            content = (
                json.dumps(data).encode()
                if info.filename == "data.json"
                else input_zip.read(info)
            )
            output_zip.writestr(info, content)

    archive = tmp_path / "tampered-domain.zip"
    archive.write_bytes(tampered.getvalue())
    files_before = {path for path in settings.MEDIA_ROOT.rglob("*") if path.is_file()}
    with pytest.raises(ValidationError) as error:
        process_uploaded_file(archive)
    assert "evidenceAttachmentHashMismatch" in str(error.value)
    files_after = {path for path in settings.MEDIA_ROOT.rglob("*") if path.is_file()}
    assert files_after == files_before


def test_domain_import_failure_cleans_staged_attachment_files(
    client, monkeypatch, tmp_path
):
    from django.core.files.storage import default_storage
    from django.forms import ValidationError

    from serdes import domain_io

    folder = Folder.objects.create(
        name="Failed evidence import", content_type=Folder.ContentType.DOMAIN
    )
    result = create(client, 3, folder=str(folder.pk))
    assert result.status_code == 201, result.data
    user = User.objects.get(email="files@example.com")
    archive = tmp_path / "failed-domain.zip"
    archive.write_bytes(domain_io.export_domain(folder, user).content)
    parsed = domain_io.process_uploaded_file(archive)
    staged = list(parsed[domain_io.STAGED_ATTACHMENT_PATHS_KEY])
    assert staged and all(default_storage.exists(name) for name in staged)

    def fail_create(*args, **kwargs):
        raise RuntimeError("simulated import failure")

    monkeypatch.setattr(domain_io, "create_model_objects", fail_create)
    with pytest.raises(ValidationError):
        domain_io.import_objects(parsed, "Failed import", False, user)
    assert all(not default_storage.exists(name) for name in staged)


def test_reader_can_download_but_cannot_remove_or_append(client):
    from iam.models import UserGroup

    result = create(client, 2)
    assert result.status_code == 201, result.data
    attachment = files(client, result.data["id"])[1]
    reader = User.objects.create_user(email="reader@example.com", password="test")
    UserGroup.objects.get(name="BI-UG-GAD").user_set.add(reader)
    client.force_authenticate(reader)
    endpoint = f"/api/evidence-revisions/{attachment['revision_id']}/attachments/{attachment['id']}/"
    response = client.get(endpoint)
    assert response.status_code == 200
    assert b"".join(response.streaming_content)
    assert client.delete(endpoint).status_code == 403
    response = client.patch(
        f"/api/evidence-revisions/{attachment['revision_id']}/",
        {"attachments": [upload()]},
        format="multipart",
    )
    assert response.status_code == 403, response.data


def test_delete_primary_keeps_other_files_and_allows_append(
    client, django_capture_on_commit_callbacks
):
    result = create(client, 3)
    before = files(client, result.data["id"])
    endpoint = f"/api/evidence-revisions/{before[0]['revision_id']}"
    with django_capture_on_commit_callbacks(execute=True):
        response = client.delete(f"{endpoint}/attachments/{before[0]['id']}/")
    assert response.status_code == 204
    assert files(client, result.data["id"]) == before[1:]
    response = client.patch(
        f"{endpoint}/", {"attachments": [upload()]}, format="multipart"
    )
    assert response.status_code == 200, response.data
    assert len(files(client, result.data["id"])) == 3


def test_overflow_with_legacy_replacement_rolls_back_file_and_metadata(
    client, settings
):
    result = create(client, 10)
    before = files(client, result.data["id"])
    names = set(settings.MEDIA_ROOT.rglob("*.txt"))
    response = client.patch(
        f"/api/evidence-revisions/{before[0]['revision_id']}/",
        {
            "attachment": upload("replacement.txt"),
            "attachments": [upload("extra.txt")],
            "observation": "must roll back",
        },
        format="multipart",
    )
    assert response.status_code == 400, response.data
    assert files(client, result.data["id"]) == before
    assert set(settings.MEDIA_ROOT.rglob("*.txt")) == names
    assert EvidenceRevision.objects.get(pk=before[0]["revision_id"]).observation is None
