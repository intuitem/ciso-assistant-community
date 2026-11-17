import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

import chat.providers as providers
import chat.rag as rag
from iam.models import User

pytestmark = pytest.mark.django_db


class _Embedder:
    def embed_query(self, _text):
        return [1.0, 0.0]

    def embed(self, texts):
        self.calls = getattr(self, "calls", 0) + len(texts)
        return [[1.0, 0.0] for _ in texts]


@pytest.fixture
def client(monkeypatch):
    client = QdrantClient(":memory:")
    client.create_collection(
        rag.COLLECTION_NAME,
        vectors_config=VectorParams(size=2, distance=Distance.COSINE),
    )
    monkeypatch.setattr(rag, "get_qdrant_client", lambda: client)
    monkeypatch.setattr(rag, "_get_reranker", lambda: None)
    monkeypatch.setattr(providers, "get_embedder", _Embedder)
    return client


class _Reranker:
    def predict(self, pairs):
        return [float("DORA" in text) for _, text in pairs]


def test_named_framework_reaches_the_reranker(client, monkeypatch):
    monkeypatch.setattr(rag, "_get_reranker", _Reranker)
    lib = {"source_type": "library", "object_type": "requirement_node"}
    client.upsert(
        rag.COLLECTION_NAME,
        points=[
            PointStruct(
                id=i,
                vector=[1.0, 0.0],
                payload={**lib, "framework": "ISO", "text": "ISO"},
            )
            for i in range(1, 7)
        ]
        + [
            PointStruct(
                id=7,
                vector=[0.0, 1.0],
                payload={**lib, "framework": "DORA", "text": "DORA"},
            )
        ],
    )
    user = User.objects.create(email="rag-library@test.local")

    def top(**kw):
        return rag.search("q", user, top_k=1, **kw)[0]["framework"]

    assert top() == "ISO"
    assert top(frameworks=["DORA"]) == "DORA"


def test_library_reindex_skips_unchanged_entries(client, monkeypatch, tmp_path):
    from chat import tasks

    yaml = tmp_path / "lib.yaml"
    yaml.write_text(
        """
urn: urn:test:lib
name: Test lib
objects:
  framework:
    urn: urn:test:fw
    ref_id: TST
    name: Test framework
    requirement_nodes:
      - urn: urn:test:req:1
        ref_id: R1
        name: Backups
        assessable: true
"""
    )
    monkeypatch.setattr(tasks, "LIBRARY_DIR", tmp_path)
    embedder = _Embedder()
    monkeypatch.setattr(providers, "get_embedder", lambda: embedder)

    tasks.index_library_knowledge_base.call_local()
    first = embedder.calls
    tasks.index_library_knowledge_base.call_local()

    assert first > 0
    assert embedder.calls == first
    assert client.count(rag.COLLECTION_NAME).count == first

    yaml.write_text("locale: fr\n" + yaml.read_text())
    tasks.index_library_knowledge_base.call_local()
    assert embedder.calls == 2 * first


def test_rank_merge_keeps_library_hits_without_reranker(client, monkeypatch):
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    monkeypatch.setattr(
        rag,
        "_user_partition_filter",
        lambda *_: Filter(
            must=[FieldCondition(key="source_type", match=MatchValue(value="model"))]
        ),
    )
    client.upsert(
        rag.COLLECTION_NAME,
        points=[
            PointStruct(id=i, vector=[1.0, 0.0], payload={"source_type": "model"})
            for i in range(1, 11)
        ]
        + [
            PointStruct(
                id=11,
                vector=[0.6, 0.8],
                payload={"source_type": "library", "framework": "DORA"},
            )
        ],
    )
    user = User.objects.create(email="rag-merge@test.local")

    results = rag.search("q", user, top_k=3)

    assert "library" in {r["source_type"] for r in results}


def test_named_frameworks_reads_graph_nodes(monkeypatch):
    from chat import knowledge_graph, tools, views

    graph = knowledge_graph.DiGraph()
    graph.add_node("urn:fw:dora", node_type="framework", name="DORA")
    monkeypatch.setattr(knowledge_graph, "get_graph", lambda: graph)
    monkeypatch.setattr(tools, "_detect_framework_names", lambda _: ["urn:fw:dora"])

    assert views._named_frameworks("DORA incident reporting") == ["DORA"]
