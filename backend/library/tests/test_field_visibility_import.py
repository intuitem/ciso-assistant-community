"""Framework `field_visibility` template: YAML import and CA seeding."""

import pytest
from core.models import ComplianceAssessment, Framework, Perimeter, StoredLibrary
from core.utils import build_initial_field_visibility, is_field_visible_to
from iam.models import Folder

LIB_WITH_FIELD_VISIBILITY = """
urn: urn:test:risk:library:fv-lib
locale: en
ref_id: FV-LIB
name: Field visibility test library
description: Framework carrying a field_visibility template
version: 1
publication_date: 2026-07-24
copyright: test
provider: test
packager: test
objects:
  framework:
    urn: urn:test:risk:framework:fv-lib
    ref_id: FV-LIB
    name: Field visibility test framework
    description: test
    min_score: 1
    max_score: 5
    field_visibility:
      score:
        auditor: edit
        respondent: hidden
      is_scored:
        auditor: edit
        respondent: hidden
      result:
        auditor: hidden
        respondent: hidden
      extended_result:
        auditor: hidden
        respondent: hidden
    requirement_nodes:
    - urn: urn:test:risk:req_node:fv-lib:1
      assessable: true
      depth: 1
      ref_id: '1'
      name: Requirement one
""".lstrip().encode("utf-8")


@pytest.mark.django_db
def test_field_visibility_imports_and_seeds_new_assessments():
    stored, error = StoredLibrary.store_library_content(LIB_WITH_FIELD_VISIBILITY)
    assert error is None, error
    assert stored.load() is None

    fw = Framework.objects.get(urn="urn:test:risk:framework:fv-lib")
    assert fw.field_visibility["score"] == {"auditor": "edit", "respondent": "hidden"}
    assert fw.field_visibility["result"] == {
        "auditor": "hidden",
        "respondent": "hidden",
    }

    folder = Folder.get_root_folder()
    perimeter = Perimeter.objects.create(name="P", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="CA",
        framework=fw,
        perimeter=perimeter,
        folder=folder,
        field_visibility=build_initial_field_visibility(fw),
    )
    assert ca.scoring_enabled is True
    assert ca.extended_result_enabled is False
    assert ca.progress_status_enabled is True
    assert is_field_visible_to(ca, "result", "auditor") is False
    assert is_field_visible_to(ca, "score", "auditor") is True
    assert is_field_visible_to(ca, "answers", "respondent") is True


@pytest.mark.django_db
def test_framework_without_field_visibility_gets_empty_template():
    lib = LIB_WITH_FIELD_VISIBILITY.replace(b"fv-lib", b"fv-lib2")
    lib = b"\n".join(
        line
        for line in lib.split(b"\n")
        if b"field_visibility" not in line
        and b"auditor:" not in line
        and b"respondent:" not in line
        and not line.strip().startswith(b"score:")
        and not line.strip().startswith(b"is_scored:")
        and not line.strip().startswith(b"result:")
        and not line.strip().startswith(b"extended_result:")
    )
    stored, error = StoredLibrary.store_library_content(lib)
    assert error is None, error
    assert stored.load() is None

    fw = Framework.objects.get(urn="urn:test:risk:framework:fv-lib2")
    assert fw.field_visibility == {}
    template = build_initial_field_visibility(fw)
    assert template["score"] == {"auditor": "hidden", "respondent": "hidden"}
