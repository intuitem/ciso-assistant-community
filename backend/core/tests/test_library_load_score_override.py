"""End-to-end test: load a YAML library that overrides scoring on some nodes
and verify the resulting Framework / RequirementNode objects.

Exercises the two override shapes:
- by reference into Framework.scores_definition["alternatives"]
- by inline override (escape hatch)
"""

from pathlib import Path

import pytest

from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
    StoredLibrary,
)
from iam.models import Folder

FIXTURE = Path(__file__).parent / "fixtures" / "test-mixed-scoring.yaml"


@pytest.mark.django_db
def test_yaml_library_load_creates_overrides():
    stored, err = StoredLibrary.store_library_content(FIXTURE.read_bytes())
    assert err is None
    assert stored is not None

    load_err = stored.load()
    assert load_err is None

    framework = Framework.objects.get(urn="urn:intuitem:test:framework:mixed-scoring")
    assert framework.min_score == 0
    assert framework.max_score == 5
    assert isinstance(framework.scores_definition, dict)
    assert framework.scores_definition.get("scale")
    assert framework.scores_definition.get("alternatives", {}).get("binary") is not None

    default_node = RequirementNode.objects.get(
        urn="urn:intuitem:test:req_node:mixed:default"
    )
    assert default_node.min_score is None
    assert default_node.max_score is None
    assert default_node.scores_definition is None

    binary_by_ref = RequirementNode.objects.get(
        urn="urn:intuitem:test:req_node:mixed:binary-by-ref"
    )
    assert binary_by_ref.min_score == 0
    assert binary_by_ref.max_score == 1
    # Stored as a bare string reference, not inlined.
    assert binary_by_ref.scores_definition == "binary"

    binary_inline = RequirementNode.objects.get(
        urn="urn:intuitem:test:req_node:mixed:binary-inline"
    )
    assert binary_inline.min_score == 0
    assert binary_inline.max_score == 1
    # YAML bare list gets wrapped to {"scale": [...]} on storage.
    assert isinstance(binary_inline.scores_definition, dict)
    assert binary_inline.scores_definition.get("scale")


@pytest.mark.django_db
def test_yaml_load_resolves_node_ref_through_ca():
    """Once the framework is loaded and a CA is created on it, the per-RA
    resolver looks the ref up in the CA's copy of scores_definition.alternatives.
    """
    stored, err = StoredLibrary.store_library_content(FIXTURE.read_bytes())
    assert err is None
    assert stored is not None
    load_err = stored.load()
    assert load_err is None

    framework = Framework.objects.get(urn="urn:intuitem:test:framework:mixed-scoring")

    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="mixed-load folder")
    perimeter = Perimeter.objects.create(name="mixed-load perimeter", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Mixed Load CA",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
    )

    # CA.save() copied the whole framework.scores_definition, including alternatives.
    assert ca.scores_definition.get("alternatives", {}).get("binary") is not None

    binary_node = RequirementNode.objects.get(
        urn="urn:intuitem:test:req_node:mixed:binary-by-ref"
    )
    ra = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=binary_node,
        folder=folder,
    )
    resolved = ra.get_resolved_scoring()
    assert resolved["min_score"] == 0
    assert resolved["max_score"] == 1
    # The ref resolved into the alternatives, returned as a bare list.
    assert isinstance(resolved["scores_definition"], list)
    assert {entry["score"] for entry in resolved["scores_definition"]} == {0, 1}
