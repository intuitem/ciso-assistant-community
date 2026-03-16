"""
RAG retrieval layer with permission-aware filtering.
Handles vector search, graph expansion via ORM, and context formatting.
"""

import structlog
import os
from typing import Any

from iam.models import Folder, RoleAssignment

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "ciso_assistant"
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")


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


def search(
    query: str,
    user,
    top_k: int = 10,
    source_type: str | None = None,
    object_type: str | None = None,
) -> list[dict]:
    """
    Permission-aware semantic search over the vector store.
    Filters results by the user's accessible folders.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue

    from .providers import get_embedder

    client = get_qdrant_client()
    embedder = get_embedder()

    query_vector = embedder.embed_query(query)

    # Build permission filter
    accessible_folders = get_accessible_folder_ids(user)
    must_conditions = [
        FieldCondition(
            key="folder_id",
            match=MatchAny(any=accessible_folders),
        )
    ]

    # Optional type filters
    if source_type:
        must_conditions.append(
            FieldCondition(key="source_type", match=MatchValue(value=source_type))
        )
    if object_type:
        must_conditions.append(
            FieldCondition(key="object_type", match=MatchValue(value=object_type))
        )

    query_filter = Filter(must=must_conditions)

    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )
    except Exception as e:
        logger.error("Qdrant search failed: %s", e)
        return []

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
        }
        for r in results.points
    ]


def graph_expand(results: list[dict], accessible_folder_ids: list[str]) -> list[dict]:
    """
    Expand retrieval results via ORM relations for richer context.
    Only returns objects in folders the user can access.
    """
    from core.models import AppliedControl, RiskScenario, RequirementAssessment

    expanded = []
    seen_ids = {r.get("object_id") for r in results if r.get("object_id")}
    accessible_set = set(accessible_folder_ids)

    for result in results:
        obj_type = result.get("object_type")
        obj_id = result.get("object_id")
        if not obj_id:
            continue

        try:
            if obj_type == "risk_scenario":
                scenario = RiskScenario.objects.select_related("folder").get(id=obj_id)
                # Related controls
                for control in scenario.applied_controls.select_related("folder").all():
                    if (
                        str(control.folder_id) in accessible_set
                        and str(control.id) not in seen_ids
                    ):
                        seen_ids.add(str(control.id))
                        expanded.append(_format_related(control, "applied_control"))
                # Related assets
                for asset in scenario.assets.select_related("folder").all():
                    if (
                        str(asset.folder_id) in accessible_set
                        and str(asset.id) not in seen_ids
                    ):
                        seen_ids.add(str(asset.id))
                        expanded.append(_format_related(asset, "asset"))

            elif obj_type == "applied_control":
                control = AppliedControl.objects.select_related("folder").get(id=obj_id)
                # Risk scenarios mitigated by this control
                for scenario in control.risk_scenarios.select_related("folder").all():
                    if (
                        str(scenario.folder_id) in accessible_set
                        and str(scenario.id) not in seen_ids
                    ):
                        seen_ids.add(str(scenario.id))
                        expanded.append(_format_related(scenario, "risk_scenario"))
                # Requirement assessments linked
                for ra in control.requirementassessment_set.select_related(
                    "compliance_assessment__folder"
                ).all():
                    folder_id = str(ra.compliance_assessment.folder_id)
                    if folder_id in accessible_set and str(ra.id) not in seen_ids:
                        seen_ids.add(str(ra.id))
                        expanded.append(_format_related(ra, "requirement_assessment"))

            elif obj_type == "requirement_assessment":
                ra = RequirementAssessment.objects.select_related(
                    "compliance_assessment__folder"
                ).get(id=obj_id)
                for control in ra.applied_controls.select_related("folder").all():
                    if (
                        str(control.folder_id) in accessible_set
                        and str(control.id) not in seen_ids
                    ):
                        seen_ids.add(str(control.id))
                        expanded.append(_format_related(control, "applied_control"))

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
