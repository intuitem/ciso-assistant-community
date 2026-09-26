"""Custom audit scale (preset reference) in domain export / import."""

import io

import pytest

from core.models import ComplianceAssessment, Framework, StoredLibrary
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from serdes.domain_io import export_domain, import_objects, process_uploaded_file


_LIBRARY = """
urn: urn:intuitem:test:library:ssx
locale: en
ref_id: SSX
name: SSX
description: SSX
copyright: Test
version: 1
publication_date: 2026-09-26
provider: test
packager: test
objects:
  framework:
    urn: urn:intuitem:test:framework:ssx
    ref_id: SSX
    name: SSX Framework
    description: SSX
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:ssx:req-1
      assessable: true
      depth: 1
      ref_id: REQ-1
      name: Requirement 1
""".lstrip()


@pytest.fixture
def admin_user():
    root = Folder.get_root_folder()
    user = User.objects.create_user("score-scale-export@test.com")
    group = UserGroup.objects.create(name="ssx-admins", folder=root)
    group.user_set.add(user)
    RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name="BI-RL-ADM"),
        folder=root,
        is_recursive=True,
    ).perimeter_folders.add(root)
    return user


@pytest.mark.django_db
def test_preset_survives_export_import(admin_user):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        name="SSX Source", parent_folder=root, content_type=Folder.ContentType.DOMAIN
    )
    stored, _ = StoredLibrary.store_library_content(_LIBRARY.encode("utf-8"))
    stored.load()
    framework = Framework.objects.get(urn="urn:intuitem:test:framework:ssx")
    reworded = [{"score": 3, "translations": {"fr": {"name": "Moyen"}}}]
    audit = ComplianceAssessment.objects.create(
        name="SSX Audit",
        framework=framework,
        folder=domain,
        score_scale_preset="1-5",
        min_score=1,
        max_score=5,
        scores_definition=reworded,
    )
    audit.create_requirement_assessments()

    response = export_domain(domain, admin_user)
    assert response.status_code == 200
    json_dump = process_uploaded_file(io.BytesIO(response.content))
    Folder.objects.filter(name="SSX Source").delete()

    result = import_objects(
        json_dump,
        domain_name="SSX Imported",
        load_missing_libraries=True,
        user=admin_user,
    )
    assert result["message"] == "Import successful"

    imported = ComplianceAssessment.objects.get(folder__name="SSX Imported")
    assert (imported.min_score, imported.max_score) == (1, 5)
    assert imported.score_scale_preset == "1-5"
    assert imported.scores_definition == reworded
    levels = imported.get_scale_levels()
    assert [lvl["score"] for lvl in levels] == [1, 2, 3, 4, 5]
    assert all(lvl["preset"] == "1-5" for lvl in levels)
