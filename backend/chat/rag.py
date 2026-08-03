"""
RAG retrieval layer with permission-aware filtering.
Handles vector search, cross-encoder re-ranking, graph expansion via ORM,
and context formatting.
"""

import structlog
import os
import time
from typing import Any

from iam.models import Folder, RoleAssignment
from chat.embedding_models import RERANKER_MODEL as _RERANKER_MODEL

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "ciso_assistant"
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")

# Cross-encoder re-ranker (cached singleton)
_reranker = None


def _get_reranker():
    """Get the cross-encoder re-ranker, loading on first use."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder

            _reranker = CrossEncoder(_RERANKER_MODEL)
            logger.info("reranker_loaded", model=_RERANKER_MODEL)
        except Exception as e:
            logger.warning("reranker_load_failed", error=e)
    return _reranker


def get_qdrant_client():
    """Get a Qdrant client instance."""
    from qdrant_client import QdrantClient

    return QdrantClient(url=QDRANT_URL)


def get_accessible_folder_ids(user) -> list[str]:
    """Get all folder IDs the user has access to, as strings for Qdrant filtering."""
    root = Folder.get_root_folder()
    folder_ids = RoleAssignment.get_accessible_folder_ids(
        folder=root,
        user=user,
        content_type=Folder.ContentType.DOMAIN,
    )
    return [str(fid) for fid in folder_ids]


def indexed_payload_types() -> dict[str, Any]:
    """Qdrant ``object_type`` payload value → the model class it came from."""
    from django.apps import apps

    from .signals import INDEXED_MODELS
    from .text import _normalize_model_name

    types = {}
    for path in INDEXED_MODELS:
        app_label, model_name = path.split(".")
        try:
            types[_normalize_model_name(model_name)] = apps.get_model(
                app_label, model_name
            )
        except LookupError:
            continue
    # Uploaded files are indexed as document_chunk, gated by IndexedDocument
    try:
        types["document_chunk"] = apps.get_model("chat", "IndexedDocument")
    except LookupError:
        # Uploaded-file chunks simply stay unsearchable rather than unscoped
        logger.debug("indexed_payload_types: IndexedDocument unavailable")
    return types


def _user_partition_filter(scope, source_type, object_type):
    """
    One clause per indexed type: that type AND the folders where the user holds
    view_<model>. A single folder_id filter would leak types the user's role
    cannot read (a respondent sees a domain but not its risk scenarios).
    """
    from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue

    clauses = []
    for payload_type, model_class in indexed_payload_types().items():
        if object_type and payload_type != object_type:
            continue
        folders = scope.folder_ids_for(model_class)
        if not folders:
            continue
        clauses.append(
            Filter(
                must=[
                    FieldCondition(
                        key="object_type", match=MatchValue(value=payload_type)
                    ),
                    FieldCondition(key="folder_id", match=MatchAny(any=folders)),
                ]
            )
        )

    if not clauses:
        return None

    conditions = [Filter(should=clauses)]
    if source_type:
        conditions.append(
            FieldCondition(key="source_type", match=MatchValue(value=source_type))
        )
    return Filter(must=conditions)


def search(
    query: str,
    user,
    top_k: int = 10,
    source_type: str | None = None,
    object_type: str | None = None,
    scope=None,
) -> list[dict]:
    """
    Permission-aware semantic search over the vector store.

    Searches two partitions and merges results:
    - User data (models, documents): filtered per object type by view_<model>
    - Library knowledge (frameworks, threats): shared, no folder filter

    Results are merged and sorted by score.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    from .providers import get_embedder
    from .scoping import ReadScope

    if scope is None:
        scope = ReadScope(user)

    client = get_qdrant_client()
    embedder = get_embedder()

    query_vector = embedder.embed_query(query)
    all_results = []

    # Over-fetch to have enough candidates for re-ranking
    fetch_limit = top_k * 3

    # --- Search 1: User data (permission-filtered) ---
    if source_type != "library":
        user_filter = _user_partition_filter(scope, source_type, object_type)
        if user_filter is not None:
            try:
                user_results = client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=query_vector,
                    limit=fetch_limit,
                    query_filter=user_filter,
                )
                all_results.extend(user_results.points)
            except Exception as e:
                logger.error("qdrant_user_search_failed", error=e)

    # --- Search 2: Library knowledge (shared, no folder filter) ---
    if source_type in (None, "library"):
        library_conditions = [
            FieldCondition(key="source_type", match=MatchValue(value="library"))
        ]
        if object_type:
            library_conditions.append(
                FieldCondition(key="object_type", match=MatchValue(value=object_type))
            )

        try:
            library_results = client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=fetch_limit,
                query_filter=Filter(must=library_conditions),
            )
            all_results.extend(library_results.points)
        except Exception as e:
            logger.error("qdrant_library_search_failed", error=e)

    # Merge and deduplicate
    seen_ids = set()
    merged = []
    for r in sorted(all_results, key=lambda x: x.score, reverse=True):
        rid = str(r.id)
        if rid not in seen_ids:
            seen_ids.add(rid)
            merged.append(r)

    # Re-rank with cross-encoder for better relevance
    reranker = _get_reranker()
    if reranker and len(merged) > top_k:
        t0 = time.time()
        pairs = [(query, r.payload.get("text", "")[:512]) for r in merged]
        try:
            scores = reranker.predict(pairs)
            ranked = sorted(zip(scores, merged), key=lambda x: x[0], reverse=True)
            merged = [r for _, r in ranked[:top_k]]
            logger.info(
                "reranker_complete",
                candidates=len(pairs),
                kept=len(merged),
                duration=round(time.time() - t0, 2),
            )
        except Exception as e:
            logger.warning("reranker_failed", error=e)
            merged = merged[:top_k]
    else:
        merged = merged[:top_k]

    return [
        {
            "id": str(r.id),
            "score": r.score,
            "text": r.payload.get("text", ""),
            "source_type": r.payload.get("source_type", ""),
            "object_type": r.payload.get("object_type", ""),
            "object_id": r.payload.get("object_id"),
            "name": r.payload.get("name", ""),
            "ref_id": r.payload.get("ref_id", ""),
            "framework": r.payload.get("framework", ""),
            "urn": r.payload.get("urn", ""),
        }
        for r in merged
    ]


