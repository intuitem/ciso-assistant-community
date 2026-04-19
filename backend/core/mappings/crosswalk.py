"""
Crosswalk suggestion engine.

Given a RequirementMappingSet with source + target frameworks, queries Qdrant
for semantic candidates and writes draft RequirementMapping rows with
heuristic-suggested relationships and explanatory signals.

Humans review and finalize the relationship type; the engine never classifies
on its own — it only proposes and orients.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable

import structlog
from django.db import transaction
from django.utils import timezone

from core.models import (
    RequirementMapping,
    RequirementMappingSet,
    RequirementNode,
)


DenseRetriever = Callable[[str, str], dict[str, tuple[int, float]]]
"""(source_urn, source_text) -> {target_urn: (rank, cosine_score)}"""

logger = structlog.get_logger(__name__)


DEFAULT_TOP_K = 5
# Tuned for paraphrase-multilingual-MiniLM-L12-v2 — its cosines compress into
# the 0.3-0.75 range for semantically similar requirements. A model with wider
# spread (mpnet) would justify higher defaults; override via generation_params.
DEFAULT_HIGH_THRESHOLD = 0.70
DEFAULT_MEDIUM_THRESHOLD = 0.50
DEFAULT_LENGTH_SUBSET_RATIO = 1.5
DEFAULT_LENGTH_SUPERSET_RATIO = 0.67
# BM25 hybrid retrieval. RRF fuses dense (Qdrant) + BM25 ranks so lexical
# signals rescue pairs dense misses (shared GRC jargon like MFA, RPO/RTO).
DEFAULT_USE_BM25 = True
DEFAULT_RRF_K = 60
DEFAULT_DENSE_FETCH_MULTIPLIER = 5  # over-fetch dense so BM25 hits have cosines


@dataclass
class Signals:
    cosine: float
    lexical: float
    length_ratio: float
    rank: int
    bidirectional: bool
    bm25_rank: int | None = None  # rank in BM25-only list (1-based); None if absent
    dense_rank: int | None = None  # rank in dense-only list; None if BM25 rescued it

    def as_dict(self) -> dict:
        out = {
            "cosine": round(self.cosine, 4),
            "lexical": round(self.lexical, 4),
            "length_ratio": round(self.length_ratio, 3),
            "rank": self.rank,
            "bidirectional": self.bidirectional,
        }
        if self.bm25_rank is not None:
            out["bm25_rank"] = self.bm25_rank
        if self.dense_rank is not None:
            out["dense_rank"] = self.dense_rank
        return out


_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _build_node_text(node: RequirementNode) -> str:
    parts: list[str] = []
    if node.ref_id:
        parts.append(node.ref_id)
    if node.name:
        parts.append(node.name)
    if node.description:
        parts.append(node.description)
    return "\n".join(parts)


BM25_RESCUE_RANK = 2  # top-3 BM25 hits escape the dense-cosine floor


def _suggest_relationship(signals: Signals, high_thr: float, med_thr: float) -> str:
    """
    Orientation heuristic — suggests a relationship type from the raw signals.
    Humans are expected to confirm or override. Never returns not_related;
    rows below med_thr are not created at all.

    BM25-rescue: a pair can clear the medium floor via high BM25 rank even
    if its dense cosine is low — that's where hybrid retrieval adds recall
    on jargon-heavy pairs.
    """
    r = signals.length_ratio
    bm25_rescued = (
        signals.bm25_rank is not None and signals.bm25_rank <= BM25_RESCUE_RANK
    )

    if signals.cosine >= high_thr and signals.bidirectional:
        if 0.75 <= r <= 1.35:
            return RequirementMapping.Relationship.EQUAL
        if r > DEFAULT_LENGTH_SUBSET_RATIO:
            return RequirementMapping.Relationship.SUBSET
        if r < DEFAULT_LENGTH_SUPERSET_RATIO:
            return RequirementMapping.Relationship.SUPERSET
        return RequirementMapping.Relationship.EQUAL
    if signals.cosine >= high_thr:
        if r > DEFAULT_LENGTH_SUBSET_RATIO:
            return RequirementMapping.Relationship.SUBSET
        if r < DEFAULT_LENGTH_SUPERSET_RATIO:
            return RequirementMapping.Relationship.SUPERSET
        return RequirementMapping.Relationship.INTERSECT
    if signals.cosine >= med_thr or bm25_rescued:
        return RequirementMapping.Relationship.INTERSECT
    return RequirementMapping.Relationship.NOT_RELATED


def _strength(signals: Signals) -> int:
    return max(0, min(10, round(signals.cosine * 10)))


@dataclass
class Hit:
    """One target candidate for a source node, with all signals needed downstream."""

    urn: str
    cosine: float  # from Qdrant; 0.0 if BM25 surfaced it and dense missed
    fused_rank: int  # 0-based final rank after RRF
    dense_rank: int | None  # rank in dense-only list (0-based), None if outside
    bm25_rank: int | None  # rank in BM25-only list (0-based), None if outside


def _probe_qdrant(client) -> bool:
    """Return True if the shared collection is reachable and non-empty.

    Called once per generation run. Connection failures, timeouts, or an
    empty collection all mean we should fall back to the in-process path.
    """
    from chat.rag import COLLECTION_NAME

    try:
        info = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        logger.info("crosswalk_qdrant_unavailable", error=str(e))
        return False
    points = getattr(info, "points_count", 0) or 0
    if points <= 0:
        logger.info("crosswalk_qdrant_empty")
        return False
    return True


def _make_qdrant_retriever(
    client,
    embedder,
    collection: str,
    target_framework_ref_id: str,
    allowed_urns: set[str],
    limit: int,
) -> DenseRetriever:
    """Dense retriever backed by the shared Qdrant index."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    must = [
        FieldCondition(key="source_type", match=MatchValue(value="library")),
        FieldCondition(key="object_type", match=MatchValue(value="requirement_node")),
    ]
    if target_framework_ref_id:
        must.append(
            FieldCondition(
                key="framework_ref_id",
                match=MatchValue(value=target_framework_ref_id),
            )
        )
    base_filter = Filter(must=must)

    def retrieve(source_urn: str, source_text: str) -> dict[str, tuple[int, float]]:
        try:
            vector = embedder.embed_query(source_text)
            hits = client.query_points(
                collection_name=collection,
                query=vector,
                limit=limit,
                query_filter=base_filter,
            ).points
        except Exception as e:
            logger.warning(
                "crosswalk_qdrant_query_failed", urn=source_urn, error=str(e)
            )
            return {}
        out: dict[str, tuple[int, float]] = {}
        rank = 0
        for h in hits:
            urn = (h.payload or {}).get("urn")
            if not urn or urn not in allowed_urns or urn == source_urn:
                continue
            out[urn] = (rank, float(h.score))
            rank += 1
        return out

    return retrieve


