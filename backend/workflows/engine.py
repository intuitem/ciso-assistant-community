"""Token-based execution engine (spec §7).

Advancement is synchronous inside the triggering request, guarded by a
row lock on the instance (PG) / SQLite's writer lock, with a max-steps
guard against runaway action loops. Task and event nodes park their token
as `waiting`; everything else executes and advances in the same call.
"""

import contextvars
import math

from django.db import transaction

from .actions import ActionError, dig, execute_action
from .models import (
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowNode,
    WorkflowToken,
)

MAX_STEPS = 300

# Event-chain depth of the workflow run currently executing in this context;
# 0 means "not inside a run" (user/API-caused changes). Read by the
# internal-event producer (workflows/events.py).
current_trigger_depth = contextvars.ContextVar("workflow_trigger_depth", default=0)


class EngineError(Exception):
    pass


def start_instance(
    version,
    *,
    trigger="manual",
    payload=None,
    initiated_by=None,
    parent_instance=None,
    parent_token=None,
):
    """Create an instance and run it synchronously (tests, subprocesses)."""
    instance = create_instance(
        version,
        trigger=trigger,
        payload=payload,
        initiated_by=initiated_by,
        parent_instance=parent_instance,
        parent_token=parent_token,
    )
    run_instance(instance)
    instance.refresh_from_db()
    return instance


def trigger_instance(version, *, trigger="manual", payload=None, initiated_by=None):
    """Entry point for webhook/manual triggers: honors the async setting."""
    from django.conf import settings

    instance = create_instance(
        version, trigger=trigger, payload=payload, initiated_by=initiated_by
    )
    if getattr(settings, "WORKFLOWS_ASYNC_EXECUTION", False):
        from .tasks import run_instance_task

        run_instance_task(str(instance.id))
    else:
        run_instance(instance)
    instance.refresh_from_db()
    return instance


def run_instance(instance):
    # Expose this run's event-chain depth so changes its actions make can be
    # attributed by the internal-event producer (spec D21 loop containment).
    depth_token = current_trigger_depth.set(instance.trigger_depth)
    try:
        with transaction.atomic():
            locked = (
                WorkflowInstance.objects.select_for_update()
                .select_related("version")
                .get(id=instance.id)
            )
            _run(locked)
    finally:
        current_trigger_depth.reset(depth_token)


def create_instance(
    version,
    *,
    trigger="manual",
    payload=None,
    initiated_by=None,
    parent_instance=None,
    parent_token=None,
    schedule=None,
    event_trigger=None,
    trigger_depth=0,
):
    start_node = version.nodes.filter(type=WorkflowNode.Type.START).first()
    if start_node is None:
        raise EngineError("This version has no start node")

    payload = payload or {}
    variables = {v.key: v.default_value for v in version.variables.all()}
    for variable_key, path in (start_node.input_mapping or {}).items():
        value = dig(payload, path)
        if value is not None:
            variables[variable_key] = value
    if payload:
        variables["payload"] = payload

    with transaction.atomic():
        instance = WorkflowInstance.objects.create(
            workflow=version.workflow,
            version=version,
            # Explicit: FolderMixin defaults folder to root, so the save()-time
            # "inherit if unset" guard never fires on its own.
            folder=version.folder,
            trigger=trigger,
            variables=variables,
            payload=payload,
            initiated_by=initiated_by,
            parent_instance=parent_instance,
            parent_token=parent_token,
            schedule=schedule,
            event_trigger=event_trigger,
            trigger_depth=trigger_depth,
        )
        _log(
            instance,
            WorkflowInstanceLog.EventType.INSTANCE_STARTED,
            node=start_node,
            message=f"Triggered by {trigger}",
            data={"variables": variables},
        )
        WorkflowToken.objects.create(instance=instance, current_node=start_node)
    return instance


def resume_token(token):
    """Wake a waiting token (event received, subprocess finished, ...)."""
    with transaction.atomic():
        instance = WorkflowInstance.objects.select_for_update().get(
            id=token.instance_id
        )
        token.status = WorkflowToken.Status.ACTIVE
        token.save(update_fields=["status", "updated_at"])
        _advance(token)
        _run(instance)


def broadcast_event(event_key, emitting_instance):
    """Wake every waiting event token matching the key in the same folder."""
    waiting = list(
        WorkflowToken.objects.filter(
            status=WorkflowToken.Status.WAITING,
            current_node__type=WorkflowNode.Type.EVENT,
            current_node__event_key=event_key,
            instance__status=WorkflowInstance.Status.ACTIVE,
            instance__folder=emitting_instance.folder,
        ).exclude(instance=emitting_instance)
    )
    for token in waiting:
        _log(
            token.instance,
            WorkflowInstanceLog.EventType.EVENT_RECEIVED,
            node=token.current_node,
            message=f"Event '{event_key}' received",
        )
        resume_token(token)
    return len(waiting)


