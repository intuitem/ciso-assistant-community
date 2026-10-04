"""Apply on accept: write an accepted response's results onto its subject,
through the targets its publication lists in `on_accept`.

Rules shared by every target:
- only on the accepting transition (closed + accepted);
- the reviewer needs the target's permission on the subject, else that target
  writes nothing (no silent elevation);
- fail closed per target: a value that cannot be worked out is never guessed;
- every write is logged as a QuickFormApplication.

`closed` is terminal in the response state machine today. A transition that
reopens a closed response would have to undo these writes.
"""

import structlog
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from core.quick_form_targets import Proposal, get_target

logger = structlog.get_logger(__name__)


def configured_targets(response) -> list[tuple[dict, object]]:
    """(entry, target) pairs from the response's publication, unknown keys
    skipped (they were refused on save; a later code change may drop one)."""
    publication = getattr(response, "publication", None)
    if publication is None:
        return []
    pairs = []
    for entry in publication.on_accept or []:
        target = get_target(str((entry or {}).get("target") or ""))
        if target is None:
            logger.warning(
                "unknown_on_accept_target",
                target=(entry or {}).get("target"),
                publication=str(publication.pk),
            )
            continue
        pairs.append((entry, target))
    return pairs


def _subject_for(response, target):
    """The subject if it is the target's model, else None."""
    if not response.subject_content_type_id or not response.subject_object_id:
        return None
    model = response.subject_content_type.model_class()
    if model is None or model._meta.label != target.subject_model:
        return None
    return model.objects.filter(pk=response.subject_object_id).first()


def _readable(user, subject) -> bool:
    from iam.models import RoleAssignment

    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return RoleAssignment.is_object_readable(user, type(subject), subject.pk)


def _allowed(user, target, subject) -> bool:
    from iam.models import Folder, Permission, RoleAssignment

    permission = Permission.objects.filter(codename=target.permission).first()
    if permission is None or user is None:
        return False
    return RoleAssignment.is_access_allowed(
        user=user, perm=permission, folder=Folder.get_folder(subject)
    )


def plan(response, user, overrides: dict | None = None) -> list[dict]:
    """What accepting would write, target by target. Each item carries the
    target, its proposal (or the reason it cannot apply) and the current value."""
    overrides = overrides or {}
    items = []
    for entry, target in configured_targets(response):
        item = {
            "target": target.key,
            "label": target.label,
            "subject": None,
            "current": None,
            "proposal": None,
            # Whether the caller may see the subject's name and current value;
            # the subject itself is kept for the write either way.
            "readable": False,
        }
        subject = _subject_for(response, target)
        if subject is None:
            item["proposal"] = Proposal.refuse("noSubject")
            items.append(item)
            continue
        item["subject"] = subject
        item["current"] = target.current(subject)
        item["readable"] = _readable(user, subject)
        if not _allowed(user, target, subject):
            item["proposal"] = Proposal.refuse("subjectPermissionRequired")
            items.append(item)
            continue
        try:
            item["proposal"] = target.resolve(
                response, entry.get("config") or {}, override=overrides.get(target.key)
            )
        except Exception as e:
            logger.error(
                "on_accept_resolve_failed",
                target=target.key,
                response=str(response.pk),
                error=e,
            )
            item["proposal"] = Proposal.refuse("targetError")
        items.append(item)
    return items


def serialize_plan(items: list[dict]) -> list[dict]:
    rows = []
    for item in items:
        proposal = item["proposal"]
        # Name and current value only for a caller who may view the subject.
        readable = item.get("readable", False)
        current = item["current"] if readable else None
        rows.append(
            {
                "target": item["target"],
                "label": item["label"],
                "subject": str(item["subject"])
                if item["subject"] and readable
                else None,
                "ok": proposal.ok,
                "reason": proposal.reason,
                "current": current[1] if current else None,
                "proposed": proposal.display if proposal.ok else None,
                "overridden": proposal.overridden,
                **({"extra": proposal.extra} if proposal.extra else {}),
            }
        )
    return rows


def apply_on_accept(response, user, overrides: dict | None = None) -> list[dict]:
    """Write every ready target of an accepted response. Returns the serialized
    plan with an `applied` flag per target."""
    from core.models import QuickFormApplication

    items = plan(response, user, overrides)
    for item in items:
        item["applied"] = False
        proposal = item["proposal"]
        if not proposal.ok:
            continue
        target = get_target(item["target"])
        subject = item["subject"]
        previous_value, previous_display = item["current"]
        try:
            # One savepoint per target: a failure rolls back that target's writes
            # and its log row together, and keeps the request's transaction usable.
            with transaction.atomic():
                target.apply(subject, proposal, response=response, user=user)
                QuickFormApplication.objects.create(
                    response=response,
                    target=target.key,
                    subject_content_type=ContentType.objects.get_for_model(subject),
                    subject_object_id=subject.pk,
                    previous_value=previous_value,
                    previous_display=str(previous_display or "")[:255],
                    new_value=proposal.value,
                    new_display=str(proposal.display or "")[:255],
                    overridden=proposal.overridden,
                    note=proposal.note or "",
                    applied_by=user
                    if getattr(user, "is_authenticated", False)
                    else None,
                )
        except Exception as e:
            logger.error(
                "on_accept_apply_failed",
                target=target.key,
                response=str(response.pk),
                error=e,
            )
            item["proposal"] = Proposal.refuse("targetError")
            continue
        item["applied"] = True

    rows = serialize_plan(items)
    for row, item in zip(rows, items):
        row["applied"] = item["applied"]
    return rows


