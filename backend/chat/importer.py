"""Bridge between the chat import workflow and the data_wizard consumers.

The import runs through the exact same RecordConsumer / write-serializer
path as the manual data wizard, so a chat-mediated import can never do more
than a wizard import could. On top of it this module adds the two things
data_wizard lacks: an atomic apply and a rollback-based dry-run.
"""

from __future__ import annotations

import structlog
from django.db import transaction

from .tabular import IMPORT_TARGETS, MAX_COUNTED_ROWS, extract_records

logger = structlog.get_logger(__name__)

MAX_REPORTED_ERRORS = 5


def run_import(
    request,
    doc,
    mapping: dict[str, str],
    target_key: str,
    folder_id: str,
    dry_run: bool,
    target_id: str | None = None,
) -> dict:
    """Run rows of an uploaded document through the target's RecordConsumer.

    Returns {created, updated, skipped, failed, row_count, errors} where
    errors is a capped list of human-readable strings. With dry_run=True the
    whole run executes normally and is then rolled back, so the counts are
    exact — including parent-container creation (e.g. findings assessments).
    """
    import data_wizard.views as dw

    target = IMPORT_TARGETS[target_key]
    consumer_cls = getattr(dw, target["consumer"])

    records = extract_records(doc, mapping)

    base_context = dw.BaseContext(
        request=request,
        folders_map=dw.get_accessible_folders_map(request.user),
        folder_id=folder_id,
        on_conflict=dw.ConflictMode.UPDATE,
        target_id=target_id,
    )

    with transaction.atomic():
        result = consumer_cls(base_context).process_records(records)
        if dry_run:
            transaction.set_rollback(True)

    report = {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "row_count": len(records),
        "truncated": len(records) >= MAX_COUNTED_ROWS,
        "errors": [str(e.error) for e in result.errors[:MAX_REPORTED_ERRORS]],
    }
    logger.info(
        "chat_import_run",
        target=target_key,
        document_id=str(doc.id),
        dry_run=dry_run,
        **{k: v for k, v in report.items() if k != "errors"},
    )
    return report
