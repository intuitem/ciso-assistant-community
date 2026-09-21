"""The mapping engine must not outlive the request that built it.

A module-level instance is one cache per gunicorn worker, refreshed only in
the worker that handled the write, so the others answer from a graph that
predates a library loaded elsewhere (#4791).
"""

import pytest
from rest_framework import status

from core.models import StoredLibrary

SRC = "urn:intuitem:risk:framework:iso27001-2022"
TGT = "urn:noshared:risk:framework:target"


def _mapping_library(source_urn: str) -> StoredLibrary:
    return StoredLibrary(
        urn="urn:noshared:risk:library:mapping",
        ref_id="noshared-mapping",
        name="No shared cache",
        provider="test",
        packager="test",
        locale="en",
        default_locale=True,
        version=1,
        is_loaded=True,
        objects_meta={},
        hash_checksum="0" * 64,
        content={
            "requirement_mapping_set": {
                "urn": "urn:noshared:risk:req_mapping_set:mapping",
                "source_framework_urn": source_urn,
                "target_framework_urn": TGT,
                "requirement_mappings": [],
            }
        },
    )


def test_the_module_exposes_no_shared_engine():
    import core.mappings.engine as engine_module

    assert not hasattr(engine_module, "engine"), (
        "a module-level instance is one cache per worker, never invalidated"
    )


@pytest.mark.django_db
def test_a_new_engine_sees_a_library_stored_without_its_signal():
    from core.mappings.engine import MappingEngine

    assert (SRC, TGT) not in MappingEngine().direct_mappings

    # bulk_create sends no post_save, which is what another worker's write
    # looks like from here.
    StoredLibrary.objects.bulk_create([_mapping_library(SRC)])

    assert (SRC, TGT) in MappingEngine().direct_mappings


@pytest.mark.django_db
def test_creating_an_audit_from_a_baseline_with_no_mapping_path_does_not_fail(
    authenticated_client,
):
    """#4791: the audit is created, it is simply not pre-filled.

    `best_mapping_inferences` legitimately returns an empty dict when the two
    frameworks are unrelated, and the result used to be indexed without a
    guard.
    """
    from core.models import ComplianceAssessment, Framework, Perimeter
    from iam.models import Folder

    folder = Folder.objects.create(
        name="no-mapping-path", parent_folder=Folder.get_root_folder()
    )
    perimeter = Perimeter.objects.create(name="no-mapping-path", folder=folder)
    source = Framework.objects.create(
        urn="urn:noshared:risk:framework:source", name="Source", folder=folder
    )
    target = Framework.objects.create(
        urn="urn:noshared:risk:framework:unrelated", name="Unrelated", folder=folder
    )
    baseline = ComplianceAssessment.objects.create(
        name="baseline", perimeter=perimeter, framework=source, folder=folder
    )

    response = authenticated_client.post(
        "/api/compliance-assessments/",
        {
            "name": "derived",
            "perimeter": str(perimeter.id),
            "framework": str(target.id),
            "baseline": str(baseline.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data


@pytest.mark.django_db
def test_creating_an_audit_from_a_baseline_applies_the_mapping(authenticated_client):
    """The happy path of #4791: results are carried over to the new audit.

    `map_from` already covers cross-framework merging, but the baseline flow
    goes through `perform_create`, which is where the crash was.
    """
    import uuid

    from core.models import (
        ComplianceAssessment,
        Framework,
        Perimeter,
        RequirementAssessment,
        RequirementNode,
    )
    from iam.models import Folder

    root = Folder.get_root_folder()
    perimeter = Perimeter.objects.create(name=f"p-{uuid.uuid4().hex[:6]}", folder=root)

    def framework(slug):
        return Framework.objects.create(
            folder=root,
            name=slug,
            ref_id=slug,
            urn=f"urn:baseline:risk:framework:{slug}",
            min_score=0,
            max_score=100,
        )

    def requirement(fw, ref_id):
        return RequirementNode.objects.create(
            folder=root,
            framework=fw,
            urn=f"{fw.urn}:req:{ref_id}",
            ref_id=ref_id,
            name=f"requirement {ref_id}",
            assessable=True,
        )

    src_fw, tgt_fw = framework("baseline-src"), framework("baseline-tgt")
    requirement(src_fw, "A")
    requirement(tgt_fw, "X")

    StoredLibrary.objects.create(
        urn="urn:baseline:risk:library:mapping",
        ref_id="baseline-mapping",
        name="Baseline mapping",
        provider="test",
        packager="test",
        locale="en",
        default_locale=True,
        version=1,
        is_loaded=True,
        objects_meta={},
        hash_checksum="1" * 64,
        content={
            "requirement_mapping_set": {
                "urn": "urn:baseline:risk:req_mapping_set:mapping",
                "name": "Baseline mapping",
                "source_framework_urn": src_fw.urn,
                "target_framework_urn": tgt_fw.urn,
                "requirement_mappings": [
                    {
                        "source_requirement_urn": f"{src_fw.urn}:req:A",
                        "target_requirement_urn": f"{tgt_fw.urn}:req:X",
                        "relationship": "equal",
                    }
                ],
            }
        },
    )

    baseline = ComplianceAssessment.objects.create(
        name="baseline", perimeter=perimeter, framework=src_fw, folder=root
    )
    baseline.create_requirement_assessments()
    answered = baseline.requirement_assessments.get(requirement__ref_id="A")
    answered.result = RequirementAssessment.Result.COMPLIANT
    answered.save()

    response = authenticated_client.post(
        "/api/compliance-assessments/",
        {
            "name": "derived",
            "perimeter": str(perimeter.id),
            "framework": str(tgt_fw.id),
            "baseline": str(baseline.id),
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED, response.data

    derived = ComplianceAssessment.objects.get(id=response.data["id"])
    carried = derived.requirement_assessments.get(requirement__ref_id="X")
    assert carried.result == RequirementAssessment.Result.COMPLIANT
