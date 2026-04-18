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
from dataclasses import dataclass
from typing import Iterable

import structlog
from django.db import transaction
from django.utils import timezone

from core.models import (
    RequirementMapping,
    RequirementMappingSet,
    RequirementNode,
)

logger = structlog.get_logger(__name__)


DEFAULT_TOP_K = 15
# Tuned for paraphrase-multilingual-MiniLM-L12-v2 — its cosines compress into
# the 0.3-0.75 range for semantically similar requirements. A model with wider
# spread (mpnet) would justify higher defaults; override via generation_params.
DEFAULT_HIGH_THRESHOLD = 0.60
DEFAULT_MEDIUM_THRESHOLD = 0.40
DEFAULT_LENGTH_SUBSET_RATIO = 1.5
DEFAULT_LENGTH_SUPERSET_RATIO = 0.67


@dataclass
class Signals:
    cosine: float
    lexical: float
    length_ratio: float
    rank: int
    bidirectional: bool

    def as_dict(self) -> dict:
        return {
            "cosine": round(self.cosine, 4),
            "lexical": round(self.lexical, 4),
            "length_ratio": round(self.length_ratio, 3),
            "rank": self.rank,
            "bidirectional": self.bidirectional,
        }


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


def _suggest_relationship(signals: Signals, high_thr: float, med_thr: float) -> str:
    """
    Orientation heuristic — suggests a relationship type from the raw signals.
    Humans are expected to confirm or override. Never returns not_related;
    rows below med_thr are not created at all.
    """
    r = signals.length_ratio
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
    if signals.cosine >= med_thr:
        return RequirementMapping.Relationship.INTERSECT
    return RequirementMapping.Relationship.NOT_RELATED


def _strength(signals: Signals) -> int:
    return max(0, min(10, round(signals.cosine * 10)))


def _query_directional_topk(
    client,
    embedder,
    nodes: list[RequirementNode],
    allowed_urns: set[str],
    target_framework_ref_id: str,
    top_k: int,
    collection: str,
) -> dict[str, list[tuple[str, float, int]]]:
    """
    For each source node, query Qdrant for the top-K hits among the allowed
    URNs. Returns src_urn -> [(tgt_urn, score, rank)].
    """
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

    out: dict[str, list[tuple[str, float, int]]] = {}
    # With a framework filter, top_k * 2 is plenty; urn de-dup removes at most 1.
    fetch_limit = max(top_k * 2, 20)

    for node in nodes:
        text = _build_node_text(node)
        if not text.strip():
            continue
        try:
            vector = embedder.embed_query(text)
            hits = client.query_points(
                collection_name=collection,
                query=vector,
                limit=fetch_limit,
                query_filter=base_filter,
            ).points
        except Exception as e:  # Qdrant down or embedding failure — skip node
            logger.warning("crosswalk_qdrant_query_failed", urn=node.urn, error=e)
            continue

        filtered: list[tuple[str, float, int]] = []
        rank = 0
        for h in hits:
            urn = (h.payload or {}).get("urn")
            if not urn or urn not in allowed_urns or urn == node.urn:
                continue
            filtered.append((urn, float(h.score), rank))
            rank += 1
            if rank >= top_k:
                break
        out[node.urn] = filtered

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

    client = get_qdrant_client()
    embedder = get_embedder()
    embedding_model = getattr(embedder, "model", None)
    embedding_model_name = getattr(
        embedding_model, "__class__", type(embedder)
    ).__name__

    fwd = _query_directional_topk(
        client,
        embedder,
        source_nodes,
        set(target_by_urn),
        mapping_set.target_framework.ref_id or "",
        top_k,
        COLLECTION_NAME,
    )
    rev = _query_directional_topk(
        client,
        embedder,
        target_nodes,
        set(source_by_urn),
        mapping_set.source_framework.ref_id or "",
        top_k,
        COLLECTION_NAME,
    )

    # Invert reverse map for quick symmetric lookup:
    # rev_lookup[(src_urn, tgt_urn)] = True iff src was in tgt's top-K
    rev_lookup: set[tuple[str, str]] = set()
    for tgt_urn, hits in rev.items():
        for src_urn, _score, _rank in hits:
            rev_lookup.add((src_urn, tgt_urn))

    # Build text once for length / lexical signals
    src_text = {n.urn: _build_node_text(n) for n in source_nodes}
    tgt_text = {n.urn: _build_node_text(n) for n in target_nodes}
    src_tokens = {urn: _tokens(t) for urn, t in src_text.items()}
    tgt_tokens = {urn: _tokens(t) for urn, t in tgt_text.items()}

    rows: list[RequirementMapping] = []
    for src_urn, hits in fwd.items():
        src_node = source_by_urn[src_urn]
        src_len = max(1, len(src_text[src_urn]))
        for tgt_urn, score, rank in hits:
            tgt_node = target_by_urn.get(tgt_urn)
            if tgt_node is None:
                continue
            tgt_len = max(1, len(tgt_text[tgt_urn]))
            signals = Signals(
                cosine=score,
                lexical=_jaccard(src_tokens[src_urn], tgt_tokens[tgt_urn]),
                length_ratio=tgt_len / src_len,
                rank=rank,
                bidirectional=(src_urn, tgt_urn) in rev_lookup,
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
        mapping_set.embedding_model = embedding_model_name
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
