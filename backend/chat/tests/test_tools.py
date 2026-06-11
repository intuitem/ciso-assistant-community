"""Tests for tools.py — argument sanitization and framework detection."""

import pytest

pytestmark = pytest.mark.django_db


class TestSanitizeArguments:
    def test_removes_null_values(self):
        from chat.tools import _sanitize_arguments

        result = _sanitize_arguments({"model": "asset", "status": None, "search": ""})
        assert "status" not in result
        assert "search" not in result
        assert result["model"] == "asset"

    def test_preserves_valid_values(self):
        from chat.tools import _sanitize_arguments

        result = _sanitize_arguments(
            {"model": "asset", "action": "list", "search": "test"}
        )
        assert result["model"] == "asset"
        assert result["action"] == "list"
        assert result["search"] == "test"

    def test_coerces_string_to_list(self):
        from chat.tools import _sanitize_arguments

        result = _sanitize_arguments(
            {"model": "asset", "has_related": "applied_control"}
        )
        assert result.get("has_related") == ["applied_control"]


class TestDetectFrameworkNames:
    @pytest.fixture(autouse=True)
    def setup_test_graph(self, monkeypatch):
        """Inject a small test graph instead of building from YAML."""
        from chat.knowledge_graph import DiGraph
        import chat.knowledge_graph as kg

        G = DiGraph()
        G.add_node(
            "urn:test:framework:3cf",
            node_type="framework",
            name="Cadre de Conformité Cyber France (3CF)",
            ref_id="3CF-ed1-v1",
        )
        G.add_node(
            "urn:test:framework:aircyber",
            node_type="framework",
            name="Public AirCyber Maturity Level Matrix",
            ref_id="AirCyber-v1.5.2",
        )
        G.add_node(
            "urn:test:framework:iso27001",
            node_type="framework",
            name="ISO/IEC 27001:2022",
            ref_id="ISO-27001-2022",
        )
        monkeypatch.setattr(kg, "_graph", G)

    def test_detects_two_frameworks(self):
        from chat.tools import _detect_framework_names

        result = _detect_framework_names(
            "c'est quoi la différence entre le 3CF et AirCyber?"
        )
        assert len(result) == 2

    def test_detects_single_framework(self):
        from chat.tools import _detect_framework_names

        result = _detect_framework_names("qu'est-ce que le 3CF?")
        assert len(result) == 1

    def test_no_frameworks(self):
        from chat.tools import _detect_framework_names

        result = _detect_framework_names("comment ça marche?")
        assert len(result) == 0

    def test_short_words_no_false_positive(self):
        from chat.tools import _detect_framework_names

        result = _detect_framework_names("la différence entre les deux")
        assert len(result) == 0

    def test_multiword_framework(self):
        from chat.tools import _detect_framework_names

        result = _detect_framework_names("tell me about ISO-27001")
        assert len(result) == 1

    def test_empty_input(self):
        from chat.tools import _detect_framework_names

        assert _detect_framework_names("") == []