def target_choices() -> list[dict]:
    from core.quick_form_targets import TARGETS

    return [
        {
            "key": t.key,
            "label": t.label,
            "subject_model": t.subject_model,
            "model_name": apps.get_model(t.subject_model)._meta.model_name,
        }
        for t in TARGETS.values()
    ]


def _subject_model_of(quick_form) -> str | None:
    """app_label.ModelName the form's subject question points at, if any."""
    from core.models import QuickFormResponse
    from core.object_references import REFERENCEABLE

    question = QuickFormResponse(quick_form=quick_form).subject_question()
    if question is None:
        return None
    return REFERENCEABLE[question.config["model"]]["model"]


def validate_on_accept(on_accept, quick_form) -> list[str]:
    """Errors that refuse saving a publication's `on_accept`."""
    if on_accept in (None, []):
        return []
    if not isinstance(on_accept, list):
        return ["onAcceptMustBeAList"]
    errors = []
    seen = set()
    subject_model = _subject_model_of(quick_form) if quick_form else None
    for entry in on_accept:
        if not isinstance(entry, dict) or not isinstance(entry.get("config", {}), dict):
            errors.append("onAcceptEntryMalformed")
            continue
        key = str(entry.get("target") or "")
        target = get_target(key)
        if target is None:
            errors.append(f"unknownOnAcceptTarget:{key}")
            continue
        if key in seen:
            errors.append(f"duplicateOnAcceptTarget:{key}")
            continue
        seen.add(key)
        if subject_model != target.subject_model:
            errors.append(f"subjectModelMismatch:{key}")
            continue
        errors += [
            f"{key}:{error}"
            for error in target.validate_config(entry.get("config") or {}, quick_form)
        ]
    return errors


def on_accept_health(publication) -> list[dict]:
    """Per target, what a library upgrade broke since the config was saved."""
    from core.models import QuickFormResponse

    rows = []
    subject_model = _subject_model_of(publication.quick_form)
    probe = QuickFormResponse(
        quick_form=publication.quick_form, publication=publication
    )
    for entry, target in configured_targets(probe):
        problems = []
        if subject_model != target.subject_model:
            problems.append("subjectModelMismatch")
        problems += target.health(entry.get("config") or {}, publication.quick_form)
        rows.append({"target": target.key, "label": target.label, "problems": problems})
    return rows


def suggested_on_accept(quick_form) -> list[dict]:
    """The form's library-suggested `on_accept`, made concrete for this
    instance. Entries that do not fit (unknown target, other subject model,
    scale too short, config refused) are left out."""
    entries = []
    subject_model = _subject_model_of(quick_form)
    for entry in quick_form.on_accept_suggestion or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("config"), dict):
            continue
        target = get_target(str(entry.get("target") or ""))
        if target is None or target.subject_model != subject_model:
            continue
        config = target.materialize(entry["config"])
        if config is None or target.validate_config(config, quick_form):
            continue
        entries.append({"target": target.key, "config": config})
    return entries


def project(
    entries: list[dict], computed_values, computed_outcome, *, ready: bool = True
) -> list[dict]:
    """What each target would propose from these results. No subject and no
    permission involved: it reads the answers' results, never the object.
    Not `ready` (scored questions left unanswered) proposes nothing: an
    unanswered page scores 0 and would read as the lowest result."""
    from types import SimpleNamespace

    results = SimpleNamespace(
        computed_values=computed_values or {}, computed_outcome=computed_outcome or {}
    )
    rows = []
    for entry in entries:
        target = get_target(str((entry or {}).get("target") or ""))
        if target is None:
            continue
        try:
            proposal = (
                target.resolve(results, entry.get("config") or {})
                if ready
                else Proposal.refuse("projectionPending")
            )
        except Exception as e:
            logger.error("on_accept_projection_failed", target=target.key, error=e)
            proposal = Proposal.refuse("targetError")
        rows.append(
            {
                "target": target.key,
                "label": target.label,
                "ok": proposal.ok,
                "reason": proposal.reason,
                "proposed": proposal.display if proposal.ok else None,
                "value": (proposal.value or {}).get("value")
                if isinstance(proposal.value, dict)
                else None,
                **({"extra": proposal.extra} if proposal.extra else {}),
            }
        )
    return rows


def can_apply_on_submit(response, user) -> bool:
    """Whether submitting can apply the publication's targets at once: every
    target is ready and its permission on the subject is the submitter's own,
    so a review would grant nothing they do not already have. Anything less
    (no subject, nothing resolved, a missing right) goes to review."""
    publication = getattr(response, "publication", None)
    if publication is None or publication.always_review or not publication.on_accept:
        return False
    items = plan(response, user)
    return bool(items) and all(item["proposal"].ok for item in items)
