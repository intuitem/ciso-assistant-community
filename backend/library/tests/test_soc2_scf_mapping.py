"""Guards the alignment of the SOC 2 / SCF mapping with the SOC 2 framework nodes."""

from pathlib import Path

import pytest

from core.utils import yaml_safe_load

LIBRARIES = Path(__file__).resolve().parents[1] / "libraries"
NODE = "urn:intuitem:risk:req_node:soc2-2017-rev-2022:"
SCF = "urn:intuitem:risk:req_node:scf-2025.2.2:"


def load(name):
    return yaml_safe_load((LIBRARIES / name).read_text())


@pytest.fixture(scope="module")
def nodes():
    framework = load("soc2_2017_with_rev_2022.yaml")["objects"]["framework"]
    return {node["urn"]: node for node in framework["requirement_nodes"]}


@pytest.fixture(scope="module")
def mapping_sets():
    return load("mapping-soc2-2017-rev-2022-and-scf-2025.2.2.yaml")["objects"][
        "requirement_mapping_sets"
    ]


def test_every_mapped_urn_is_a_framework_node(nodes, mapping_sets):
    scf = {
        node["urn"]
        for node in load("scf-2025.2.2.yaml")["objects"]["framework"][
            "requirement_nodes"
        ]
    }
    known = nodes.keys() | scf
    assert len(mapping_sets) == 2
    for mapping_set in mapping_sets:
        dangling = {
            urn
            for row in mapping_set["requirement_mappings"]
            for urn in (row["source_requirement_urn"], row["target_requirement_urn"])
            if urn not in known
        }
        assert not dangling, mapping_set["urn"]


def test_every_assessable_node_is_mapped(nodes, mapping_sets):
    mapped = {
        row["source_requirement_urn"] for row in mapping_sets[0]["requirement_mappings"]
    }
    assert not {u for u, node in nodes.items() if node["assessable"]} - mapped


def test_points_of_focus_map_to_the_controls_of_their_own_wording(nodes, mapping_sets):
    targets = {}
    for row in mapping_sets[0]["requirement_mappings"]:
        targets.setdefault(row["source_requirement_urn"], set()).add(
            row["target_requirement_urn"]
        )
    # The STRM numbers these one higher: the framework merges its threats point
    assert "Identifies Threats" in nodes[f"{NODE}cc3.2.5"]["description"]
    assert f"{SCF}thr-01" in targets[f"{NODE}cc3.2.5"]
    assert "Identifies Vulnerability" in nodes[f"{NODE}cc3.2.6"]["description"]
    assert f"{SCF}vpm-01" in targets[f"{NODE}cc3.2.6"]
    assert "From Vendors" in nodes[f"{NODE}cc3.2.7"]["description"]
    assert f"{SCF}tpm-02" in targets[f"{NODE}cc3.2.7"]
    assert "Assesses the Significance" in nodes[f"{NODE}cc3.2.8"]["description"]
    assert f"{SCF}vpm-03.1" in targets[f"{NODE}cc3.2.8"]


@pytest.mark.parametrize(
    "suffix,ref_id",
    [(f"pp1.{i}", f"PI1.{i}") for i in range(1, 6)] + [("c6.5.1", "CC6.5.1")],
)
def test_misspelled_urns_stay_put(nodes, suffix, ref_id):
    """A framework update deletes dropped nodes, and their assessments with them."""
    assert nodes[f"{NODE}{suffix}"]["ref_id"] == ref_id


def test_merged_threats_point_is_only_a_partial_match(mapping_sets):
    relationships = {
        row["relationship"]
        for row in mapping_sets[0]["requirement_mappings"]
        if row["source_requirement_urn"] == f"{NODE}cc3.2.5"
        and row["target_requirement_urn"] == f"{SCF}thr-01"
    }
    assert relationships == {"intersect"}
