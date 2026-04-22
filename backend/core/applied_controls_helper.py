"""Merge operations for AppliedControl.

Implements the primitive: "rewire all references from N source controls to
1 target control, union direct M2Ms onto the target, then hard-delete the
sources." The same primitive powers the batch merge flow and the single-row
"Replace with…" flow.

Traceability comes from django-auditlog (already registered for AppliedControl)
plus webhook "deleted"/"updated" dispatches. No dedicated merge-log model.
"""

from __future__ import annotations

from typing import Any

import structlog
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import ForeignKey
from rest_framework.exceptions import PermissionDenied, ValidationError

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Reverse-relation inventory
# ---------------------------------------------------------------------------
# The 13 reverse M2Ms plus 2 FKs that point at AppliedControl. This list is the
# rewire contract — if a new relation is added on AppliedControl, it must be
# added here as well. Keep aligned with AppliedControlViewSet.get_queryset()
# in backend/core/views.py.


def _reverse_m2m_through_tables() -> list[tuple[Any, str]]:
    """Return [(through_model, response_key)] for every reverse M2M on AppliedControl."""
    # Local imports to avoid load-time cycles.
    from core.models import (
        Finding,
        RequirementAssessment,
        RiskScenario,
        TaskTemplate,
        Vulnerability,
    )
    from crq.models import QuantitativeRiskHypothesis
    from ebios_rm.models import Stakeholder
    from privacy.models import DataBreach, Processing
    from resilience.models import AssetAssessment

    return [
        (RequirementAssessment.applied_controls.through, "RequirementAssessment"),
        (RiskScenario.applied_controls.through, "RiskScenario"),
        (RiskScenario.existing_applied_controls.through, "RiskScenario_existing"),
        (Finding.applied_controls.through, "Finding"),
        (Vulnerability.applied_controls.through, "Vulnerability"),
        (TaskTemplate.applied_controls.through, "TaskTemplate"),
        (Stakeholder.applied_controls.through, "Stakeholder"),
        (Processing.associated_controls.through, "Processing"),
        (DataBreach.remediation_measures.through, "DataBreach"),
        (
            QuantitativeRiskHypothesis.existing_applied_controls.through,
            "QuantitativeRiskHypothesis_existing",
        ),
        (
            QuantitativeRiskHypothesis.added_applied_controls.through,
            "QuantitativeRiskHypothesis_added",
        ),
        (
            QuantitativeRiskHypothesis.removed_applied_controls.through,
            "QuantitativeRiskHypothesis_removed",
        ),
        (AssetAssessment.associated_controls.through, "AssetAssessment"),
    ]


DIRECT_M2M_FIELDS: tuple[str, ...] = (
    "evidences",
    "assets",
    "owner",
    "security_exceptions",
    "objectives",
    "filtering_labels",
)


# ---------------------------------------------------------------------------
# Rewire helpers
# ---------------------------------------------------------------------------


def _through_fk_attnames(through_model) -> tuple[str, str]:
    """Return (appliedcontrol_attname, other_attname) for the through table."""
    from core.models import AppliedControl

    fk_fields = [
        f for f in through_model._meta.get_fields() if isinstance(f, ForeignKey)
    ]
    ac_field = next(f for f in fk_fields if f.related_model is AppliedControl)
    other_field = next(f for f in fk_fields if f.related_model is not AppliedControl)
    return ac_field.attname, other_field.attname


def _rewire_through(through_model, source_ids: list, target_id) -> int:
    """Move through-rows from sources to target, dedupe against existing target pairs.

    Returns the number of source-side rows that were resolved (either collapsed
    into an existing target pair or newly repointed)."""
    ac_attname, other_attname = _through_fk_attnames(through_model)

    existing_target_others = set(
        through_model.objects.filter(**{ac_attname: target_id}).values_list(
            other_attname, flat=True
        )
    )
    source_others = set(
        through_model.objects.filter(**{f"{ac_attname}__in": source_ids}).values_list(
            other_attname, flat=True
        )
    )
    to_create = source_others - existing_target_others
    if to_create:
        through_model.objects.bulk_create(
            [
                through_model(**{ac_attname: target_id, other_attname: oid})
                for oid in to_create
            ],
            ignore_conflicts=True,
        )
    deleted, _ = through_model.objects.filter(
        **{f"{ac_attname}__in": source_ids}
    ).delete()
    return deleted