def _make_inprocess_retriever(
    embedder,
    target_nodes: list[RequirementNode],
    allowed_urns: set[str],
    limit: int,
) -> DenseRetriever:
    """Dense retriever that embeds the target corpus locally and brute-forces cosine.

    Cheap for framework-sized corpora (100–2000 nodes) and has no external
    dependency. Used when Qdrant is unavailable.
    """
    import numpy as np

    texts = [_build_node_text(n) for n in target_nodes]
    urns = [n.urn for n in target_nodes]
    vectors = embedder.embed(texts) if texts else []
    matrix = (
        np.asarray(vectors, dtype=np.float32)
        if vectors
        else np.zeros((0, 0), dtype=np.float32)
    )
    if matrix.size:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = matrix / np.clip(norms, 1e-9, None)

    def retrieve(source_urn: str, source_text: str) -> dict[str, tuple[int, float]]:
        if not matrix.size:
            return {}
        q = np.asarray(embedder.embed_query(source_text), dtype=np.float32)
        q_norm = float(np.linalg.norm(q))
        if q_norm == 0.0:
            return {}
        q = q / q_norm
        scores = matrix @ q  # cosine since both sides are unit-normalized
        # argsort descending; -scores is cheaper than sorted(..., reverse=True)
        order = np.argsort(-scores)
        out: dict[str, tuple[int, float]] = {}
        rank = 0
        for i in order:
            urn = urns[int(i)]
            if urn == source_urn or urn not in allowed_urns:
                continue
            out[urn] = (rank, float(scores[int(i)]))
            rank += 1
            if rank >= limit:
                break
        return out

    return retrieve


def _build_bm25_corpus(nodes: list[RequirementNode]):
    """Build a BM25 index over the node texts. Returns (index, urn_order)."""
    from rank_bm25 import BM25Okapi

    tokenized = [list(_tokens(_build_node_text(n))) for n in nodes]
    urns = [n.urn for n in nodes]
    # rank_bm25 rejects empty corpora — guard.
    if not any(tokenized):
        return None, urns
    # Replace empty token lists with a placeholder so BM25 stays well-defined;
    # their scores will be ~0 regardless.
    tokenized = [t or ["_"] for t in tokenized]
    return BM25Okapi(tokenized), urns


