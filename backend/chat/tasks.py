"""
Huey background tasks for document ingestion and object indexing.
"""

import structlog
import uuid
from datetime import timedelta

from django.utils import timezone
from huey import crontab
from huey.contrib.djhuey import db_periodic_task, db_task

logger = structlog.get_logger(__name__)

#: How long an ingestion may hold its claim on a document. A worker stopped
#: mid-run never releases it, so the catch-up does once this has passed: keep
#: it above the longest ingestion, or a run still in progress is started again.
INGESTION_LEASE = timedelta(hours=6)


@db_task()
def ingest_document(document_id: str):
    """
    Async task: extract text from a document, chunk it, embed it, store in Qdrant.
    """
    from .models import IndexedDocument
    from .extractors import get_extractor
    from .providers import get_embedder
    from .rag import COLLECTION_NAME, get_qdrant_client

    # Claim it: the catch-up resubmits what looks stuck, and a second delivery
    # must not extract and embed the same document again.
    claimed = IndexedDocument.objects.filter(
        id=document_id, status=IndexedDocument.Status.PENDING
    ).update(status=IndexedDocument.Status.PROCESSING, updated_at=timezone.now())
    doc = IndexedDocument.objects.filter(id=document_id).first() if claimed else None
    if doc is None:
        logger.info("Document is not waiting for ingestion", document_id=document_id)
        return

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
                    "name": doc.filename,
                    **chunk.metadata,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]

        client.upsert(collection_name=COLLECTION_NAME, points=points)

        # The document may have been dropped or moved while this ran.
        if not IndexedDocument.objects.filter(id=doc.id).exists():
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=_document_filter([document_id]),
            )
            return
        _stamp_current_folders(client, [document_id])

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

    folder_id = _resolve_folder_id(obj)
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


@db_task()
def catch_up_indexing():
    """Queue evidence attachments and published documents missing from the index."""
    from .signals import index_missing_documents

    evidence, documents = index_missing_documents()
    logger.info(
        "Checked documents for indexing", evidence=evidence, documents=documents
    )
    index_library_knowledge_base()


@db_periodic_task(crontab(hour="3", minute="15"))
def index_missing_documents_nightly():
    """Catch up on documents the signals missed (chat disabled, worker down)."""
    from django.conf import settings

    from global_settings.utils import ff_is_enabled

    if settings.ENABLE_CHAT and ff_is_enabled("chat_mode"):
        catch_up_indexing.call_local()


def _document_filter(document_ids):
    from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

    # object_id carries the document id on chunks and, unlike document_id, has a
    # payload index (init_qdrant).
    return Filter(
        must=[
            FieldCondition(key="object_type", match=MatchValue(value="document_chunk")),
            FieldCondition(key="object_id", match=MatchAny(any=document_ids)),
        ]
    )


@db_task(retries=3, retry_delay=60)
def remove_document_chunks(document_id: str):
    """Remove an indexed document's chunks from the vector store."""
    from .rag import COLLECTION_NAME, get_qdrant_client

    try:
        get_qdrant_client().delete(
            collection_name=COLLECTION_NAME,
            points_selector=_document_filter([document_id]),
        )
    except Exception as e:
        logger.error(
            "Failed to remove document chunks", document_id=document_id, error=e
        )
        raise


def _stamp_current_folders(client, document_ids):
    """Write on each document's chunks the folder the database gives it now.

    The folder is read when writing, never handed over by the caller: a retry
    running late, or an ingestion racing with a move, would otherwise put an
    older folder back. The second pass catches a move committed in between.
    """
    from .models import IndexedDocument
    from .rag import COLLECTION_NAME

    written = {}
    for _ in range(2):
        by_folder = {}
        rows = IndexedDocument.objects.filter(id__in=document_ids).values_list(
            "id", "folder_id"
        )
        for doc_id, folder_id in rows:
            if written.get(doc_id) != folder_id:
                written[doc_id] = folder_id
                by_folder.setdefault(str(folder_id), []).append(str(doc_id))
        for folder_id, ids in by_folder.items():
            client.set_payload(
                collection_name=COLLECTION_NAME,
                payload={"folder_id": folder_id},
                points=_document_filter(ids),
            )


@db_task(retries=3, retry_delay=60)
def move_document_chunks(document_ids: list[str]):
    """Point indexed documents' chunks at the folder their document is in now."""
    from .rag import get_qdrant_client

    try:
        _stamp_current_folders(get_qdrant_client(), document_ids)
    except Exception as e:
        logger.error(
            "Failed to move document chunks", document_ids=document_ids, error=e
        )
        raise


def _resolve_folder_id(obj) -> str:
    """Walk the FK chain to find a folder_id for a model object.

    Most indexed models have FolderMixin (direct folder_id). RequirementAssessment
    has it too via FolderMixin, but we keep this helper future-proof for parent-FK
    resolutions (e.g. children of RequirementAssessment if we index those later).
    """
    direct = getattr(obj, "folder_id", None)
    if direct:
        return str(direct)
    for parent_attr in (
        "compliance_assessment",
        "risk_assessment",
        "questionnaire_run",
    ):
        parent = getattr(obj, parent_attr, None)
        if parent and getattr(parent, "folder_id", None):
            return str(parent.folder_id)
    return ""