def _rewire_fk(fk_model, fk_attname: str, source_ids: list, target_id) -> int:
    """Bulk update an FK from source ids to target id. Returns rows updated."""
    qs = fk_model.objects.filter(**{f"{fk_attname}__in": source_ids})
    count = qs.count()
    qs.update(**{fk_attname: target_id})
    return count


def _rewire_sync_mappings(source_ids: list, target_id) -> dict[str, int]:
    """Repoint SyncMapping GFKs while respecting (configuration, content_type, local_object_id)."""
    from core.models import AppliedControl
    from integrations.models import SyncMapping

    ct = ContentType.objects.get_for_model(AppliedControl)
    target_configs = set(
        SyncMapping.objects.filter(
            content_type=ct, local_object_id=target_id
        ).values_list("configuration_id", flat=True)
    )
    moved = 0
    deleted = 0
    for sm in SyncMapping.objects.filter(
        content_type=ct, local_object_id__in=source_ids
    ):
        if sm.configuration_id in target_configs:
            sm.delete()
            deleted += 1
        else:
            sm.local_object_id = target_id
            sm.save(update_fields=["local_object_id"])
            target_configs.add(sm.configuration_id)
            moved += 1
    return {"moved": moved, "deleted": deleted}


def _union_direct_m2ms(target, sources) -> dict[str, int]:
    """Union direct M2M fields from every source onto the target."""
    counts = {}
    for field_name in DIRECT_M2M_FIELDS:
        related = getattr(target, field_name, None)
        if related is None:
            continue
        for src in sources:
            src_related = getattr(src, field_name, None)
            if src_related is None:
                continue
            related.add(*src_related.all())
        counts[field_name] = related.count()
    return counts


# ---------------------------------------------------------------------------
# Managed documents
# ---------------------------------------------------------------------------


def _candidate_managed_documents(source_ids: list, target_id) -> list[dict]:
    """Return every ManagedDocument currently attached to any source or the target."""
    try:
        from doc_management.models import ManagedDocument
    except ImportError:
        return []

    policy_ids = list(source_ids)
    if target_id is not None:
        policy_ids.append(target_id)
    docs = ManagedDocument.objects.filter(policy_id__in=policy_ids).values(
        "id", "name", "policy_id"
    )
    return [
        {"id": str(d["id"]), "name": d["name"], "policy_id": str(d["policy_id"])}
        for d in docs
    ]


def _detect_managed_document_conflict(
    source_ids: list, target_id, candidates: list[dict]
) -> dict | None:
    """A conflict exists when 2+ distinct 'parties' (sources or target) have docs.

    A single source with multiple docs is NOT a conflict — siblings from the same
    control stay as siblings on the merged target.
    """
    parties_with_docs = {d["policy_id"] for d in candidates}
    if len(parties_with_docs) < 2:
        return None
    return {
        "parties_with_docs": sorted(parties_with_docs),
        "candidates": candidates,
    }


def _apply_managed_document_resolution(
    source_ids: list,
    target_id,
    candidates: list[dict],
    keep_id: str | None,
) -> dict[str, int]:
    """For the kept doc: repoint to target. For every other candidate: unlink (policy=None)."""
    try:
        from doc_management.models import ManagedDocument
    except ImportError:
        return {"kept": 0, "unlinked": 0, "repointed": 0}

    candidate_ids = {c["id"] for c in candidates}
    if keep_id is not None and keep_id not in candidate_ids:
        raise ValidationError(
            "managed_document_resolution.keep must be one of the candidate document ids."
        )

    result = {"kept": 0, "unlinked": 0, "repointed": 0}

    # 1. Kept doc -> target (may already be on target; update is idempotent)
    if keep_id is not None:
        ManagedDocument.objects.filter(id=keep_id).update(policy_id=target_id)
        result["kept"] = 1

    # 2. Every other candidate currently on a source or the target gets unlinked.
    unlink_qs = ManagedDocument.objects.filter(id__in=candidate_ids)
    if keep_id is not None:
        unlink_qs = unlink_qs.exclude(id=keep_id)
    result["unlinked"] = unlink_qs.filter(
        policy_id__in=list(source_ids) + ([target_id] if target_id is not None else [])
    ).update(policy_id=None)
    return result


