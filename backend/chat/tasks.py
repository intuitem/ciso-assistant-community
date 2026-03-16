"""
Huey background tasks for document ingestion and object indexing.
"""

import structlog
import uuid

from django.utils import timezone
from huey.contrib.djhuey import db_task

logger = structlog.get_logger(__name__)


@db_task()
def ingest_document(document_id: str):
    """
    Async task: extract text from a document, chunk it, embed it, store in Qdrant.
    """
    from .models import IndexedDocument
    from .extractors import get_extractor
    from .providers import get_embedder
    from .rag import COLLECTION_NAME, get_qdrant_client

    try:
        doc = IndexedDocument.objects.get(id=document_id)
    except IndexedDocument.DoesNotExist:
        logger.error("IndexedDocument %s not found", document_id)
        return

    doc.status = IndexedDocument.Status.PROCESSING
    doc.save(update_fields=["status"])

    try:
        # Get extractor for file type
        extractor = get_extractor(doc.content_type)
        if not extractor:
            raise ValueError(f"No extractor for content type: {doc.content_type}")

        # Extract chunks
        chunks = extractor(doc.file)
        if not chunks:
            raise ValueError("No content extracted from document")

        # Embed chunks
        embedder = get_embedder()
        texts = [chunk.text for chunk in chunks]
        embeddings = embedder.embed(texts)

        # Store in Qdrant
        from qdrant_client.models import PointStruct

        client = get_qdrant_client()
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc.id}:{chunk.index}")),
                vector=embedding,
                payload={
                    "text": chunk.text,
                    "folder_id": str(doc.folder_id),
                    "source_type": "document",
                    "object_type": "document_chunk",
                    "object_id": str(doc.id),
                    "document_id": str(doc.id),
                    "chunk_index": chunk.index,
                    "filename": doc.filename,
                    **chunk.metadata,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]

        client.upsert(collection_name=COLLECTION_NAME, points=points)

        doc.status = IndexedDocument.Status.INDEXED
        doc.chunk_count = len(chunks)
        doc.indexed_at = timezone.now()
        doc.save(update_fields=["status", "chunk_count", "indexed_at"])

        logger.info("Indexed document %s: %d chunks", doc.filename, len(chunks))

    except Exception as e:
        logger.error("Failed to ingest document %s: %s", document_id, e)
        doc.status = IndexedDocument.Status.FAILED
        doc.error_message = str(e)
        doc.save(update_fields=["status", "error_message"])


@db_task()
def index_model_object(app_label: str, model_name: str, object_id: str):
    """
    Async task: index or re-index a single Django model object into Qdrant.
    """
    from django.apps import apps

    from .providers import get_embedder
    from .rag import COLLECTION_NAME, get_qdrant_client

    try:
        model_class = apps.get_model(app_label, model_name)
        obj = model_class.objects.get(id=object_id)
    except Exception as e:
        logger.error("Cannot load %s.%s/%s: %s", app_label, model_name, object_id, e)
        return

    # Build text representation
    text = _build_object_text(obj, model_name)
    if not text:
        return

    folder_id = str(getattr(obj, "folder_id", ""))
    if not folder_id:
        return

    try:
        embedder = get_embedder()
        vector = embedder.embed_query(text)

        from qdrant_client.models import PointStruct

        client = get_qdrant_client()
        point = PointStruct(
            id=str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"{app_label}.{model_name}:{object_id}")
            ),
            vector=vector,
            payload={
                "text": text,
                "folder_id": folder_id,
                "source_type": "model",
                "object_type": _normalize_model_name(model_name),
                "object_id": object_id,
                "name": str(obj),
                "ref_id": getattr(obj, "ref_id", "") or "",
            },
        )

        client.upsert(collection_name=COLLECTION_NAME, points=[point])
        logger.debug("Indexed %s.%s/%s", app_label, model_name, object_id)

    except Exception as e:
        logger.error(
            "Failed to index %s.%s/%s: %s", app_label, model_name, object_id, e
        )