def graph_expand(results: list[dict], scope) -> list[dict]:
    """
    Expand retrieval results via ORM relations for richer context.
    Every hop is re-checked against the user's read scope — the seed being
    readable says nothing about what hangs off it.
    """
    from core.models import Asset, AppliedControl, RiskScenario, RequirementAssessment

    # relation to walk per seed type: (attribute, related model, payload type)
    hops = {
        "risk_scenario": (
            ("applied_controls", AppliedControl, "applied_control"),
            ("assets", Asset, "asset"),
        ),
        "applied_control": (
            ("risk_scenarios", RiskScenario, "risk_scenario"),
            (
                "requirementassessment_set",
                RequirementAssessment,
                "requirement_assessment",
            ),
        ),
        "requirement_assessment": (
            ("applied_controls", AppliedControl, "applied_control"),
        ),
    }
    seeds = {
        "risk_scenario": RiskScenario,
        "applied_control": AppliedControl,
        "requirement_assessment": RequirementAssessment,
    }

    expanded = []
    seen_ids = {r.get("object_id") for r in results if r.get("object_id")}

    for result in results:
        obj_type = result.get("object_type")
        obj_id = result.get("object_id")
        if not obj_id or obj_type not in seeds:
            continue

        try:
            seed = scope.queryset(seeds[obj_type]).filter(id=obj_id).first()
            if seed is None:
                continue
            for attribute, related_model, payload_type in hops[obj_type]:
                for obj in getattr(seed, attribute).all():
                    if str(obj.id) in seen_ids or not scope.can_read(
                        related_model, obj.id
                    ):
                        continue
                    seen_ids.add(str(obj.id))
                    expanded.append(_format_related(obj, payload_type))
        except Exception as e:
            logger.debug("Graph expansion failed for %s/%s: %s", obj_type, obj_id, e)

    return expanded


def _format_related(obj, obj_type: str) -> dict:
    """Format a Django model instance as a context dict."""
    name = str(obj)
    description = getattr(obj, "description", "") or ""
    ref_id = getattr(obj, "ref_id", "") or ""
    return {
        "object_type": obj_type,
        "object_id": str(obj.id),
        "name": name,
        "text": f"{obj_type.replace('_', ' ').title()}: {name}\n{description}".strip(),
        "ref_id": ref_id,
        "source_type": "graph_expansion",
        "score": 0.0,
    }


def format_context(results: list[dict], expanded: list[dict] | None = None) -> str:
    """Format search results and expanded context into a string for the LLM."""
    parts = []

    for i, r in enumerate(results, 1):
        source_label = r.get("framework") or r.get("object_type", "unknown")
        ref = r.get("ref_id", "")
        header = f"[Source {i}: {source_label}"
        if ref:
            header += f" - {ref}"
        if r.get("urn"):
            header += f" ({r['urn']})"
        header += f" (score: {r['score']:.2f})]"
        parts.append(f"{header}\n{r['text']}")

    if expanded:
        parts.append("\n--- Related objects ---")
        for r in expanded:
            parts.append(f"[Related: {r['object_type']} - {r['name']}]\n{r['text']}")

    return "\n\n".join(parts)


def build_context_refs(
    results: list[dict], expanded: list[dict] | None = None
) -> list[dict]:
    """Build context_refs list for storing in ChatMessage."""
    refs = []
    for r in results:
        ref = {
            "type": r.get("object_type", r.get("source_type", "")),
            "name": r.get("name", ""),
        }
        if r.get("object_id"):
            ref["id"] = r["object_id"]
        if r.get("ref_id"):
            ref["ref_id"] = r["ref_id"]
        if r.get("score"):
            ref["score"] = round(r["score"], 3)
        # Library citations
        if r.get("source_type") == "library":
            ref["source"] = "library"
            if r.get("framework"):
                ref["framework"] = r["framework"]
            if r.get("urn"):
                ref["urn"] = r["urn"]
        refs.append(ref)

    if expanded:
        for r in expanded:
            refs.append(
                {
                    "type": r["object_type"],
                    "id": r.get("object_id", ""),
                    "name": r["name"],
                    "source": "graph_expansion",
                }
            )

    return refs