def _repoint_all_managed_documents(source_ids: list, target_id) -> int:
    """No-conflict path: every source doc gets repointed to the target."""
    try:
        from doc_management.models import ManagedDocument
    except ImportError:
        return 0
    return _rewire_fk(ManagedDocument, "policy_id", source_ids, target_id)


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


def _check_permissions(
    user,
    source_folders: list,
    target_folder,
    target_is_new: bool,
) -> None:
    """Raise PermissionDenied if user lacks the required perm on any relevant folder."""
    from core.models import AppliedControl
    from iam.models import RoleAssignment

    # Scope by content_type so a codename collision from another app can't
    # trigger MultipleObjectsReturned.
    ct = ContentType.objects.get_for_model(AppliedControl)
    change = Permission.objects.get(codename="change_appliedcontrol", content_type=ct)
    delete = Permission.objects.get(codename="delete_appliedcontrol", content_type=ct)
    add = Permission.objects.get(codename="add_appliedcontrol", content_type=ct)

    for folder in source_folders:
        if not RoleAssignment.is_access_allowed(user=user, perm=change, folder=folder):
            raise PermissionDenied(
                f"Missing change permission on source folder '{folder}'."
            )
        if not RoleAssignment.is_access_allowed(user=user, perm=delete, folder=folder):
            raise PermissionDenied(
                f"Missing delete permission on source folder '{folder}'."
            )
    if target_folder is not None:
        if not RoleAssignment.is_access_allowed(
            user=user, perm=change, folder=target_folder
        ):
            raise PermissionDenied(
                f"Missing change permission on target folder '{target_folder}'."
            )
        if target_is_new and not RoleAssignment.is_access_allowed(
            user=user, perm=add, folder=target_folder
        ):
            raise PermissionDenied(
                f"Missing add permission on target folder '{target_folder}'."
            )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def merge_applied_controls(
    *,
    source_ids: list,
    target: dict,
    user,
    request=None,
    dry_run: bool = False,
    managed_document_resolution: dict | None = None,
) -> dict:
    """Merge primitive.

    Args:
        source_ids: list of AppliedControl UUIDs to absorb (1..20, already deduped
            by the serializer and with any target id already stripped).
        target: {"type": "new", "fields": {...}} or {"type": "existing", "id": "..."}.
        user: authenticated user performing the merge.
        request: DRF request object (optional). When provided, it is passed as
            serializer context on target=new creation so folder-access rules that
            depend on ``context['request']`` are enforced.
        dry_run: if True, returns the would-be response (including managed_document
            conflict info) without touching state.
        managed_document_resolution: {"keep": "<doc_id>"} — required on real merge
            when a managed-document conflict exists.

    Returns a dict with `target_id`, `target_is_new`, `folder_mismatch`, `rewired`,
    `unioned_m2m`, `managed_documents`, `managed_document_conflict`, `sync_mappings`,
    `deleted_sources`.

    Security notes:
    - Target creation (target=new) happens inside the atomic block, **after**
      permission checks and managed-document conflict validation, so a failure
      never leaves an orphan AppliedControl behind.
    - Source/target folder permissions are checked against the raw folder IDs
      *before* any mutation; the write serializer for target=new is given request
      context so its own folder-access rules apply.
    """
    from core.models import AppliedControl, Comment
    from iam.models import Folder
    from webhooks.service import dispatch_webhook_event

    # -- 1. Fetch and validate sources ---------------------------------------
    sources = list(AppliedControl.objects.filter(id__in=source_ids))
    found_ids = {str(s.id) for s in sources}
    missing = [str(sid) for sid in source_ids if str(sid) not in found_ids]
    if missing:
        raise ValidationError({"source_ids": f"Not found: {missing}"})

    # AppliedControl does not inherit from LibraryMixin, so it has no `urn` or
    # `builtin` fields. Nothing to guard against here — kept as a comment in case
    # those fields are ever added later.

    # -- 2. Pre-validate target (no creation or mutation yet) -----------------
    target_is_new = target["type"] == "new"
    target_existing_obj: AppliedControl | None = None

    if target_is_new:
        fields = target.get("fields") or {}
        folder_id = fields.get("folder")
        if not folder_id:
            raise ValidationError(
                {"target": "fields.folder is required when target.type='new'"}
            )
        try:
            target_folder = Folder.objects.get(id=folder_id)
        except Folder.DoesNotExist:
            raise ValidationError({"target.fields.folder": "Folder does not exist."})
    else:
        try:
            existing = AppliedControl.objects.get(id=target["id"])
        except AppliedControl.DoesNotExist:
            raise ValidationError(
                f"Target applied control {target['id']} does not exist."
            )
        # Defense in depth — serializer already stripped target from source_ids.
        if str(existing.id) in found_ids:
            raise ValidationError(
                "The target applied control must not appear in source_ids."
            )
        target_existing_obj = existing
        target_folder = existing.folder

    # -- 3. Permission checks BEFORE any mutation ---------------------------
    source_folders = [s.folder for s in sources if s.folder is not None]
    _check_permissions(user, source_folders, target_folder, target_is_new)

    # -- 4. Managed-document conflict ---------------------------------------
    source_id_list = [s.id for s in sources]
    md_target_id = target_existing_obj.id if target_existing_obj is not None else None
    md_candidates = _candidate_managed_documents(source_id_list, md_target_id)
    md_conflict = _detect_managed_document_conflict(
        source_id_list, md_target_id, md_candidates
    )

    folder_mismatch = any(
        (s.folder_id if s.folder else None)
        != (target_folder.id if target_folder else None)
        for s in sources
    )

    # -- 5. Dry-run short-circuit -------------------------------------------
    if dry_run:
        return {
            "target_id": str(target_existing_obj.id) if target_existing_obj else None,
            "target_is_new": target_is_new,
            "target_folder_id": str(target_folder.id) if target_folder else None,
            "source_folder_ids": sorted({str(f.id) for f in source_folders}),
            "folder_mismatch": folder_mismatch,
            "managed_document_conflict": md_conflict,
            "rewired_preview": _compute_rewire_preview(source_id_list),
            "unioned_m2m_preview": _compute_union_preview(
                sources, target_existing_obj, target_is_new
            ),
            "deleted_sources_preview": [str(s.id) for s in sources],
        }

    # -- 6. Real merge: conflict must be resolved ---------------------------
    if md_conflict is not None:
        keep_id = (managed_document_resolution or {}).get("keep")
        if not keep_id:
            raise ValidationError(
                {
                    "managed_document_resolution": (
                        "Required: multiple applied controls have managed documents; "
                        "pick one to retain."
                    ),
                    "managed_document_conflict": md_conflict,
                }
            )

    # -- 7. Atomic create-target (if new) + rewire + delete -----------------
    with transaction.atomic():
        # 7.0. Persist target now that permissions + conflict checks have passed.
        if target_is_new:
            from core.serializers import AppliedControlWriteSerializer

            serializer_context = {"request": request} if request is not None else {}
            serializer = AppliedControlWriteSerializer(
                data=target.get("fields") or {}, context=serializer_context
            )
            serializer.is_valid(raise_exception=True)
            target_obj = serializer.save()
        else:
            assert target_existing_obj is not None  # pyright hint
            target_obj = target_existing_obj

        # 7a. Direct M2M union onto target
        unioned = _union_direct_m2ms(target_obj, sources)

        # 7b. Reverse M2M rewire
        rewired: dict[str, int] = {}
        for through, key in _reverse_m2m_through_tables():
            rewired[key] = _rewire_through(through, source_id_list, target_obj.id)

        # 7c. Comment FK
        rewired["Comment"] = _rewire_fk(
            Comment, "applied_control_id", source_id_list, target_obj.id
        )

        # 7d. Managed documents
        if md_conflict is not None:
            md_result = _apply_managed_document_resolution(
                source_id_list,
                target_obj.id,
                md_candidates,
                (managed_document_resolution or {}).get("keep"),
            )
        else:
            repointed = _repoint_all_managed_documents(source_id_list, target_obj.id)
            md_result = {"kept": 0, "unlinked": 0, "repointed": repointed}

        # 7e. SyncMapping GFK
        sync_result = _rewire_sync_mappings(source_id_list, target_obj.id)

        # 7f. Dispatch deletion webhooks before actually deleting
        source_snapshots = [
            {"id": str(s.id), "name": s.name, "urn": getattr(s, "urn", None)}
            for s in sources
        ]
        for src in sources:
            try:
                dispatch_webhook_event(src, "deleted")
            except Exception:
                logger.error(
                    "Webhook dispatch failed during merge (deleted)", exc_info=True
                )

        # 7g. Hard-delete sources (auditlog LogEntry rows are preserved)
        AppliedControl.objects.filter(id__in=source_id_list).delete()

        # 7h. Touch target so updated_at refreshes and integration sync fires.
        # Skip for a freshly-created target — its initial save already did that
        # and M2M additions don't trigger a second sync on syncable fields.
        if not target_is_new:
            target_obj.save()

        # 7i. Update webhook on target
        try:
            dispatch_webhook_event(target_obj, "updated")
        except Exception:
            logger.error(
                "Webhook dispatch failed during merge (updated)", exc_info=True
            )

    logger.info(
        "Applied controls merged",
        source_ids=[s["id"] for s in source_snapshots],
        target_id=str(target_obj.id),
        target_is_new=target_is_new,
        folder_mismatch=folder_mismatch,
        merged_by=str(getattr(user, "id", None)),
    )

    return {
        "target_id": str(target_obj.id),
        "target_is_new": target_is_new,
        "target_folder_id": str(target_folder.id) if target_folder else None,
        "folder_mismatch": folder_mismatch,
        "rewired": rewired,
        "unioned_m2m": unioned,
        "managed_documents": md_result,
        "managed_document_conflict": md_conflict,
        "sync_mappings": sync_result,
        "deleted_sources": source_snapshots,
    }


