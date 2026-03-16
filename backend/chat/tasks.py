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
