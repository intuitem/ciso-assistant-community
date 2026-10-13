"""Apply on accept: write an accepted response's results onto its subject,
through the targets its form lists in `on_accept`.

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


def form_targets(quick_form) -> list[tuple[dict, object]]:
    """(entry, target) pairs from the form's `on_accept`, unknown keys skipped
    (a library may name a target this version does not have)."""
    pairs = []
    for entry in getattr(quick_form, "on_accept", None) or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("config", {}), dict):
            # Skipped, so it fails closed; logged, so the form can be found.
            logger.warning("malformed_on_accept_entry", quick_form=str(quick_form.pk))
            continue
        target = get_target(str(entry.get("target") or ""))
        if target is None:
            logger.warning(
                "unknown_on_accept_target",
                target=entry.get("target"),
                quick_form=str(quick_form.pk),
            )
            continue
        pairs.append((entry, target))
    return pairs


def targets_of(quick_form) -> list[str]:
    return [target.key for _, target in form_targets(quick_form)]


def configured_targets(response) -> list[tuple[dict, object]]:
    return form_targets(response.quick_form)


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
            "origin": None,
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
        item["origin"] = target.origin(subject, response)
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
                **(
                    {"replaces": item["origin"]}
                    if readable and item.get("origin")
                    else {}
                ),
            }
        )
    return rows


def apply_on_accept(
    response, user, overrides: dict | None = None, items: list[dict] | None = None
) -> list[dict]:
    """Write every ready target of an accepted response. Returns the serialized
    plan with an `applied` flag per target. `items`: a plan already made for
    these overrides, not made again."""
    from core.models import QuickFormApplication

    if items is None:
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


def validate_on_accept_document(quick_form: dict) -> list[dict]:
    """Shape errors in a form document's `on_accept`, reported like rule
    errors when the builder saves: {where, ref_id, expression, error}. Which
    objects exist (tier keys…) is the instance's business: see the health."""
    from types import SimpleNamespace

    form = SimpleNamespace(
        outcomes_definition=quick_form.get("outcomes_definition") or []
    )
    errors = []
    for entry in quick_form.get("on_accept") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("config", {}), dict):
            errors.append(_setup_error("", "onAcceptEntryMalformed"))
            continue
        key = str(entry.get("target") or "")
        target = get_target(key)
        if target is None:
            errors.append(_setup_error(key, "unknownOnAcceptTarget"))
            continue
        for problem in target.validate_config(entry.get("config") or {}, form):
            errors.append(_setup_error(key, problem))
    return errors


def _setup_error(target: str, code: str) -> dict:
    return {"where": "on_accept", "ref_id": target, "expression": "", "error": code}


def on_accept_health(quick_form, cache: dict | None = None) -> list[dict]:
    """Per target, what keeps the form's setup from applying on this instance:
    a target this version lacks, a config the form's rules no longer support,
    or objects it names that are missing here (e.g. a tier key not on this
    scale)."""
    if not quick_form.on_accept:
        return []
    rows = []
    subject_model = _subject_model_of(quick_form)
    for entry in quick_form.on_accept:
        if not isinstance(entry, dict) or not isinstance(entry.get("config", {}), dict):
            rows.append(
                {"target": "", "label": "", "problems": ["onAcceptEntryMalformed"]}
            )
            continue
        key = str(entry.get("target") or "")
        target = get_target(key)
        if target is None:
            rows.append(
                {"target": key, "label": key, "problems": ["unknownOnAcceptTarget"]}
            )
            continue
        problems = []
        if subject_model != target.subject_model:
            problems.append("subjectModelMismatch")
        problems += target.health(entry.get("config") or {}, quick_form, cache)
        rows.append({"target": target.key, "label": target.label, "problems": problems})
    return rows


def project(
    entries: list[dict],
    computed_values,
    computed_outcome,
    *,
    ready: bool = True,
    score: float | None = None,
) -> list[dict]:
    """What each target would propose from these results. No subject and no
    permission involved: it reads the answers' results, never the object.
    Not `ready` (scored questions left unanswered) proposes nothing: an
    unanswered page scores 0 and would read as the lowest result."""
    from types import SimpleNamespace

    results = SimpleNamespace(
        computed_values=computed_values or {},
        computed_outcome=computed_outcome or {},
        score=score,
    )
    rows = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("config", {}), dict):
            continue
        target = get_target(str(entry.get("target") or ""))
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


def can_apply_on_submit(response, user, *, scored_complete: bool = True) -> bool:
    """Whether submitting can apply the form's targets at once: every
    target is ready and its permission on the subject is the submitter's own,
    so a review would grant nothing they do not already have. Anything less
    (no subject, nothing resolved, a missing right, scored questions left
    unanswered — they score 0 and would read as the lowest result) goes to
    review."""
    publication = getattr(response, "publication", None)
    if (
        not scored_complete
        or (publication is not None and publication.always_review)
        or not configured_targets(response)
    ):
        return False
    items = plan(response, user)
    return bool(items) and all(item["proposal"].ok for item in items)