def _run(instance):
    for _ in range(MAX_STEPS):
        token = instance.tokens.filter(status=WorkflowToken.Status.ACTIVE).first()
        if token is None:
            break
        _process(token)
    else:
        _fail_instance(instance, "Max execution steps exceeded")
        return
    _refresh_status(instance)


def _process(token):
    node = token.current_node
    instance = token.instance
    _log(instance, WorkflowInstanceLog.EventType.NODE_ENTERED, node=node)

    try:
        if node.type == WorkflowNode.Type.END:
            token.status = WorkflowToken.Status.COMPLETED
            token.save(update_fields=["status", "updated_at"])
            return

        if node.type == WorkflowNode.Type.TASK:
            # Human-task materialization (TaskNode integration) is the next
            # milestone; until then the run parks here, visible in the log.
            token.status = WorkflowToken.Status.WAITING
            token.save(update_fields=["status", "updated_at"])
            _log(
                instance,
                WorkflowInstanceLog.EventType.TASK_WAITING,
                node=node,
                message=f"Waiting on task '{node.label}'",
            )
            return

        if node.type == WorkflowNode.Type.EVENT:
            token.status = WorkflowToken.Status.WAITING
            token.save(update_fields=["status", "updated_at"])
            _log(
                instance,
                WorkflowInstanceLog.EventType.EVENT_WAITING,
                node=node,
                message=f"Waiting for event '{node.event_key}'",
            )
            return

        if node.type == WorkflowNode.Type.ACTION:
            output = execute_action(node, instance) or {}
            _store_node_output(node, output, instance)
            _apply_output_mapping(node, output, instance)
            _log(
                instance,
                WorkflowInstanceLog.EventType.ACTION_EXECUTED,
                node=node,
                message=(node.action_config or {}).get("type", ""),
                data=_truncate_log_data(output),
            )

        if node.type == WorkflowNode.Type.SUBPROCESS:
            _start_subprocess(token)
            if token.status == WorkflowToken.Status.WAITING:
                return

        _advance(token)
    except (ActionError, EngineError) as e:
        _handle_failure(token, str(e))
    except Exception as e:  # noqa: BLE001 — a buggy action must not 500 the request
        _handle_failure(token, f"{type(e).__name__}: {e}")


def _handle_failure(token, message):
    """Retry policy (spec D10/D17): schedule a delayed Huey re-execution while
    attempts remain on action/subprocess nodes, else park the token in error."""
    node = token.current_node
    retryable = node.type in (
        WorkflowNode.Type.ACTION,
        WorkflowNode.Type.SUBPROCESS,
    )
    if not retryable or token.retry_count >= node.retry_max_attempts:
        _fail_token(token, message)
        return

    token.retry_count += 1
    token.status = WorkflowToken.Status.RETRYING
    token.error_message = message
    token.save(update_fields=["retry_count", "status", "error_message", "updated_at"])
    delay = node.retry_delay_seconds
    if node.retry_backoff == WorkflowNode.RetryBackoff.EXPONENTIAL:
        delay *= 2 ** (token.retry_count - 1)
    _log(
        token.instance,
        WorkflowInstanceLog.EventType.ERROR,
        node=node,
        message=(
            f"{message} — retry {token.retry_count}/{node.retry_max_attempts} "
            f"in {delay}s"
        ),
    )
    from .tasks import retry_token_task

    retry_token_task.schedule(args=(str(token.id),), delay=delay)


def _start_subprocess(token):
    node = token.current_node
    instance = token.instance
    target = node.subprocess_workflow
    version = target.published_version if target else None
    if version is None:
        raise EngineError("Subprocess workflow has no published version")
    child_payload = {
        child_key: dig(instance.variables, parent_path)
        for child_key, parent_path in (node.input_mapping or {}).items()
    }
    _log(
        instance,
        WorkflowInstanceLog.EventType.SUBPROCESS_STARTED,
        node=node,
        message=target.name,
    )
    child = start_instance(
        version,
        trigger="subprocess",
        payload=child_payload,
        parent_instance=instance,
        parent_token=token,
    )
    if child.status == WorkflowInstance.Status.COMPLETED:
        _store_node_output(node, child.variables, instance)
        _apply_output_mapping(node, child.variables, instance)
    elif child.status == WorkflowInstance.Status.ACTIVE:
        token.status = WorkflowToken.Status.WAITING
        token.save(update_fields=["status", "updated_at"])
    else:
        raise EngineError(f"Subprocess failed ({child})")


