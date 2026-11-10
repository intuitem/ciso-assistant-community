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
