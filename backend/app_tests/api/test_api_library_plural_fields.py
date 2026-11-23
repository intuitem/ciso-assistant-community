"""Libraries may spell their object fields singular (legacy: "framework",
"risk_matrix", "requirement_mapping_set") or plural (what the library builder
and the converters write). Every reader must accept both."""

import pytest
import yaml
from django.urls import reverse

from chat.knowledge_graph import DiGraph, _process_library
from chat.tasks import _parse_library_yaml
from core.models import StoredLibrary

A_FW = "urn:test:risk:framework:plural-a"
B_FW = "urn:test:risk:framework:singular-b"


def _library(ref_id, provider, objects):
    return {
        "urn": f"urn:test:risk:library:{ref_id}",
        "locale": "en",
        "ref_id": ref_id,
        "name": f"Library {ref_id}",
        "description": "d",
        "copyright": "c",
        "version": 1,
        "provider": provider,
        "packager": "test",
        "objects": objects,
    }


def _framework(urn, name, ref):
    return {
        "urn": urn,
        "ref_id": ref,
        "name": name,
        "description": f"{name} description",
        "requirement_nodes": [
            {
                "urn": f"urn:test:risk:req_node:{ref}:1",
                "ref_id": "1",
                "name": f"{name} requirement",
                "assessable": True,
                "depth": 1,
            }
        ],
    }


def _mapping_set(ref, source, target):
    return {
        "urn": f"urn:test:risk:req_mapping_set:{ref}",
        "ref_id": ref,
        "name": ref,
        "source_framework_urn": source,
        "target_framework_urn": target,
        "requirement_mappings": [
            {
                "source_requirement_urn": f"{source.replace(':framework:', ':req_node:')}:1",
                "target_requirement_urn": f"{target.replace(':framework:', ':req_node:')}:1",
                "relationship": "equal",
            }
        ],
    }


PLURAL_FRAMEWORK = _library(
    "plural-a",
    "test",
    {"frameworks": [_framework(A_FW, "Framework A plural", "plural-a")]},
)
SINGULAR_FRAMEWORK = _library(
    "singular-b",
    "test",
    {"framework": _framework(B_FW, "Framework B singular", "singular-b")},
)
PLURAL_MAPPING = _library(
    "plural-map",
    "plural-provider",
    {
        "requirement_mapping_sets": [
            _mapping_set("a-to-b", A_FW, B_FW),
            _mapping_set("b-to-a", B_FW, A_FW),
        ]
    },
)
SINGULAR_MAPPING = _library(
    "singular-map",
    "singular-provider",
    {"requirement_mapping_set": _mapping_set("b-to-a-legacy", B_FW, A_FW)},
)


def _store(document):
    stored, error = StoredLibrary.store_library_content(
        yaml.safe_dump(document).encode()
    )
    assert error is None, error
    return stored


@pytest.fixture
def libraries():
    plural = _store(PLURAL_FRAMEWORK)
    singular = _store(SINGULAR_FRAMEWORK)
    mapping = _store(PLURAL_MAPPING)
    legacy_mapping = _store(SINGULAR_MAPPING)
    mapping.is_loaded = True  # the mapping engine only reads loaded sets
    mapping.save()
    return plural, singular, mapping, legacy_mapping


@pytest.mark.django_db
class TestPluralFieldsApi:
    def test_mapping_set_list_resolves_framework_names(
        self, authenticated_client, libraries
    ):
        res = authenticated_client.get(reverse("requirement-mapping-sets-list"))
        assert res.status_code == 200, res.content
        row = next(r for r in res.json()["results"] if r["ref_id"] == "plural-map")
        assert row["source_framework"]["str"] == "Framework A plural"
        assert row["target_framework"]["str"] == "Framework B singular"
        assert row["frameworks_available"] is True

    def test_mapping_set_retrieve_resolves_framework_names(
        self, authenticated_client, libraries
    ):
        _, _, mapping, _ = libraries
        res = authenticated_client.get(
            reverse("requirement-mapping-sets-detail", args=[mapping.pk])
        )
        assert res.status_code == 200, res.content
        assert res.json()["source_framework"]["str"] == "Framework A plural"

    @pytest.mark.parametrize("view", ["graph_data", "table_data"])
    def test_mapping_set_detail_views(self, authenticated_client, libraries, view):
        _, _, mapping, _ = libraries
        res = authenticated_client.get(
            reverse("requirement-mapping-sets-detail", args=[mapping.pk]) + f"{view}/"
        )
        assert res.status_code == 200, res.content

    def test_mapping_graph_names_plural_framework(
        self, authenticated_client, libraries
    ):
        plural, *_ = libraries
        assert plural.load() is None  # graph paths start from imported frameworks
        res = authenticated_client.get(
            reverse("requirement-mapping-sets-list") + "graph-data/"
        )
        assert res.status_code == 200, res.content
        names = {n["urn"]: n["name"] for n in res.json()["nodes"]}
        assert names[A_FW] == "Framework A plural"

    def test_stored_library_tree_of_plural_framework(
        self, authenticated_client, libraries
    ):
        plural, *_ = libraries
        res = authenticated_client.get(
            reverse("stored-libraries-detail", args=[plural.pk]) + "tree/"
        )
        assert res.status_code == 200, res.content
        assert res.json()

    def test_object_type_filter_matches_both_spellings(
        self, authenticated_client, libraries
    ):
        # Callers ask with the plural; legacy singular libraries still match.
        res = authenticated_client.get(
            reverse("stored-libraries-list"), {"object_type": "frameworks"}
        )
        assert res.status_code == 200, res.content
        ref_ids = {r["ref_id"] for r in res.json()["results"]}
        assert {"plural-a", "singular-b"} <= ref_ids

    def test_mapping_provider_choices_cover_both_spellings(
        self, authenticated_client, libraries
    ):
        res = authenticated_client.get(
            reverse("requirement-mapping-sets-list") + "provider/"
        )
        assert res.status_code == 200, res.content
        assert {"plural-provider", "singular-provider"} <= set(res.json())


class TestPluralFieldsChat:
    def test_knowledge_graph_reads_plural_fields(self):
        graph = DiGraph()
        _process_library(graph, PLURAL_FRAMEWORK)
        _process_library(graph, PLURAL_MAPPING)
        assert graph[A_FW]["name"] == "Framework A plural"
        assert "urn:test:risk:req_node:plural-a:1" in graph
        mapped = {
            (src, dst)
            for fw in (A_FW, B_FW)
            for src, dst, attrs in graph.out_edges(fw, data=True)
            if attrs.get("edge_type") == "has_mapping"
        }
        assert mapped == {(A_FW, B_FW), (B_FW, A_FW)}

    def test_knowledge_graph_still_reads_singular_fields(self):
        graph = DiGraph()
        _process_library(graph, SINGULAR_FRAMEWORK)
        _process_library(graph, SINGULAR_MAPPING)
        assert graph[B_FW]["name"] == "Framework B singular"
        assert (B_FW, A_FW) in {(src, dst) for src, dst in graph.out_edges(B_FW)}

    @pytest.mark.parametrize("document", [PLURAL_FRAMEWORK, SINGULAR_FRAMEWORK])
    def test_rag_index_reads_requirement_nodes(self, tmp_path, document):
        path = tmp_path / "library.yaml"
        path.write_text(yaml.safe_dump(document))
        entries = _parse_library_yaml(path)
        assert [e["object_type"] for e in entries].count("requirement_node") == 1
