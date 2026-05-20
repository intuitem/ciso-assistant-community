"""End-to-end test: load a YAML library that overrides scoring on some nodes
and verify the resulting Framework / RequirementNode objects.
"""

from pathlib import Path

import pytest

from core.models import Framework, RequirementNode, StoredLibrary

FIXTURE = Path(__file__).parent / "fixtures" / "test-mixed-scoring.yaml"


@pytest.mark.django_db
def test_yaml_library_load_creates_overrides():
    stored, err = StoredLibrary.store_library_content(FIXTURE.read_bytes())
    assert err is None
    assert stored is not None

    load_err = stored.load()
    assert load_err is None

    framework = Framework.objects.get(
        urn="urn:intuitem:test:framework:mixed-scoring"
    )
    assert framework.min_score == 0
    assert framework.max_score == 5

    default_node = RequirementNode.objects.get(
        urn="urn:intuitem:test:req_node:mixed:default"
    )
    assert default_node.min_score is None
    assert default_node.max_score is None
    assert default_node.scores_definition is None
    assert default_node.target_score is None

    binary_node = RequirementNode.objects.get(
        urn="urn:intuitem:test:req_node:mixed:binary"
    )
    assert binary_node.min_score == 0
    assert binary_node.max_score == 1
    # scores_definition is wrapped in {"scale": [...]} at storage time
    assert isinstance(binary_node.scores_definition, dict)
    assert binary_node.scores_definition.get("scale")
    assert binary_node.target_score == 1

    target_only = RequirementNode.objects.get(
        urn="urn:intuitem:test:req_node:mixed:target-only"
    )
    assert target_only.min_score is None
    assert target_only.max_score is None
    assert target_only.target_score == 4