# ---------------------------------------------------------------------------
# Dry-run previews
# ---------------------------------------------------------------------------


def _compute_rewire_preview(source_ids: list) -> dict[str, int]:
    """Count rows currently attached to sources, per through-table / FK."""
    from core.models import Comment

    counts: dict[str, int] = {}
    for through, key in _reverse_m2m_through_tables():
        ac_attname, _ = _through_fk_attnames(through)
        counts[key] = through.objects.filter(
            **{f"{ac_attname}__in": source_ids}
        ).count()
    counts["Comment"] = Comment.objects.filter(
        applied_control_id__in=source_ids
    ).count()
    try:
        from doc_management.models import ManagedDocument

        counts["ManagedDocument"] = ManagedDocument.objects.filter(
            policy_id__in=source_ids
        ).count()
    except ImportError:
        pass
    return counts


def _compute_union_preview(sources, target_obj, target_is_new: bool) -> dict[str, int]:
    """Count of items the target would gain per direct M2M after union."""
    counts: dict[str, int] = {}
    for field_name in DIRECT_M2M_FIELDS:
        existing: set = set()
        if not target_is_new and target_obj.pk is not None:
            existing = set(getattr(target_obj, field_name).values_list("id", flat=True))
        gained: set = set()
        for src in sources:
            src_related = getattr(src, field_name, None)
            if src_related is None:
                continue
            for obj_id in src_related.values_list("id", flat=True):
                if obj_id not in existing:
                    gained.add(obj_id)
        counts[field_name] = len(gained)
    return counts