def _query_directional_topk(
    dense_retriever: DenseRetriever,
    source_nodes: list[RequirementNode],
    target_nodes: list[RequirementNode],
    allowed_urns: set[str],
    top_k: int,
    use_bm25: bool,
) -> dict[str, list[Hit]]:
    """For each source node, fuse dense + BM25 retrieval via RRF and return top-K."""
    # Build a BM25 index over the target corpus once — reused across all sources.
    bm25_index = None
    bm25_urns: list[str] = []
    if use_bm25:
        bm25_index, bm25_urns = _build_bm25_corpus(target_nodes)

    out: dict[str, list[Hit]] = {}

    for node in source_nodes:
        text = _build_node_text(node)
        if not text.strip():
            continue

        # --- Dense retrieval (Qdrant or in-process, same shape) ---
        dense_by_urn = dense_retriever(node.urn, text)

        # --- BM25 retrieval (optional) ---
        bm25_by_urn: dict[str, int] = {}
        if bm25_index is not None:
            query_tokens = list(_tokens(text))
            if query_tokens:
                scores = bm25_index.get_scores(query_tokens)
                # Top BM25 candidates, excluding self
                ranked = sorted(
                    range(len(bm25_urns)), key=lambda i: scores[i], reverse=True
                )
                r = 0
                for idx in ranked[: top_k * 2]:
                    if scores[idx] <= 0:
                        break
                    urn = bm25_urns[idx]
                    if urn == node.urn or urn not in allowed_urns:
                        continue
                    bm25_by_urn[urn] = r
                    r += 1

        # --- Reciprocal Rank Fusion ---
        candidate_urns = set(dense_by_urn) | set(bm25_by_urn)
        if not candidate_urns:
            out[node.urn] = []
            continue
        fused_scores: dict[str, float] = {}
        for urn in candidate_urns:
            score = 0.0
            if urn in dense_by_urn:
                score += 1.0 / (DEFAULT_RRF_K + dense_by_urn[urn][0] + 1)
            if urn in bm25_by_urn:
                score += 1.0 / (DEFAULT_RRF_K + bm25_by_urn[urn] + 1)
            fused_scores[urn] = score

        ordered = sorted(fused_scores.items(), key=lambda kv: kv[1], reverse=True)[
            :top_k
        ]
        hits_out: list[Hit] = []
        for fused_rank, (urn, _score) in enumerate(ordered):
            dense = dense_by_urn.get(urn)
            bm25_r = bm25_by_urn.get(urn)
            hits_out.append(
                Hit(
                    urn=urn,
                    cosine=dense[1] if dense else 0.0,
                    fused_rank=fused_rank,
                    dense_rank=dense[0] if dense else None,
                    bm25_rank=bm25_r,
                )
            )
        out[node.urn] = hits_out

    return out


