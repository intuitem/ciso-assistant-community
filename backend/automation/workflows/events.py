"""Internal event triggers: start workflows when something happens
inside CISO Assistant.

Two halves:

- `dispatch_internal_event(...)` — the generic seam. Any producer (today the
  auditlog CUD mirror, later portal actions or other app events) calls it with
  a string event key and a payload; matching enabled triggers start their
  workflow's published version.
- The CUD producer — a post_save receiver on auditlog's LogEntry (connected in
  apps.ready), mirroring webhooks/signals.py. LogEntry is the broadest hook:
  it covers every audited model, catches m2m changes, and carries the
  field-level old→new diff that transition filters need.

Loop containment: runs carry a trigger_depth; changes made by a run at depth
d dispatch events at depth d, which start instances at depth d+1, capped at
MAX_TRIGGER_DEPTH.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

import structlog

from iam.models import Folder

from .models import Condition, WorkflowInstance, WorkflowNode, WorkflowTrigger

logger = structlog.get_logger(__name__)

MAX_TRIGGER_DEPTH = 5

# How long one user action's events keep collapsing into its first run.
COALESCE_WINDOW = timedelta(minutes=5)

CUD_ACTIONS = ["created", "updated", "deleted"]

VALID_FILTER_OPS = {choice[0] for choice in Condition.Operator.choices}
MAX_FILTER_DEPTH = 5


def _log_entry_verb(action):
    """Map an auditlog LogEntry.Action to its CUD event verb, or None for
    non-CUD actions (e.g. ACCESS). auditlog imported lazily like elsewhere."""
    from auditlog.models import LogEntry

    return {
        LogEntry.Action.CREATE: "created",
        LogEntry.Action.UPDATE: "updated",
        LogEntry.Action.DELETE: "deleted",
    }.get(action)


def make_event_key(model_name, verb):
    """Canonical internal-event key format. Keep producer and consumer in step
    by minting keys through here only."""
    return f"{model_name}.{verb}"


def event_key_catalog():
    """All CUD event keys, derived from the auditlog registry so new model
    registrations appear automatically."""
    from auditlog.registry import auditlog

    keys = []
    for model in sorted(auditlog.get_models(), key=lambda m: m._meta.model_name):
        # Skip the workflow engine's own bookkeeping models: triggering on them
        # is either circular (instances) or pointless (graph rows). Keyed on
        # the defining module, not the app label, since the engine now shares
        # the `automation` app with unrelated models (e.g. posture).
        if model.__module__ == "automation.workflows.models":
            continue
        for action in CUD_ACTIONS:
            keys.append(
                {
                    "key": make_event_key(model._meta.model_name, action),
                    "model": model._meta.model_name,
                    "action": action,
                }
            )
    return keys


def dispatch_internal_event(event_key, payload, folder_id, origin_depth=0):
    """Match triggers and start workflows. Returns started instances."""
    from .engine import EngineError, create_instance
    from .tasks import run_instance_task

    started = []
    triggers = WorkflowTrigger.objects.filter(
        type=WorkflowTrigger.Type.INTERNAL_EVENT,
        enabled=True,
        event_key=event_key,
        workflow__is_active=True,
    ).select_related("workflow")
    state_cache = {}
    for trigger in triggers:
        # Hard security boundary: the event's object must live within the
        # workflow's folder subtree, regardless of user filters. Events from
        # models that carry no folder count as root-scoped, so only workflows
        # whose scope includes the root folder may receive them — never a
        # bypass.
        effective_folder = (
            str(folder_id)
            if folder_id is not None
            else str(Folder.get_root_folder().id)
        )
        if effective_folder not in _workflow_scope(trigger.workflow):
            continue
        filters = (trigger.config or {}).get("filters") or {}
        if not _filters_match(filters, payload, state_cache):
            continue

        if origin_depth + 1 > MAX_TRIGGER_DEPTH:
            _bookkeep(trigger, WorkflowTrigger.Result.SKIPPED_DEPTH)
            logger.warning(
                "event trigger skipped: chain depth exceeded",
                trigger=str(trigger.id),
                event_key=event_key,
                origin_depth=origin_depth,
            )
            continue
        version = trigger.workflow.published_version
        entry = None
        if version is not None:
            entry = version.nodes.filter(
                type=WorkflowNode.Type.TRIGGER, ref=trigger.node_ref
            ).first()
        if version is None or entry is None:
            _bookkeep(trigger, WorkflowTrigger.Result.SKIPPED_UNPUBLISHED)
            continue
        if version.run_as is None:
            # No run identity, no automatic execution.
            _bookkeep(trigger, WorkflowTrigger.Result.SKIPPED_NO_IDENTITY)
            continue
        # One run per (trigger, user action, object): a save that writes
        # several LogEntries for one object is one run, while a bulk edit still
        # gets a run per object. Windowed, not unique-constrained: the cid can
        # come from an inbound x-correlation-id header, and a client reusing
        # one must not silence a trigger for good.
        cid = (payload or {}).get("cid") or ""
        try:
            with transaction.atomic():
                if cid and _already_running(trigger, cid, payload):
                    _bookkeep(trigger, WorkflowTrigger.Result.SKIPPED_COALESCED)
                    continue
                instance = create_instance(
                    version,
                    trigger=WorkflowInstance.Trigger.INTERNAL_EVENT,
                    payload=payload,
                    entry_node=entry,
                    trigger_registration=trigger,
                    trigger_depth=origin_depth + 1,
                    trigger_cid=cid,
                )
        except EngineError:
            _bookkeep(trigger, WorkflowTrigger.Result.ERROR)
            continue
        run_instance_task(str(instance.id))
        _bookkeep(trigger, WorkflowTrigger.Result.TRIGGERED, fired=True)
        started.append(instance)
    return started


def _already_running(trigger, cid, payload):
    """Locks the trigger row first: two dispatch workers must not both read
    "nothing started yet" for the same user action."""
    WorkflowTrigger.objects.select_for_update().filter(pk=trigger.pk).first()
    return trigger.instances.filter(
        trigger_cid=cid,
        payload__object_id=(payload or {}).get("object_id"),
        created_at__gte=timezone.now() - COALESCE_WINDOW,
    ).exists()


def _bookkeep(trigger, result, fired=False):
    from django.db.models import F

    updates = {"last_result": result, "last_triggered_at": timezone.now()}
    if fired:
        updates["trigger_count"] = F("trigger_count") + 1
    WorkflowTrigger.objects.filter(id=trigger.id).update(**updates)


def _workflow_scope(workflow):
    # String ids: additional_data serializes folder_id as str.
    from .actions import _read_scope_folder_ids

    return {str(fid) for fid in _read_scope_folder_ids(workflow.folder)}


# ---------- filter tree validation ----------


def validate_filter_tree(tree):
    """Shape-check a boolean filter tree. Raises ValueError on bad shape."""
    if tree in (None, {}):
        return
    _validate_group(tree, depth=0)


def _validate_group(group, depth):
    if depth > MAX_FILTER_DEPTH:
        raise ValueError("filter tree too deep")
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping")
    if group.get("operator", "and") not in ("and", "or", "not"):
        raise ValueError("invalid operator")
    conditions = group.get("conditions", [])
    children = group.get("children", [])
    if not isinstance(conditions, list) or not isinstance(children, list):
        raise ValueError("conditions and children must be lists")
    for condition in conditions:
        if (
            not isinstance(condition, dict)
            or not isinstance(condition.get("field"), str)
            or not condition.get("field")
            or condition.get("op", "eq") not in VALID_FILTER_OPS
            or not isinstance(condition.get("changed", False), bool)
        ):
            raise ValueError("invalid condition")
    for child in children:
        _validate_group(child, depth + 1)


def walk_conditions(group):
    yield from group.get("conditions", [])
    for child in group.get("children", []):
        yield from walk_conditions(child)


# ---------- filter tree evaluation ----------


def _filters_match(tree, payload, state_cache):
    if not tree or (not tree.get("conditions") and not tree.get("children")):
        return True
    return _evaluate_group(tree, payload, state_cache)


def _evaluate_group(group, payload, state_cache):
    results = [
        _evaluate_condition(condition, payload, state_cache)
        for condition in group.get("conditions", [])
    ]
    results += [
        _evaluate_group(child, payload, state_cache)
        for child in group.get("children", [])
    ]
    if not results:
        return True
    operator = group.get("operator", "and")
    if operator == "or":
        return any(results)
    if operator == "not":
        return not all(results)
    return all(results)


def _evaluate_condition(condition, payload, state_cache):
    field = condition.get("field", "")
    changes = payload.get("changes") or {}

    if condition.get("changed"):
        # Transition semantics: the field must have changed in THIS operation
        # and its new value must satisfy the condition.
        if field not in changes:
            return False
        return _compare(condition, changes[field][1])

    # State semantics: evaluate against the live object; deleted objects fall
    # back to the diff's old values.
    if payload.get("operation") == "deleted":
        if field in changes:
            return _compare(condition, changes[field][0])
        return False
    value = _current_value(field, payload, state_cache)
    if value is _MISSING:
        return False
    return _compare(condition, value)


_MISSING = object()


def _current_value(field, payload, state_cache):
    obj = _fetch_object(payload, state_cache)
    if obj is None:
        # Object gone or unfetchable: best effort via the diff's new values.
        new_values = payload.get("new_values") or {}
        return new_values.get(field, _MISSING)
    if field == "folder":
        return str(getattr(obj, "folder_id", "") or "")
    if field == "filtering_labels":
        if not hasattr(obj, "filtering_labels"):
            return _MISSING
        return list(obj.filtering_labels.values_list("label", flat=True))
    if not hasattr(obj, field):
        return _MISSING
    return getattr(obj, field)


def _fetch_object(payload, state_cache):
    key = (payload.get("model"), payload.get("object_id"))
    if key in state_cache:
        return state_cache[key]
    obj = None
    try:
        from django.contrib.contenttypes.models import ContentType

        # ContentType is only unique per (app_label, model); model-name-only
        # resolution picks an arbitrary app on a cross-app name collision.
        # The producer sends app_label; model-only stays as a fallback for
        # payloads predating it.
        lookup = {"model": payload.get("model")}
        if payload.get("app_label"):
            lookup["app_label"] = payload["app_label"]
        content_type = ContentType.objects.filter(**lookup).first()
        if content_type is not None:
            obj = (
                content_type.model_class()
                .objects.filter(pk=payload.get("object_id"))
                .first()
            )
    except Exception:  # noqa: BLE001 — matching must never break the producer
        obj = None
    state_cache[key] = obj
    return obj


def _compare(condition, runtime):
    op = condition.get("op", "eq")
    expected = condition.get("value")

    if op == "is_null":
        return runtime is None or runtime == ""
    if runtime is None:
        return False

    # Numeric comparison when both sides parse as numbers.
    if op in ("gt", "lt", "gte", "lte"):
        try:
            runtime_num, expected_num = float(runtime), float(expected)
        except TypeError, ValueError:
            return False
        return {
            "gt": runtime_num > expected_num,
            "lt": runtime_num < expected_num,
            "gte": runtime_num >= expected_num,
            "lte": runtime_num <= expected_num,
        }[op]

    if isinstance(runtime, list):
        # M2M subjects (filtering_labels): membership semantics.
        values = [str(item) for item in runtime]
        if op == "contains":
            return str(expected) in values
        if op == "not_in":
            return str(expected) not in values
        if op == "eq":
            return values == [str(expected)]
        return False

    runtime_str = str(runtime)
    if op == "eq":
        return runtime_str == str(expected)
    if op == "neq":
        return runtime_str != str(expected)
    if op == "in":
        return runtime_str in [part.strip() for part in str(expected).split(",")]
    if op == "not_in":
        return runtime_str not in [part.strip() for part in str(expected).split(",")]
    if op == "contains":
        return str(expected) in runtime_str
    return False


# ---------- CUD producer (auditlog mirror) ----------


def forward_log_entry(sender, instance, created, **kwargs):
    """post_save receiver on auditlog.LogEntry — see apps.ready()."""
    from auditlog.models import LogEntry
    from django.db import transaction

    if not created or instance.action == LogEntry.Action.ACCESS:
        return
    verb = _log_entry_verb(instance.action)
    if verb is None or instance.content_type_id is None:
        return
    key = make_event_key(instance.content_type.model, verb)
    # Cheap indexed gate: one query per audited save, no enqueue when nothing
    # listens for this key.
    if not WorkflowTrigger.objects.filter(
        type=WorkflowTrigger.Type.INTERNAL_EVENT, enabled=True, event_key=key
    ).exists():
        return

    from .engine import current_trigger_depth
    from .tasks import dispatch_internal_event_task

    origin_depth = current_trigger_depth.get()
    log_entry_id = instance.pk
    transaction.on_commit(
        lambda: dispatch_internal_event_task(log_entry_id, origin_depth)
    )


def payload_from_log_entry(log_entry):
    changes = log_entry.changes_dict or {}
    additional = log_entry.additional_data or {}
    verb = _log_entry_verb(log_entry.action)
    return {
        "event_key": make_event_key(log_entry.content_type.model, verb),
        "model": log_entry.content_type.model,
        "app_label": log_entry.content_type.app_label,
        "operation": verb,
        "object_id": str(log_entry.object_pk),
        "object_repr": log_entry.object_repr,
        "changes": changes,
        "new_values": {field: diff[1] for field, diff in changes.items()},
        "cid": log_entry.cid or "",
        "folder_id": additional.get("folder_id"),
        "actor_email": getattr(log_entry.actor, "email", None),
        "timestamp": log_entry.timestamp.isoformat() if log_entry.timestamp else None,
    }
