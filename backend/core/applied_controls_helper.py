"""Merge N source AppliedControls into 1 target: union direct M2Ms, rewire
reverse relations + FKs + SyncMapping GFKs, hard-delete sources. Traceability
via django-auditlog + webhook dispatches."""

from __future__ import annotations

from typing import Any

import structlog
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import ForeignKey
from rest_framework.exceptions import PermissionDenied, ValidationError

logger = structlog.get_logger(__name__)


# Rewire contract: every reverse M2M on AppliedControl must be listed here.
# Keep aligned with AppliedControlViewSet.get_queryset() in views.py.
def _reverse_m2m_through_tables() -> list[tuple[Any, str]]:
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


def _through_fk_attnames(through_model) -> tuple[str, str]:
    from core.models import AppliedControl

    fk_fields = [
        f for f in through_model._meta.get_fields() if isinstance(f, ForeignKey)
    ]
    ac_field = next(f for f in fk_fields if f.related_model is AppliedControl)
    other_field = next(f for f in fk_fields if f.related_model is not AppliedControl)
    return ac_field.attname, other_field.attname


def _rewire_through(through_model, source_ids: list, target_id) -> int:
    """Move through-rows to target, dedupe against existing target pairs."""
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
    qs = fk_model.objects.filter(**{f"{fk_attname}__in": source_ids})
    count = qs.count()
    qs.update(**{fk_attname: target_id})
    return count


def _rewire_sync_mappings(source_ids: list, target_id) -> dict[str, int]:
    """Repoint SyncMapping GFKs, respecting the (configuration, content_type,
    local_object_id) uniqueness constraint."""
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


def _candidate_managed_documents(source_ids: list, target_id) -> list[dict]:
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
    """Conflict when 2+ distinct parties (sources or target) have docs.
    A single source with multiple docs is not a conflict — siblings stay."""
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
    """Repoint the kept doc to target; unlink (policy=None) every other candidate."""
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

    if keep_id is not None:
        ManagedDocument.objects.filter(id=keep_id).update(policy_id=target_id)
        result["kept"] = 1

    unlink_qs = ManagedDocument.objects.filter(id__in=candidate_ids)
    if keep_id is not None:
        unlink_qs = unlink_qs.exclude(id=keep_id)
    result["unlinked"] = unlink_qs.filter(
        policy_id__in=list(source_ids) + ([target_id] if target_id is not None else [])
    ).update(policy_id=None)
    return result


def _repoint_all_managed_documents(source_ids: list, target_id) -> int:
    try:
        from doc_management.models import ManagedDocument
    except ImportError:
        return 0
    return _rewire_fk(ManagedDocument, "policy_id", source_ids, target_id)


def _check_permissions(
    user,
    source_folders: list,
    target_folder,
    target_is_new: bool,
) -> None:
    from core.models import AppliedControl
    from iam.models import RoleAssignment

    # Scope Permission.objects.get by content_type to avoid MultipleObjectsReturned
    # on codename collisions across apps.
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


def merge_applied_controls(
    *,
    source_ids: list,
    target: dict,
    user,
    request=None,
    lookup_queryset=None,
    dry_run: bool = False,
    managed_document_resolution: dict | None = None,
) -> dict:
    """Merge N sources into 1 target. See module docstring for semantics.

    `lookup_queryset` should be the view's IAM-scoped queryset so UUIDs the
    caller can't see are treated as "not found". `request` is passed to the
    write serializer on target=new so its folder-access rules fire. Target
    creation happens inside the atomic block, after permissions and conflict
    checks, so failures never leak an orphan row."""
    from core.models import AppliedControl, Comment
    from iam.models import Folder
    from webhooks.service import dispatch_webhook_event

    lookup_queryset = (
        lookup_queryset if lookup_queryset is not None else AppliedControl.objects.all()
    )

    sources = list(lookup_queryset.filter(id__in=source_ids))
    found_ids = {str(s.id) for s in sources}
    missing = [str(sid) for sid in source_ids if str(sid) not in found_ids]
    if missing:
        raise ValidationError({"source_ids": f"Not found: {missing}"})

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
            existing = lookup_queryset.get(id=target["id"])
        except AppliedControl.DoesNotExist:
            raise ValidationError(
                f"Target applied control {target['id']} does not exist."
            )
        if str(existing.id) in found_ids:
            raise ValidationError(
                "The target applied control must not appear in source_ids."
            )
        target_existing_obj = existing
        target_folder = existing.folder

    source_folders = [s.folder for s in sources if s.folder is not None]
    _check_permissions(user, source_folders, target_folder, target_is_new)

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

    with transaction.atomic():
        # Lock sources + target and re-detect conflicts so concurrent writers
        # can't smuggle changes in between the dry-run preview and the rewire.
        locked_sources = list(
            AppliedControl.objects.select_for_update().filter(id__in=source_id_list)
        )
        if len(locked_sources) != len(source_id_list):
            raise ValidationError(
                "One or more source applied controls are no longer available."
            )
        if target_existing_obj is not None:
            AppliedControl.objects.select_for_update().filter(
                id=target_existing_obj.id
            ).first()

        locked_candidates = _candidate_managed_documents(source_id_list, md_target_id)
        locked_conflict = _detect_managed_document_conflict(
            source_id_list, md_target_id, locked_candidates
        )
        if locked_conflict is not None:
            keep_id = (managed_document_resolution or {}).get("keep")
            if not keep_id or keep_id not in {c["id"] for c in locked_candidates}:
                raise ValidationError(
                    {
                        "managed_document_resolution": (
                            "A managed-document conflict appeared during the merge; "
                            "please retry to pick which document to keep."
                        ),
                        "managed_document_conflict": locked_conflict,
                    }
                )
        sources = locked_sources
        md_candidates = locked_candidates
        md_conflict = locked_conflict

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

        unioned = _union_direct_m2ms(target_obj, sources)

        rewired: dict[str, int] = {}
        for through, key in _reverse_m2m_through_tables():
            rewired[key] = _rewire_through(through, source_id_list, target_obj.id)
        rewired["Comment"] = _rewire_fk(
            Comment, "applied_control_id", source_id_list, target_obj.id
        )

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

        sync_result = _rewire_sync_mappings(source_id_list, target_obj.id)

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

        AppliedControl.objects.filter(id__in=source_id_list).delete()

        # Refresh updated_at + re-trigger integration sync. Skip for a new
        # target: its initial save already did both, and M2M additions don't
        # affect any syncable field.
        if not target_is_new:
            target_obj.save()

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


def _compute_rewire_preview(source_ids: list) -> dict[str, int]:
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