def generate_suggestions(mapping_set: RequirementMappingSet) -> dict:
    """
    Populate draft RequirementMapping rows for the given mapping set.
    Returns a summary dict. Raises on unrecoverable failures (caller marks
    the set as failed).
    """
    from chat.providers import get_embedder
    from chat.rag import COLLECTION_NAME, get_qdrant_client

    params = mapping_set.generation_params or {}
    top_k = int(params.get("top_k", DEFAULT_TOP_K))
    high_thr = float(params.get("high_threshold", DEFAULT_HIGH_THRESHOLD))
    med_thr = float(params.get("medium_threshold", DEFAULT_MEDIUM_THRESHOLD))
    use_bm25 = bool(params.get("use_bm25", DEFAULT_USE_BM25))

    t0 = time.time()

    source_nodes = list(
        RequirementNode.objects.filter(
            framework=mapping_set.source_framework, assessable=True
        )
        .exclude(urn__isnull=True)
        .exclude(urn__exact="")
    )
    target_nodes = list(
        RequirementNode.objects.filter(
            framework=mapping_set.target_framework, assessable=True
        )
        .exclude(urn__isnull=True)
        .exclude(urn__exact="")
    )

    source_by_urn = {n.urn: n for n in source_nodes}
    target_by_urn = {n.urn: n for n in target_nodes}

    if not source_nodes or not target_nodes:
        logger.warning(
            "crosswalk_missing_nodes",
            mapping_set=str(mapping_set.id),
            source_count=len(source_nodes),
            target_count=len(target_nodes),
        )
        return {"pairs": 0, "reason": "empty_framework"}

    embedder = get_embedder()
    embedding_model_name = getattr(
        getattr(embedder, "model", None), "__class__", type(embedder)
    ).__name__

    # Probe Qdrant once; fall back to in-process embedding if unreachable/empty.
    # With a fallback available, deployments without Qdrant still get the feature —
    # at the cost of embedding both frameworks on every run.
    client = get_qdrant_client()
    qdrant_ready = _probe_qdrant(client)
    retrieval_backend = "qdrant" if qdrant_ready else "in-process"
    dense_limit = max(top_k * DEFAULT_DENSE_FETCH_MULTIPLIER, 30)
    logger.info(
        "crosswalk_retrieval_backend",
        backend=retrieval_backend,
        mapping_set=str(mapping_set.id),
    )

    if qdrant_ready:
        fwd_retriever = _make_qdrant_retriever(
            client,
            embedder,
            COLLECTION_NAME,
            mapping_set.target_framework.ref_id or "",
            set(target_by_urn),
            dense_limit,
        )
        rev_retriever = _make_qdrant_retriever(
            client,
            embedder,
            COLLECTION_NAME,
            mapping_set.source_framework.ref_id or "",
            set(source_by_urn),
            dense_limit,
        )
    else:
        fwd_retriever = _make_inprocess_retriever(
            embedder, target_nodes, set(target_by_urn), dense_limit
        )
        rev_retriever = _make_inprocess_retriever(
            embedder, source_nodes, set(source_by_urn), dense_limit
        )

    fwd = _query_directional_topk(
        fwd_retriever, source_nodes, target_nodes, set(target_by_urn), top_k, use_bm25
    )
    rev = _query_directional_topk(
        rev_retriever, target_nodes, source_nodes, set(source_by_urn), top_k, use_bm25
    )

    # Invert reverse map for quick symmetric lookup:
    # rev_lookup[(src_urn, tgt_urn)] = True iff src was in tgt's top-K
    rev_lookup: set[tuple[str, str]] = set()
    for tgt_urn, hits in rev.items():
        for h in hits:
            rev_lookup.add((h.urn, tgt_urn))

    # Build text once for length / lexical signals
    src_text = {n.urn: _build_node_text(n) for n in source_nodes}
    tgt_text = {n.urn: _build_node_text(n) for n in target_nodes}
    src_tokens = {urn: _tokens(t) for urn, t in src_text.items()}
    tgt_tokens = {urn: _tokens(t) for urn, t in tgt_text.items()}

    rows: list[RequirementMapping] = []
    for src_urn, hits in fwd.items():
        src_node = source_by_urn[src_urn]
        src_len = max(1, len(src_text[src_urn]))
        for h in hits:
            tgt_node = target_by_urn.get(h.urn)
            if tgt_node is None:
                continue
            tgt_len = max(1, len(tgt_text[h.urn]))
            signals = Signals(
                cosine=h.cosine,
                lexical=_jaccard(src_tokens[src_urn], tgt_tokens[h.urn]),
                length_ratio=tgt_len / src_len,
                rank=h.fused_rank,
                bidirectional=(src_urn, h.urn) in rev_lookup,
                bm25_rank=h.bm25_rank,
                dense_rank=h.dense_rank,
            )
            suggested = _suggest_relationship(signals, high_thr, med_thr)
            if suggested == RequirementMapping.Relationship.NOT_RELATED:
                continue
            rows.append(
                RequirementMapping(
                    mapping_set=mapping_set,
                    source_requirement=src_node,
                    target_requirement=tgt_node,
                    relationship=suggested,
                    strength_of_relationship=_strength(signals),
                    is_suggested=True,
                    reviewed=False,
                    suggestion_metadata=signals.as_dict(),
                )
            )

    with transaction.atomic():
        RequirementMapping.objects.filter(
            mapping_set=mapping_set, is_suggested=True, reviewed=False
        ).delete()
        RequirementMapping.objects.bulk_create(rows, batch_size=500)
        mapping_set.status = RequirementMappingSet.Status.READY
        mapping_set.generated_at = timezone.now()
        mapping_set.embedding_model = f"{embedding_model_name} ({retrieval_backend})"
        mapping_set.generation_error = ""
        # Do not overwrite generation_params — it represents user-supplied
        # overrides, not the effective run config.
        mapping_set.save(
            update_fields=[
                "status",
                "generated_at",
                "embedding_model",
                "generation_error",
                "updated_at",
            ]
        )

    duration = round(time.time() - t0, 2)
    logger.info(
        "crosswalk_generated",
        mapping_set=str(mapping_set.id),
        pairs=len(rows),
        source_count=len(source_nodes),
        target_count=len(target_nodes),
        duration=duration,
    )
    return {
        "pairs": len(rows),
        "source_count": len(source_nodes),
        "target_count": len(target_nodes),
        "duration": duration,
    }
