"""BIO2 v1.2 (`bio2`) <-> BIO2 v1.3 (`bio2-v1.3`), lets a v1.2 audit carry over to v1.3."""

from pathlib import Path

import pytest
import yaml
from core.mappings.engine import MappingEngine
from core.models import LoadedLibrary, RequirementNode, StoredLibrary

LIBRARIES_DIR = Path(__file__).resolve().parents[2] / "library" / "libraries"
MAPPING = "mapping-bio2-and-bio2-v1.3"
V12 = "urn:intuitem:risk:framework:bio2"
V13 = "urn:intuitem:risk:framework:bio2-v1.3"
V12_NODE = "urn:intuitem:risk:req_node:bio2:"
V13_NODE = "urn:intuitem:risk:req_node:bio2-v1.3:"


def load(ref_id):
    urn = f"urn:intuitem:risk:library:{ref_id}"
    if not LoadedLibrary.objects.filter(urn=urn).exists():
        stored = StoredLibrary.objects.filter(urn=urn).first()
        if stored is None:
            content = (LIBRARIES_DIR / f"{ref_id}.yaml").read_bytes()
            stored, error = StoredLibrary.store_library_content(content)
            assert error is None, f"could not store {ref_id}: {error}"
        assert stored.load() is None


@pytest.fixture
def libraries(db):
    for ref_id in ("bio2", "bio2-v1.3", MAPPING):
        load(ref_id)


@pytest.fixture(scope="module")
def forward():
    content = yaml.safe_load((LIBRARIES_DIR / f"{MAPPING}.yaml").read_text())
    return content["objects"]["requirement_mapping_sets"][0]["requirement_mappings"]


def audit(framework_urn, result="compliant", overrides=None):
    """Every requirement done with `result`, except the ref_ids in `overrides`."""
    overrides = overrides or {}
    nodes = RequirementNode.objects.filter(
        framework__urn=framework_urn, assessable=True
    )
    return {
        "min_score": 0,
        "max_score": 100,
        "requirement_assessments": {
            n.urn: {
                "result": overrides.get(n.ref_id, result),
                "status": "done",
                "name": n.ref_id,
                "id": str(n.id),
                "source_framework": {},
            }
            for n in nodes
        },
    }


