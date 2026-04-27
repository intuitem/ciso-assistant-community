"""Tests for knowledge_graph.py — framework resolution and graph queries."""

import pytest

from chat.knowledge_graph import DiGraph, _resolve_framework, format_graph_result


@pytest.fixture
def small_graph():
    """Minimal graph with 3 frameworks for testing."""
    G = DiGraph()
    G.add_node(
        "urn:intuitem:risk:framework:c3cf-ed1-v1",
        node_type="framework",
        name="Cadre de Conformité Cyber France (3CF) pour l'aviation civile",
        ref_id="3CF-ed1-v1",
        provider="DSAC",
        locale="fr",
    )
    G.add_node(
        "urn:intuitem:risk:framework:aircyber-v1.5.2",
        node_type="framework",
        name="Public AirCyber Maturity Level Matrix",
        ref_id="AirCyber-v1.5.2",
        provider="BoostAeroSpace",
        locale="en",
    )
    G.add_node(
        "urn:intuitem:risk:framework:iso27001-2022",
        node_type="framework",
        name="ISO/IEC 27001:2022",
        ref_id="ISO-27001-2022",
        provider="ISO",
        locale="en",
    )
    # Non-framework node (should be ignored by _resolve_framework)
    G.add_node(
        "urn:intuitem:risk:req:some-requirement",
        node_type="requirement_node",
        name="3CF requirement about cyber",
        ref_id="3CF-01",
    )
    return G


class TestResolveFramework:
    def test_exact_urn(self, small_graph):
        urn = "urn:intuitem:risk:framework:c3cf-ed1-v1"
        assert _resolve_framework(small_graph, urn) == urn

    def test_exact_ref_id(self, small_graph):
        result = _resolve_framework(small_graph, "3CF-ed1-v1")
        assert result == "urn:intuitem:risk:framework:c3cf-ed1-v1"

    def test_exact_ref_id_case_insensitive(self, small_graph):
        result = _resolve_framework(small_graph, "3cf-ed1-v1")
        assert result == "urn:intuitem:risk:framework:c3cf-ed1-v1"

    def test_partial_ref_id_3cf(self, small_graph):
        result = _resolve_framework(small_graph, "3CF")
        assert result == "urn:intuitem:risk:framework:c3cf-ed1-v1"

    def test_partial_name_aircyber(self, small_graph):
        result = _resolve_framework(small_graph, "AirCyber")
        assert result == "urn:intuitem:risk:framework:aircyber-v1.5.2"

    def test_partial_ref_id_iso(self, small_graph):
        result = _resolve_framework(small_graph, "ISO-27001")
        assert result == "urn:intuitem:risk:framework:iso27001-2022"

    def test_partial_name_27001(self, small_graph):
        # "27001" appears in both name and ref_id
        result = _resolve_framework(small_graph, "27001")
        assert result == "urn:intuitem:risk:framework:iso27001-2022"

    def test_empty_identifier(self, small_graph):
        assert _resolve_framework(small_graph, "") is None

    def test_no_match_returns_none(self, small_graph):
        assert _resolve_framework(small_graph, "NIST CSF") is None

    def test_short_common_words_no_match(self, small_graph):
        assert _resolve_framework(small_graph, "la") is None
        assert _resolve_framework(small_graph, "the") is None
        assert _resolve_framework(small_graph, "entre") is None

    def test_does_not_match_non_framework_nodes(self, small_graph):
        # "3CF-01" doesn't substring-match "3CF-ed1-v1"
        result = _resolve_framework(small_graph, "3CF-01")
        assert result is None

    def test_best_score_uses_ref_id_over_name(self, small_graph):
        # "3CF" in ref_id "3CF-ed1-v1" → 3/10=0.3
        # "3CF" in name (62 chars) → 3/62≈0.048
        # Should use the higher score (ref_id)
        result = _resolve_framework(small_graph, "3CF")
        assert result is not None


class TestDigraph:
    def test_add_node_and_get(self):
        G = DiGraph()
        G.add_node("a", color="red")
        assert "a" in G
        assert G["a"]["color"] == "red"

    def test_add_edge(self):
        G = DiGraph()
        G.add_edge("a", "b", weight=1)
        edges = list(G.out_edges("a", data=True))
        assert len(edges) == 1
        assert edges[0] == ("a", "b", {"weight": 1})

    def test_in_edges(self):
        G = DiGraph()
        G.add_edge("a", "b", rel="parent")
        edges = list(G.in_edges("b", data=True))
        assert len(edges) == 1
        assert edges[0] == ("a", "b", {"rel": "parent"})

    def test_nodes_with_data(self):
        G = DiGraph()
        G.add_node("x", val=1)
        G.add_node("y", val=2)
        nodes = dict(G.nodes(data=True))
        assert nodes["x"]["val"] == 1
        assert nodes["y"]["val"] == 2

    def test_contains(self):
        G = DiGraph()
        G.add_node("x")
        assert "x" in G
        assert "y" not in G

    def test_get_nonexistent(self):
        G = DiGraph()
        assert G.get("missing") is None


class TestFormatGraphResult:
    def test_none(self):
        assert format_graph_result(None) == "No results found."

    def test_empty_list(self):
        assert format_graph_result([]) == "No results found."

    def test_dict(self):
        result = format_graph_result({"name": "test", "count": 5})
        assert "name: test" in result
        assert "count: 5" in result

    def test_list_of_dicts(self):
        result = format_graph_result([{"name": "a"}, {"name": "b"}])
        assert "name: a" in result
        assert "name: b" in result

    def test_skips_empty_values(self):
        result = format_graph_result(
            {"name": "test", "empty": "", "null": None, "blank": []}
        )
        assert "empty" not in result
        assert "null" not in result
        assert "blank" not in result
