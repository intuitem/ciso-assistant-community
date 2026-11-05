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


_SCALED_LIBRARY = """
urn: urn:intuitem:test:library:ssy
locale: en
ref_id: SSY
name: SSY
description: SSY
copyright: Test
version: 1
publication_date: 2026-09-26
provider: test
packager: test
objects:
  framework:
    urn: urn:intuitem:test:framework:ssy
    ref_id: SSY
    name: SSY Framework
    description: SSY
    min_score: 1
    max_score: 4
    scores_definition:
    - score: 1
      name: Low
    - score: 4
      name: High
    requirement_nodes:
    - urn: urn:intuitem:test:req_node:ssy:req-1
      assessable: true
      depth: 1
      ref_id: REQ-1
      name: Requirement 1
""".lstrip()


def _export_scaled_audit(admin_user):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        name="SSY Source", parent_folder=root, content_type=Folder.ContentType.DOMAIN
    )
    stored, _ = StoredLibrary.store_library_content(_SCALED_LIBRARY.encode("utf-8"))
    stored.load()
    framework = Framework.objects.get(urn="urn:intuitem:test:framework:ssy")
    ComplianceAssessment.objects.create(
        name="SSY Audit",
        framework=framework,
        folder=domain,
        min_score=1,
        max_score=4,
        scores_definition=[],
    ).create_requirement_assessments()
    response = export_domain(domain, admin_user)
    assert response.status_code == 200
    json_dump = process_uploaded_file(io.BytesIO(response.content))
    Folder.objects.filter(name="SSY Source").delete()
    return framework, json_dump


def _audit_fields(json_dump):
    return next(
        obj["fields"]
        for obj in json_dump["objects"]
        if obj["model"] == "core.complianceassessment"
    )


def _import(json_dump, admin_user):
    return import_objects(
        json_dump,
        domain_name="SSY Imported",
        load_missing_libraries=True,
        user=admin_user,
    )


@pytest.mark.django_db
def test_export_predating_presets_gets_framework_labels(admin_user):
    framework, json_dump = _export_scaled_audit(admin_user)
    _audit_fields(json_dump).pop("score_scale_preset")

    _import(json_dump, admin_user)

    imported = ComplianceAssessment.objects.get(folder__name="SSY Imported")
    assert imported.scores_definition == framework.scores_definition


@pytest.mark.django_db
def test_current_export_keeps_empty_labels(admin_user):
    _, json_dump = _export_scaled_audit(admin_user)

    _import(json_dump, admin_user)

    imported = ComplianceAssessment.objects.get(folder__name="SSY Imported")
    assert not imported.scores_definition


@pytest.mark.django_db
def test_unknown_preset_is_refused(admin_user):
    from django.core.exceptions import ValidationError

    _, json_dump = _export_scaled_audit(admin_user)
    _audit_fields(json_dump)["score_scale_preset"] = "9-9"

    with pytest.raises(ValidationError):
        _import(json_dump, admin_user)
    assert not ComplianceAssessment.objects.filter(folder__name="SSY Imported").exists()