@pytest.mark.django_db
class TestBio2V13Mapping:
    def test_mapping_links_existing_requirements(self, libraries, forward):
        urns = {r["source_requirement_urn"] for r in forward} | {
            r["target_requirement_urn"] for r in forward
        }
        assert urns == set(
            RequirementNode.objects.filter(urn__in=urns).values_list("urn", flat=True)
        )

    def test_every_v13_requirement_is_reached(self, libraries, forward):
        v13 = set(
            RequirementNode.objects.filter(
                framework__urn=V13, assessable=True
            ).values_list("urn", flat=True)
        )
        assert len(v13) == 117
        assert v13 == {r["target_requirement_urn"] for r in forward}

    def test_v12_audit_carries_over_to_v13(self, libraries):
        inferences, path = MappingEngine().best_mapping_inferences(audit(V12), V12, V13)
        assert path == [V12, V13]
        mapped = inferences["requirement_assessments"]
        assert {RequirementNode.objects.get(urn=u).framework.urn for u in mapped} == {
            V13
        }

    def test_v13_audit_maps_back_to_v12(self, libraries):
        inferences, path = MappingEngine().best_mapping_inferences(audit(V13), V13, V12)
        assert path == [V13, V12]
        mapped = set(inferences["requirement_assessments"])
        # Cancelled in v1.3 without a successor, so nothing maps back to them
        assert {V12_NODE + "5.35.01", V12_NODE + "7.01.01"}.isdisjoint(mapped)
        assert len(mapped) == 118

    def test_broader_v13_requirements_are_left_for_review(self, libraries):
        """A complete v1.2 audit must not close what v1.3 added (board adoption, Cbw...)."""
        inferences, _ = MappingEngine().best_mapping_inferences(audit(V12), V12, V13)
        mapped = inferences["requirement_assessments"]
        for ref_id in ("5.01.01", "5.02.01", "5.14.01"):
            target = mapped[V13_NODE + ref_id]
            assert target["result"] != "compliant", ref_id
            assert target.get("status") != "done", ref_id
        # an unchanged requirement still carries its status over
        assert mapped[V13_NODE + "5.10.02"]["status"] == "done"

    def test_full_links_carry_result_and_status(self, libraries):
        source = audit(
            V12,
            overrides={
                "5.04.02": "non_compliant",  # equal, renumbered to 5.10.02
                "5.01.02": "not_applicable",  # equal, same ref_id
                "8.01.02": "partially_compliant",  # superset of 8.01.02 and 6.03.04
            },
        )
        inferences, _ = MappingEngine().best_mapping_inferences(source, V12, V13)
        mapped = inferences["requirement_assessments"]
        for ref_id, expected in [
            ("5.10.02", "non_compliant"),
            ("5.01.02", "not_applicable"),
            ("8.01.02", "partially_compliant"),
            ("6.03.04", "partially_compliant"),
        ]:
            assert mapped[V13_NODE + ref_id]["result"] == expected, ref_id
            assert mapped[V13_NODE + ref_id]["status"] == "done", ref_id

    def test_reverse_partial_links_are_left_for_review(self, libraries):
        inferences, _ = MappingEngine().best_mapping_inferences(audit(V13), V13, V12)
        mapped = inferences["requirement_assessments"]
        # reversed superset: v1.3 5.14.01 covers v1.2 5.14.01 entirely
        assert mapped[V12_NODE + "5.14.01"]["result"] == "compliant"
        assert mapped[V12_NODE + "5.14.01"]["status"] == "done"
        # reached only through reversed subset (8.01.02) or intersect (5.01.01) links
        for ref_id in ("8.01.02", "5.01.01"):
            assert mapped[V12_NODE + ref_id]["result"] != "compliant", ref_id
            assert mapped[V12_NODE + ref_id].get("status") != "done", ref_id

    def test_absorbed_measures_only_lower_their_target(self, libraries):
        source = audit(
            V12, overrides={"7.10.02": "non_compliant", "5.21.01": "non_compliant"}
        )
        inferences, _ = MappingEngine().best_mapping_inferences(source, V12, V13)
        mapped = inferences["requirement_assessments"]
        # v1.3 7.10.01 keeps the v1.2 7.10.01 text: the 7.10.02 gap stays on check and report
        assert mapped[V13_NODE + "7.10.01"]["result"] == "compliant"
        assert mapped[V13_NODE + "7.10.02"]["result"] == "non_compliant"
        # 5.21.01 is described in 5.21.03: the gap lowers it, and it stays closed
        assert mapped[V13_NODE + "5.21.03"]["result"] == "non_compliant"
        assert mapped[V13_NODE + "5.21.03"]["status"] == "done"

    def test_v13_drops_implementation_groups(self, libraries):
        framework = RequirementNode.objects.filter(framework__urn=V13).first().framework
        assert not framework.implementation_groups_definition


@pytest.mark.parametrize(
    "old,new",
    [
        ("5.04.02", "5.10.02"),
        ("5.04.03", "5.10.03"),
        ("5.24.06", "5.21.05"),
        ("8.08.06", "5.24.08"),
        ("5.25.01", "5.26.02"),
    ],
)
def test_renumbered_requirements_map_as_equal(forward, old, new):
    rows = [r for r in forward if r["source_requirement_urn"] == V12_NODE + old]
    assert [(r["target_requirement_urn"], r["relationship"]) for r in rows] == [
        (V13_NODE + new, "equal")
    ]


@pytest.mark.parametrize(
    "old,new",
    [
        ("5.01.01", "5.02.01"),
        ("5.21.01", "5.21.03"),
        ("8.01.02", "6.03.04"),
        ("8.24.03", "8.24.01"),
    ],
)
def test_official_revision_history_is_followed(forward, old, new):
    """Each move listed in the BIO2 v1.3 revision history has its mapping row."""
    assert any(
        r["source_requirement_urn"] == V12_NODE + old
        and r["target_requirement_urn"] == V13_NODE + new
        for r in forward
    )