def _store_node_output(node, output, instance):
    """Persist the node's output for {{node.<ref>.<path>}} references and the
    builder's reference-run data browser (spec D20). Structure-preserving:
    nested JSON stays navigable and referenceable; only oversized leaves and
    collections shrink. The display log truncates flat and harder."""
    key = node.ref or str(node.id)
    instance.node_outputs[key] = _cap_structure(output)
    instance.save(update_fields=["node_outputs", "updated_at"])


MAX_LEAF_CHARS = 1000
MAX_COLLECTION_ITEMS = 100
MAX_STRUCTURE_DEPTH = 10


def _cap_structure(value, budget=None, depth=0):
    """Bound node_outputs without flattening: dicts and lists keep their shape
    (so paths into them keep working), long strings truncate, huge collections
    tail-omit, and a global character budget backstops pathological payloads."""
    if budget is None:
        budget = [32000]
    if budget[0] <= 0:
        return "<truncated: output budget exceeded>"
    if depth > MAX_STRUCTURE_DEPTH:
        return "<truncated: max depth>"

    if isinstance(value, str):
        if len(value) > MAX_LEAF_CHARS:
            budget[0] -= MAX_LEAF_CHARS
            return f"{value[:MAX_LEAF_CHARS]}… <{len(value)} chars truncated>"
        budget[0] -= len(value)
        return value

    if isinstance(value, dict):
        capped = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= MAX_COLLECTION_ITEMS or budget[0] <= 0:
                capped["<omitted>"] = f"{len(value) - index} more keys"
                break
            budget[0] -= len(str(key))
            capped[key] = _cap_structure(item, budget, depth + 1)
        return capped

    if isinstance(value, list):
        capped_items = []
        for index, item in enumerate(value):
            if index >= MAX_COLLECTION_ITEMS or budget[0] <= 0:
                capped_items.append(f"<{len(value) - index} more items>")
                break
            capped_items.append(_cap_structure(item, budget, depth + 1))
        return capped_items

    budget[0] -= 8
    return value


def _apply_output_mapping(node, output, instance):
    mapping = node.output_mapping or {}
    if not mapping:
        return
    updates = {}
    for variable_key, path in mapping.items():
        value = dig(output, path)
        if value is not None:
            updates[variable_key] = value
    if updates:
        instance.variables.update(updates)
        instance.save(update_fields=["variables", "updated_at"])


def _advance(token):
    node = token.current_node
    instance = token.instance
    edges = list(node.outgoing_edges.all())
    if not edges:
        raise EngineError(f"Node '{node}' has no outgoing edge")

    if node.fork_type == WorkflowNode.ForkType.PARALLEL:
        chosen = edges
    else:
        chosen = []
        for edge in sorted(edges, key=lambda e: e.priority):
            if _evaluate_edge(edge, instance.variables):
                chosen = [edge]
                break
        if not chosen:
            raise EngineError(f"No outgoing edge of '{node}' matched")

    token.status = WorkflowToken.Status.CONSUMED
    token.save(update_fields=["status", "updated_at"])
    for edge in chosen:
        _arrive(instance, edge)


def _arrive(instance, edge):
    target = edge.target_node
    if target.join_type == WorkflowNode.JoinType.NONE:
        WorkflowToken.objects.create(
            instance=instance, current_node=target, arrived_via_edge=edge
        )
        return

    WorkflowToken.objects.create(
        instance=instance,
        current_node=target,
        arrived_via_edge=edge,
        status=WorkflowToken.Status.WAITING,
    )
    _log(instance, WorkflowInstanceLog.EventType.JOIN_ARRIVAL, node=target, edge=edge)
    incoming_count = target.incoming_edges.count()
    waiting = instance.tokens.filter(
        status=WorkflowToken.Status.WAITING, current_node=target
    )

    if target.join_type == WorkflowNode.JoinType.AND:
        arrived_edges = set(waiting.values_list("arrived_via_edge_id", flat=True))
        if len(arrived_edges) < incoming_count:
            return
    else:  # OR: fire once per activation, consume the stragglers
        arrivals = instance.logs.filter(
            event_type=WorkflowInstanceLog.EventType.JOIN_ARRIVAL, node=target
        ).count()
        fired = instance.logs.filter(
            event_type=WorkflowInstanceLog.EventType.JOIN_FIRED, node=target
        ).count()
        if fired >= math.ceil(arrivals / incoming_count):
            waiting.update(status=WorkflowToken.Status.CONSUMED)
            return

    waiting.update(status=WorkflowToken.Status.CONSUMED)
    _log(instance, WorkflowInstanceLog.EventType.JOIN_FIRED, node=target)
    WorkflowToken.objects.create(instance=instance, current_node=target)