# Text-building helpers used to live here. They moved to ``chat/text.py`` so
# ``chat/questionnaire.py`` can import them at top level without circularity.
from .text import (  # noqa: F401 — re-exported for callers that import via tasks
    _build_object_text,
    _normalize_model_name,
    _text_for_applied_control,
    _text_for_generic_model,
    _text_for_requirement_assessment,
)


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
    from core.utils import yaml_safe_load
    from library.builder import normalize_objects

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml_safe_load(f)
    except Exception as e:
        logger.warning("failed_to_parse_yaml", file=str(filepath), error=e)
        return []

    if not isinstance(data, dict):
        return []

    library_name = data.get("name", "")
    library_ref_id = data.get("ref_id", "")
    locale = data.get("locale", "en")
    provider = data.get("provider", "")

    entries = []
    # Both spellings are valid ("framework" is legacy): read the plural lists.
    objects = normalize_objects(data.get("objects", {}))

    # Index the library itself as a summary entry
    if library_name:
        lib_description = data.get("description", "")
        entries.append(
            {
                "urn": data.get("urn", ""),
                "ref_id": library_ref_id,
                "name": library_name,
                "description": lib_description,
                "annotation": "",
                "framework": library_name,
                "framework_ref_id": library_ref_id,
                "provider": provider,
                "locale": locale,
                "object_type": "framework",
            }
        )

    # Extract framework requirement nodes
    for framework in objects.get("frameworks") or []:
        if not isinstance(framework, dict):
            continue
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


def _library_point_id(entry: dict) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"library:{entry['urn']}"))


@db_task()
def index_library_knowledge_base():
    """
    Async task: parse all YAML library files and index requirement nodes,
    threats, and reference controls into Qdrant as shared knowledge.

    Uses source_type="library" — accessible to all authenticated users
    without folder-based permission filtering. Entries already indexed with
    the same text are skipped.
    """
    import time

    from .providers import get_embedder
    from .rag import (
        BM25_MODEL,
        BM25_VECTOR,
        COLLECTION_NAME,
        get_qdrant_client,
        has_bm25,
    )

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

    from qdrant_client.models import Document, PointStruct

    hybrid = has_bm25(client)
    BATCH_SIZE = 100
    total_indexed = 0

    for batch_start in range(0, len(all_entries), BATCH_SIZE):
        batch = all_entries[batch_start : batch_start + BATCH_SIZE]
        ids = [_library_point_id(e) for e in batch]
        try:
            indexed = {
                str(p.id): p.payload.get("text")
                for p in client.retrieve(
                    COLLECTION_NAME, ids=ids, with_payload=["text"]
                )
            }
        except Exception as e:
            logger.error("library_lookup_failed", batch_start=batch_start, error=e)
            indexed = {}
        batch = [
            e
            for e, point_id in zip(batch, ids)
            if indexed.get(point_id) != _build_library_entry_text(e)
        ]
        if not batch:
            continue
        texts = [_build_library_entry_text(e) for e in batch]

        try:
            embeddings = embedder.embed(texts)
        except Exception as e:
            logger.error(
                "library_embedding_failed",
                batch_start=batch_start,
                error=e,
            )
            continue

        points = []
        for entry, text, embedding in zip(batch, texts, embeddings):
            points.append(
                PointStruct(
                    id=_library_point_id(entry),
                    vector=(
                        {
                            "": embedding,
                            BM25_VECTOR: Document(text=text, model=BM25_MODEL),
                        }
                        if hybrid
                        else embedding
                    ),
                    payload={
                        "text": text,
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
                error=e,
            )

    logger.info(
        "library_indexing_complete",
        total_indexed=total_indexed,
        duration=round(time.time() - t0, 2),
    )


@db_task()
def update_session_summary(session_id: str):
    """Async wrapper around memory.update_summary_for_session."""
    from .memory import update_summary_for_session
    from .models import ChatSession
    from .providers import get_llm

    try:
        session = ChatSession.objects.get(pk=session_id)
    except ChatSession.DoesNotExist:
        return
    update_summary_for_session(session, get_llm())


# ---------------------------------------------------------------------------
# Questionnaire Autopilot — re-exports
# ---------------------------------------------------------------------------
# The questionnaire-specific code lives in chat/questionnaire.py. We re-export
# the public callables here so existing import sites (`from .tasks import
# parse_questionnaire`, etc.) keep working without churn, AND so importing
# chat.tasks at Django startup also imports chat.questionnaire — which is how
# the @db_task decorators in that module register with Huey.
from .questionnaire import (  # noqa: F401, E402
    # Huey tasks
    parse_questionnaire,
    suggest_value_mapping,
    run_questionnaire_prefill,
    refresh_folder_index,
    # Synchronous helpers called from view actions
    extract_questions_from_sheet,
    retry_question_with_hints,
    draft_applied_control_for_question,
    # Constants used by view validation
    _VALID_AC_CATEGORIES,
    _VALID_AC_CSF_FUNCTIONS,
    _VALID_AC_STATUSES,
)