@db_task()
def remove_model_object(app_label: str, model_name: str, object_id: str):
    """Remove a deleted object from the vector store."""
    from .rag import COLLECTION_NAME, get_qdrant_client
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    try:
        client = get_qdrant_client()
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(key="object_id", match=MatchValue(value=object_id)),
                    FieldCondition(key="source_type", match=MatchValue(value="model")),
                ]
            ),
        )
        logger.debug("Removed %s.%s/%s from index", app_label, model_name, object_id)
    except Exception as e:
        logger.error(
            "Failed to remove %s.%s/%s: %s", app_label, model_name, object_id, e
        )


def _build_object_text(obj, model_name: str) -> str:
    """Build a searchable text representation of a model object."""
    parts = [f"Type: {model_name.replace('_', ' ').title()}"]

    name = getattr(obj, "name", None)
    if name:
        parts.append(f"Name: {name}")

    ref_id = getattr(obj, "ref_id", None)
    if ref_id:
        parts.append(f"Reference: {ref_id}")

    description = getattr(obj, "description", None)
    if description:
        parts.append(f"Description: {description}")

    # Model-specific fields
    if hasattr(obj, "current_level"):
        parts.append(
            f"Current risk level: {obj.get_current_level_display() if hasattr(obj, 'get_current_level_display') else obj.current_level}"
        )

    if hasattr(obj, "treatment"):
        parts.append(
            f"Treatment: {obj.get_treatment_display() if hasattr(obj, 'get_treatment_display') else obj.treatment}"
        )

    if hasattr(obj, "status"):
        status_display = (
            obj.get_status_display()
            if hasattr(obj, "get_status_display")
            else obj.status
        )
        parts.append(f"Status: {status_display}")

    if hasattr(obj, "category"):
        cat_display = (
            obj.get_category_display()
            if hasattr(obj, "get_category_display")
            else obj.category
        )
        if cat_display:
            parts.append(f"Category: {cat_display}")

    if hasattr(obj, "business_value"):
        bv = (
            obj.get_business_value_display()
            if hasattr(obj, "get_business_value_display")
            else obj.business_value
        )
        if bv:
            parts.append(f"Business value: {bv}")

    return "\n".join(parts)


def _normalize_model_name(model_name: str) -> str:
    """Convert model class name to snake_case identifier."""
    import re

    s = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", model_name)
    return s.lower()


# ---------------------------------------------------------------------------
# Library knowledge base indexing
# ---------------------------------------------------------------------------

LIBRARY_DIR = None  # Resolved lazily


def _get_library_dir():
    """Get the path to the YAML library directory."""
    global LIBRARY_DIR
    if LIBRARY_DIR is None:
        from pathlib import Path

        LIBRARY_DIR = Path(__file__).resolve().parent.parent / "library" / "libraries"
    return LIBRARY_DIR


def _parse_library_yaml(filepath) -> list[dict]:
    """
    Parse a YAML library file and extract indexable entries.
    Returns a list of dicts with: urn, ref_id, name, description, etc.
    """
    import yaml

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.warning("failed_to_parse_yaml", file=str(filepath), error=str(e))
        return []

    if not isinstance(data, dict):
        return []

    library_name = data.get("name", "")
    library_ref_id = data.get("ref_id", "")
    locale = data.get("locale", "en")
    provider = data.get("provider", "")

    entries = []
    objects = data.get("objects", {})

    # Extract framework requirement nodes
    framework = objects.get("framework", {})
    if isinstance(framework, dict):
        framework_name = framework.get("name", library_name)
        framework_ref_id = framework.get("ref_id", library_ref_id)
        for node in framework.get("requirement_nodes", []):
            # Skip empty section headers
            if not node.get("name") and not node.get("description"):
                continue
            entries.append(
                {
                    "urn": node.get("urn", ""),
                    "ref_id": node.get("ref_id", ""),
                    "name": node.get("name", ""),
                    "description": node.get("description", ""),
                    "annotation": node.get("annotation", ""),
                    "framework": framework_name,
                    "framework_ref_id": framework_ref_id,
                    "provider": provider,
                    "locale": locale,
                    "object_type": "requirement_node",
                }
            )

    # Extract threats
    for threat in objects.get("threats", []):
        entries.append(
            {
                "urn": threat.get("urn", ""),
                "ref_id": threat.get("ref_id", ""),
                "name": threat.get("name", ""),
                "description": threat.get("description", ""),
                "annotation": "",
                "framework": library_name,
                "framework_ref_id": library_ref_id,
                "provider": provider,
                "locale": locale,
                "object_type": "library_threat",
            }
        )

    # Extract reference controls
    for ctrl in objects.get("reference_controls", []):
        entries.append(
            {
                "urn": ctrl.get("urn", ""),
                "ref_id": ctrl.get("ref_id", ""),
                "name": ctrl.get("name", ""),
                "description": ctrl.get("description", ""),
                "annotation": ctrl.get("annotation", ""),
                "framework": library_name,
                "framework_ref_id": library_ref_id,
                "provider": provider,
                "locale": locale,
                "object_type": "reference_control",
            }
        )

    return entries


