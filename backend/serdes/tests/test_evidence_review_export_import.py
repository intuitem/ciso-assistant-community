"""An approved evidence survives a domain export / import round-trip with its decision."""

import io

import pytest

from core.models import Evidence, EvidenceRevision
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from serdes.domain_io import export_domain, import_objects, process_uploaded_file


@pytest.fixture
def admin_user():
    root = Folder.get_root_folder()
    user = User.objects.create_user("evidence-review-export@test.com")
    group = UserGroup.objects.create(name="erx-admins", folder=root)
    group.user_set.add(user)
    RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-ADM"),
        folder=root,
        is_recursive=True,
    ).perimeter_folders.add(root)
    return user


@pytest.mark.django_db
def test_round_trip_keeps_the_decision(admin_user):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        name="ERX Source", parent_folder=root, content_type=Folder.ContentType.DOMAIN
    )
    evidence = Evidence.objects.create(name="ERX Pen test", folder=domain)
    revision = EvidenceRevision.objects.create(
        evidence=evidence, link="https://example.com/report"
    )
    revision.record_review(admin_user, "approved", "covers all hosts")

    json_dump = process_uploaded_file(
        io.BytesIO(export_domain(domain, admin_user).content)
    )
    domain.delete()
    result = import_objects(
        json_dump,
        domain_name="ERX Imported",
        load_missing_libraries=True,
        user=admin_user,
    )
    assert result["message"] == "Import successful"

    imported = Evidence.objects.get(folder__name="ERX Imported")
    assert imported.status == Evidence.Status.APPROVED
    rev = imported.revisions.get()
    assert rev.review_status == EvidenceRevision.ReviewStatus.APPROVED
    assert rev.review_comment == "covers all hosts"
    assert rev.reviewed_at is not None


def _restore(user, revision, file_bytes):
    import hashlib
    import json
    import struct

    from django.urls import reverse
    from rest_framework.test import APIClient

    header = json.dumps(
        {
            "id": str(revision.id),
            "filename": "report.txt",
            "hash": hashlib.sha256(file_bytes).hexdigest(),
        }
    ).encode()
    block = header + file_bytes
    client = APIClient()
    client.force_authenticate(user)
    return client.post(
        reverse("batch-upload-attachments"),
        data=struct.pack(">I", len(block)) + block,
        content_type="application/octet-stream",
    )


@pytest.mark.django_db
@pytest.mark.parametrize("same_bytes", [True, False])
def test_restoring_other_bytes_voids_the_decision(admin_user, same_bytes):
    from django.core.files.uploadedfile import SimpleUploadedFile

    evidence = Evidence.objects.create(
        name="ERX Restore", folder=Folder.get_root_folder()
    )
    revision = EvidenceRevision.objects.create(
        evidence=evidence,
        attachment=SimpleUploadedFile("report.txt", b"reviewed bytes"),
    )
    revision.record_review(admin_user, "approved", "")
    revision.refresh_from_db()
    # Lose the stored file so the restore cannot skip on a hash match.
    revision.attachment.storage.delete(revision.attachment.name)

    response = _restore(
        admin_user, revision, b"reviewed bytes" if same_bytes else b"other bytes"
    )
    assert response.status_code == 200, response.content
    assert response.json()["restored"] == 1, response.json()

    revision.refresh_from_db()
    evidence.refresh_from_db()
    if same_bytes:
        assert revision.review_status == EvidenceRevision.ReviewStatus.APPROVED
        assert evidence.status == Evidence.Status.APPROVED
    else:
        assert revision.review_status == EvidenceRevision.ReviewStatus.PENDING
        assert evidence.status == Evidence.Status.IN_REVIEW