def _evaluate_edge(edge, variables):
    root_groups = [g for g in edge.condition_groups.all() if g.parent_group_id is None]
    if not root_groups:
        return True
    return all(_evaluate_group(group, variables) for group in root_groups)


def _evaluate_group(group, variables):
    results = [
        _evaluate_condition(condition, variables)
        for condition in group.conditions.all()
    ]
    results += [_evaluate_group(child, variables) for child in group.children.all()]
    if not results:
        return True
    if group.operator == "or":
        return any(results)
    if group.operator == "not":
        return not all(results)
    return all(results)


def _evaluate_condition(condition, variables):
    runtime = variables.get(condition.variable.key)
    expected = _coerce(condition.value, condition.variable.type)
    op = condition.op

    if op == "is_null":
        return runtime is None
    if runtime is None:
        return False
    if condition.variable.type == "number":
        try:
            runtime = float(runtime)
        except (TypeError, ValueError):
            return False
    if op == "eq":
        return runtime == expected
    if op == "neq":
        return runtime != expected
    if op in ("gt", "lt", "gte", "lte"):
        try:
            return {
                "gt": runtime > expected,
                "lt": runtime < expected,
                "gte": runtime >= expected,
                "lte": runtime <= expected,
            }[op]
        except TypeError:
            return False
    if op == "in":
        return str(runtime) in [
            part.strip() for part in str(condition.value).split(",")
        ]
    if op == "not_in":
        return str(runtime) not in [
            part.strip() for part in str(condition.value).split(",")
        ]
    if op == "contains":
        return str(condition.value) in str(runtime)
    return False


def _coerce(value, variable_type):
    if variable_type == "number":
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    if variable_type == "boolean":
        return str(value).strip().lower() in ("true", "1", "yes")
    return value


def _fail_token(token, message):
    token.status = WorkflowToken.Status.ERROR
    token.error_message = message
    token.save(update_fields=["status", "error_message", "updated_at"])
    _log(
        token.instance,
        WorkflowInstanceLog.EventType.ERROR,
        node=token.current_node,
        message=message,
    )


def _fail_instance(instance, message):
    _log(instance, WorkflowInstanceLog.EventType.ERROR, message=message)
    instance.status = WorkflowInstance.Status.FAILED
    instance.save(update_fields=["status", "updated_at"])


def _refresh_status(instance):
    statuses = set(instance.tokens.values_list("status", flat=True))
    if statuses & {
        WorkflowToken.Status.ACTIVE,
        WorkflowToken.Status.WAITING,
        WorkflowToken.Status.RETRYING,
    }:
        return
    if WorkflowToken.Status.ERROR in statuses:
        instance.status = WorkflowInstance.Status.FAILED
    else:
        instance.status = WorkflowInstance.Status.COMPLETED
        _log(instance, WorkflowInstanceLog.EventType.INSTANCE_COMPLETED)
    instance.save(update_fields=["status", "updated_at"])

    # A finished subprocess hands control back to its parent.
    if (
        instance.parent_token_id
        and instance.status == WorkflowInstance.Status.COMPLETED
    ):
        parent_token = instance.parent_token
        if parent_token and parent_token.status == WorkflowToken.Status.WAITING:
            _apply_output_mapping(
                parent_token.current_node, instance.variables, parent_token.instance
            )
            resume_token(parent_token)


def _truncate_log_data(output, limit=2000):
    """Keep the instance log lean: large action outputs (HTTP bodies) are
    previewed, not stored verbatim. output_mapping already ran on the full
    value, so nothing functional is lost."""
    import json

    truncated = {}
    for key, value in output.items():
        serialized = value if isinstance(value, str) else json.dumps(value, default=str)
        if len(serialized) > limit:
            truncated[key] = (
                f"{serialized[:limit]}… <{len(serialized)} chars truncated>"
            )
        else:
            truncated[key] = value
    return truncated


def _log(instance, event_type, node=None, edge=None, message="", data=None):
    WorkflowInstanceLog.objects.create(
        instance=instance,
        node=node,
        edge=edge,
        event_type=event_type,
        message=message,
        data=data or {},
    )
