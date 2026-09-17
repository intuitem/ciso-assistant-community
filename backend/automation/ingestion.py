"""Posture result ingestion.

One write path, shared by the REST endpoint (`upload-results`, the file
importers) and the workflow engine's `post_results` action. Callers differ only
in how they report the outcome: the viewset wraps `IngestionError` into a DRF
Response, the action turns it into a node failure.
"""

import re
import uuid

from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import Asset, RequirementNode
from iam.models import RoleAssignment

from .models import PostureResult, PostureRun

UPDATE_FIELDS = [
    "result",
    "timestamp",
    "actual",
    "expected",
    "message",
    "source",
    "imported_by",
]


class IngestionError(Exception):
    """A rejected payload. `payload` is the body the REST endpoint returns."""

    def __init__(self, payload):
        self.payload = payload
        super().__init__(payload.get("error", "ingestion refused"))


def ingest_posture_results(
    assessment, *, asset_id, entries, run_id, source, tool, user
):
    """Upsert one batch of results. Returns the run summary.

    `run_id` is the patch contract: a provided id upserts on
    (run, asset, requirement) so a retried delivery is idempotent; an absent
    one starts a new run whose generated id comes back in the summary.
    """
    if not asset_id or not isinstance(entries, list) or not entries:
        raise IngestionError(
            {"error": "asset and a non-empty results list are required"}
        )
    if not all(isinstance(e, dict) for e in entries):
        raise IngestionError({"error": "results entries must be objects"})
    try:
        asset_id = uuid.UUID(str(asset_id))
    except TypeError, ValueError:
        raise IngestionError({"error": "asset must be a valid UUID"})

    asset = assessment.assets.filter(id=asset_id).first()
    enrolled = False
    if asset is None:
        asset = Asset.objects.filter(id=asset_id).first()
        if asset is None or not RoleAssignment.is_access_allowed(
            user=user,
            perm=Permission.objects.get(codename="view_asset"),
            folder=asset.folder if asset else assessment.folder,
        ):
            raise IngestionError({"error": "unknown asset", "asset": str(asset_id)})
        assessment.assets.add(asset)
        enrolled = True

    valid_results = set(PostureResult.Result.values)
    invalid = [e.get("ref_id") for e in entries if e.get("result") not in valid_results]
    if invalid:
        raise IngestionError({"error": "invalid result values", "ref_ids": invalid})

    if run_id:
        try:
            run_id = uuid.UUID(str(run_id))
        except ValueError:
            raise IngestionError({"error": "run_id must be a valid UUID"})
        if (
            PostureRun.objects.filter(id=run_id)
            .exclude(posture_assessment=assessment)
            .exists()
        ):
            raise IngestionError({"error": "run_id belongs to another assessment"})

    if source not in PostureResult.Source.values:
        raise IngestionError({"error": "invalid source"})

    timestamp = timezone.now()

    nodes = {
        node.ref_id: node
        for node in RequirementNode.objects.filter(
            framework=assessment.framework, assessable=True
        )
        if node.ref_id
    }

    def match(ref_id):
        node = nodes.get(ref_id)
        if node is None and ref_id:
            node = nodes.get(re.sub(r"^[^0-9]+", "", str(ref_id)))
        return node

    unknown_refs = [e.get("ref_id") for e in entries if match(e.get("ref_id")) is None]

    matched = {}
    for entry in entries:
        node = match(entry.get("ref_id"))
        if node is not None:
            matched[node.id] = entry

    try:
        with transaction.atomic():
            run, run_created = PostureRun.objects.get_or_create(
                id=run_id or uuid.uuid4(),
                posture_assessment=assessment,
                defaults={"started_at": timestamp, "tool": tool},
            )
            existing = {
                r.requirement_id: r
                for r in run.results.filter(asset=asset, requirement_id__in=matched)
            }
            to_create, to_update = [], []
            for node_id, entry in matched.items():
                fields = {
                    "result": entry["result"],
                    "timestamp": timestamp,
                    "actual": str(entry.get("actual") or "")[:255],
                    "expected": str(entry.get("expected") or "")[:255],
                    "message": str(entry.get("message") or ""),
                    "source": source,
                    "imported_by": user,
                }
                obj = existing.get(node_id)
                if obj is None:
                    to_create.append(
                        PostureResult(
                            run=run, asset=asset, requirement_id=node_id, **fields
                        )
                    )
                else:
                    for key, value in fields.items():
                        setattr(obj, key, value)
                    to_update.append(obj)
            PostureResult.objects.bulk_create(to_create, batch_size=500)
            if to_update:
                PostureResult.objects.bulk_update(
                    to_update, UPDATE_FIELDS, batch_size=500
                )
            if matched:
                assessment.prune_history({(asset.id, node_id) for node_id in matched})
            elif run_created:
                # Nothing matched, so the run this call opened is noise.
                run.delete()
                run = None
    except IntegrityError:
        raise IngestionError({"error": "run_id belongs to another assessment"})

    return {
        # None when the run was dropped: reporting a deleted id would let a
        # retry be configured against a row that is not there.
        "run_id": str(run.id) if run else None,
        "created": len(to_create),
        "updated": len(to_update),
        "unknown_ref_ids": unknown_refs,
        "enrolled_asset": enrolled,
    }