def _build_library_entry_text(entry: dict) -> str:
    """Build searchable text for a library entry."""
    parts = [f"Framework: {entry['framework']}"]
    if entry.get("ref_id"):
        parts.append(f"Reference: {entry['ref_id']}")
    if entry.get("name"):
        parts.append(f"Name: {entry['name']}")
    if entry.get("description"):
        parts.append(f"Description: {entry['description']}")
    if entry.get("annotation"):
        parts.append(f"Guidance: {entry['annotation']}")
    return "\n".join(parts)


@db_task()
def index_library_knowledge_base():
    """
    Async task: parse all YAML library files and index requirement nodes,
    threats, and reference controls into Qdrant as shared knowledge.

    Uses source_type="library" — accessible to all authenticated users
    without folder-based permission filtering.
    """
    import time

    from .providers import get_embedder
    from .rag import COLLECTION_NAME, get_qdrant_client

    t0 = time.time()
    library_dir = _get_library_dir()
    if not library_dir.exists():
        logger.warning("library_dir_not_found", path=str(library_dir))
        return

    yaml_files = sorted(library_dir.glob("*.yaml"))
    logger.info("library_indexing_started", file_count=len(yaml_files))

    # Collect all entries from all YAML files
    all_entries = []
    for filepath in yaml_files:
        entries = _parse_library_yaml(filepath)
        all_entries.extend(entries)

    if not all_entries:
        logger.info("library_indexing_no_entries")
        return

    logger.info(
        "library_entries_parsed",
        count=len(all_entries),
        duration=round(time.time() - t0, 2),
    )

    # Embed in batches
    embedder = get_embedder()
    client = get_qdrant_client()

    from qdrant_client.models import PointStruct

    BATCH_SIZE = 100
    total_indexed = 0

    for batch_start in range(0, len(all_entries), BATCH_SIZE):
        batch = all_entries[batch_start : batch_start + BATCH_SIZE]
        texts = [_build_library_entry_text(e) for e in batch]

        try:
            embeddings = embedder.embed(texts)
        except Exception as e:
            logger.error(
                "library_embedding_failed",
                batch_start=batch_start,
                error=str(e),
            )
            continue

        points = []
        for entry, embedding in zip(batch, embeddings):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"library:{entry['urn']}"))
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": _build_library_entry_text(entry),
                        "source_type": "library",
                        "object_type": entry["object_type"],
                        "urn": entry["urn"],
                        "ref_id": entry.get("ref_id", ""),
                        "name": entry.get("name", ""),
                        "framework": entry["framework"],
                        "framework_ref_id": entry.get("framework_ref_id", ""),
                        "provider": entry.get("provider", ""),
                        "locale": entry.get("locale", "en"),
                    },
                )
            )

        try:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            total_indexed += len(points)
        except Exception as e:
            logger.error(
                "library_upsert_failed",
                batch_start=batch_start,
                error=str(e),
            )

    logger.info(
        "library_indexing_complete",
        total_indexed=total_indexed,
        duration=round(time.time() - t0, 2),
    )
