"""Bridge between the chat import workflow and the data_wizard consumers.

The import runs through the exact same RecordConsumer / write-serializer
path as the manual data wizard, so a chat-mediated import can never do more
than a wizard import could. On top of it this module adds the two things
data_wizard lacks: an atomic apply and a rollback-based dry-run.
"""

from __future__ import annotations

import structlog
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from .tabular import (
    IMPORT_TARGETS,
    MAX_COUNTED_ROWS,
    extract_records,
    permission_model_name,
)

logger = structlog.get_logger(__name__)

MAX_REPORTED_ERRORS = 5

# Consumer detail keys reported back as "created alongside the rows".
SIDE_EFFECT_LABELS = {
    "assets_created": "assets",
    "applied_controls_created": "applied controls",
}


def format_side_effects(details: dict | None) -> str:
    if not details:
        return ""
    return ", ".join(
        f"{details[key]} {label}"
        for key, label in SIDE_EFFECT_LABELS.items()
        if details.get(key)
    )


def check_import_permission(user, target_key: str, folder_id: str) -> bool:
    """Same `add_<model>` gate the manual wizard applies before consuming a file."""
    from data_wizard.views import may_import

    return may_import(user, permission_model_name(target_key), folder_id)


def container_name_from(doc) -> str:
    """Name a container created by this import after the uploaded file."""
    return (doc.filename or "").rsplit(".", 1)[0].strip()[:200]


def run_import(
    request,
    doc,
    mapping: dict[str, str],
    target_key: str,
    folder_id: str,
    dry_run: bool,
    target_id: str | None = None,
    matrix_id: str | None = None,
) -> dict:
    """Run rows of an uploaded document through the target's RecordConsumer.

    Returns {created, updated, skipped, failed, row_count, errors, details}
    where errors is a capped list of human-readable strings. With dry_run=True
    the whole run executes normally and is then rolled back, so the counts are
    exact — containers and name-referenced assets/controls included.
    """
    import data_wizard.views as dw

    if not check_import_permission(request.user, target_key, folder_id):
        logger.warning(
            "chat_import_denied",
            target=target_key,
            folder_id=folder_id,
            user_id=str(request.user.id),
        )
        raise PermissionDenied(
            "You are not allowed to import this object type into this domain."
        )

    target = IMPORT_TARGETS[target_key]
    consumer_cls = getattr(dw, target["consumer"])

    records = extract_records(doc, mapping)

    base_context = dw.BaseContext(
        request=request,
        folders_map=dw.get_accessible_folders_map(request.user),
        folder_id=folder_id,
        on_conflict=dw.ConflictMode.UPDATE,
        target_id=target_id,
        matrix_id=matrix_id,
        container_name=container_name_from(doc),
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
        "details": result.details,
    }
    logger.info(
        "chat_import_run",
        target=target_key,
        document_id=str(doc.id),
        dry_run=dry_run,
        **{k: v for k, v in report.items() if k != "errors"},
    )
    return report
