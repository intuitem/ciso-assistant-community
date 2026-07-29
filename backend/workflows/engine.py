"""Token-based execution engine (spec §7).

Advancement is synchronous inside the triggering request, guarded by a
row lock on the instance (PG) / SQLite's writer lock, with a max-steps
guard against runaway action loops. Task and event nodes park their token
as `waiting`; everything else executes and advances in the same call.
"""

import contextvars
import re

from django.db import transaction

from .actions import ActionError, _render_context, dig, execute_action, render
from .models import (
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowNode,
    WorkflowToken,
)

# Loops multiply node visits (100 items x body size), so the runaway guard
# sits far above any legitimate run.
MAX_STEPS = 5000

# Event-chain depth of the workflow run currently executing in this context;
# 0 means "not inside a run" (user/API-caused changes). Read by the
# internal-event producer (workflows/events.py).
current_trigger_depth = contextvars.ContextVar("workflow_trigger_depth", default=0)


class EngineError(Exception):
    """Raised with a deliberate, user-facing message (never internals or
    stack traces); user_message is what API responses may expose."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def start_instance(
    version,
    *,
    trigger="manual",
    payload=None,
    initiated_by=None,
    parent_instance=None,
    parent_token=None,
    entry_node=None,
):
    """Create an instance and run it synchronously (tests, subprocesses)."""
    instance = create_instance(
        version,
        trigger=trigger,
        payload=payload,
        initiated_by=initiated_by,
        parent_instance=parent_instance,
        parent_token=parent_token,
        entry_node=entry_node,
    )
    run_instance(instance)
    instance.refresh_from_db()
    return instance


def trigger_instance(
    version,
    *,
    trigger="manual",
    payload=None,
    initiated_by=None,
    entry_node=None,
    trigger_registration=None,
):
    """Entry point for webhook/manual triggers: honors the async setting."""
    from django.conf import settings

    instance = create_instance(
        version,
        trigger=trigger,
        payload=payload,
        initiated_by=initiated_by,
        entry_node=entry_node,
        trigger_registration=trigger_registration,
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


def default_entry_node(version):
    """Entry resolution when the caller names no trigger node: the manual
    trigger when there is exactly one, else the sole trigger node. Used by
    manual runs without an explicit choice and by subprocess starts (the
    child version resolves its own entry)."""
    trigger_nodes = list(version.nodes.filter(type=WorkflowNode.Type.TRIGGER))
    if not trigger_nodes:
        raise EngineError("This version has no trigger node")
    manual = [
        n
        for n in trigger_nodes
        if (n.trigger_config or {}).get("type") == WorkflowNode.TriggerType.MANUAL
    ]
    if len(manual) == 1:
        return manual[0]
    if len(trigger_nodes) == 1:
        return trigger_nodes[0]
    raise EngineError("Ambiguous entry: this version has several trigger nodes")


def create_instance(
    version,
    *,
    trigger="manual",
    payload=None,
    initiated_by=None,
    parent_instance=None,
    parent_token=None,
    trigger_registration=None,
    trigger_depth=0,
    entry_node=None,
):
    if entry_node is None:
        entry_node = default_entry_node(version)

    payload = payload or {}
    variables = {v.key: v.default_value for v in version.variables.all()}
    for variable_key, path in (entry_node.input_mapping or {}).items():
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
            trigger_registration=trigger_registration,
            trigger_depth=trigger_depth,
        )
        _log(
            instance,
            WorkflowInstanceLog.EventType.INSTANCE_STARTED,
            node=entry_node,
            message=f"Triggered by {trigger}",
            data={"variables": variables},
        )
        WorkflowToken.objects.create(instance=instance, current_node=entry_node)
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


def _set_iteration_overlay(token):
    """Expose the token's innermost iteration context to _render_context
    (spec D29). Execution is single-token-at-a-time inside a run, so the
    transient instance attribute is safe."""
    stack = token.iteration_context or []
    token.instance._iteration_context = dict(stack[-1]) if stack else None


def _process(token):
    node = token.current_node
    instance = token.instance
    _log(instance, WorkflowInstanceLog.EventType.NODE_ENTERED, node=node)
    _set_iteration_overlay(token)

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
            config = node.action_config or {}
            output = execute_action(node, instance) or {}
            _store_node_output(node, output, instance)
            _apply_output_mapping(node, output, instance)
            if config.get("for_each"):
                # One summary entry, not one per item (spec D27); per-item
                # detail lives in node_outputs.
                failed = len(output.get("errors") or [])
                message = f"{config.get('type', '')}: processed {output.get('count', 0)} items"
                if failed:
                    message += f" · {failed} failed"
            else:
                message = config.get("type", "")
            _log(
                instance,
                WorkflowInstanceLog.EventType.ACTION_EXECUTED,
                node=node,
                message=message,
                data=_truncate_log_data(output),
            )

        if node.type == WorkflowNode.Type.SUBPROCESS:
            _start_subprocess(token)
            if token.status == WorkflowToken.Status.WAITING:
                return

        if node.type == WorkflowNode.Type.LOOP:
            _process_loop(token)
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
        controller = token.loop_controller
        if controller is not None:
            controller.instance = token.instance
        if (
            controller is not None
            and controller.status == WorkflowToken.Status.WAITING
            and (controller.current_node.loop_config or {}).get(
                "on_item_error", "continue"
            )
            == "continue"
        ):
            # continue policy (spec D29): the iteration is recorded as failed
            # and the loop moves on instead of stalling the run.
            _log(
                token.instance,
                WorkflowInstanceLog.EventType.ERROR,
                node=node,
                message=f"{message} — loop continues with the next item",
            )
            token.status = WorkflowToken.Status.COMPLETED
            token.error_message = message
            token.save(update_fields=["status", "error_message", "updated_at"])
            _loop_body_returned(controller, failed=message)
            return
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


LOOP_MAX_ITEMS = 100
LOOP_TEMPLATE_RE = re.compile(r"^\{\{\s*([\w.]+)\s*\}\}$")


def _loop_each_edges(node):
    return [e for e in node.outgoing_edges.all() if e.source_port == "each"]


def _process_loop(token):
    """Loop node (spec D29). The first token to arrive becomes the CONTROLLER:
    it parks WAITING holding {items, index, outstanding, results, errors} and
    emits body tokens through the `each` port. Body tokens return to the loop
    input; the last return of an iteration collects and advances. Exhausted →
    the controller stores the loop output and releases through `done`."""
    node = token.current_node
    instance = token.instance

    controller = token.loop_controller
    if controller is not None and controller.current_node_id == node.id:
        # A body token coming home. Pin the controller to the run's shared
        # instance object: a lazily-loaded FK copy would carry stale
        # node_outputs and clobber sibling writes on save.
        controller.instance = instance
        token.status = WorkflowToken.Status.COMPLETED
        token.save(update_fields=["status", "updated_at"])
        _loop_body_returned(controller, failed=None)
        return

    # Fresh arrival: this token becomes the controller.
    config = node.loop_config or {}
    expression = config.get("collection") or ""
    match = (
        LOOP_TEMPLATE_RE.match(expression) if isinstance(expression, str) else None
    )
    if match is None:
        raise ActionError("loop: collection must be a single {{path}} expression")
    _set_iteration_overlay(token)
    items = dig(_render_context(instance), match.group(1))
    if items is None:
        items = []
    if not isinstance(items, list):
        raise ActionError(
            f"loop: '{expression}' did not resolve to a list "
            f"(got {type(items).__name__})"
        )
    if len(items) > LOOP_MAX_ITEMS:
        raise ActionError(f"loop: {len(items)} items exceeds the {LOOP_MAX_ITEMS} cap")

    token.status = WorkflowToken.Status.WAITING
    token.loop_state = {
        "items": items,
        "index": -1,
        "outstanding": 0,
        "results": [],
        "errors": [],
    }
    token.save(update_fields=["status", "loop_state", "updated_at"])
    _loop_next_iteration(token)


def _loop_next_iteration(controller):
    node = controller.current_node
    instance = controller.instance
    state = controller.loop_state
    state["index"] += 1

    if state["index"] >= len(state["items"]):
        _loop_finish(controller)
        return

    each_edges = _loop_each_edges(node)
    if not each_edges:
        raise ActionError("loop: no edge leaves the 'each' port")
    item = state["items"][state["index"]]
    state["outstanding"] = len(each_edges)
    controller.loop_state = state
    controller.save(update_fields=["loop_state", "updated_at"])
    stack = list(controller.iteration_context or []) + [
        {"item": item, "index": state["index"]}
    ]
    for edge in each_edges:
        _arrive(instance, edge, iteration_context=stack, loop_controller=controller)


def _loop_body_returned(controller, failed):
    state = controller.loop_state
    if failed:
        state["errors"].append({"index": state["index"], "message": failed})
    state["outstanding"] -= 1
    controller.loop_state = state
    controller.save(update_fields=["loop_state", "updated_at"])
    if state["outstanding"] > 0:
        return

    # Iteration complete: collect (unless it failed), then advance.
    iteration_failed = any(
        e["index"] == state["index"] for e in state["errors"]
    )
    collect = (controller.current_node.loop_config or {}).get("collect")
    if collect and not iteration_failed:
        overlay = {
            "item": state["items"][state["index"]],
            "index": state["index"],
        }
        controller.instance._iteration_context = overlay
        state["results"].append(render(collect, _render_context(controller.instance)))
        controller.instance._iteration_context = None
        controller.loop_state = state
        controller.save(update_fields=["loop_state", "updated_at"])
    _loop_next_iteration(controller)


def _loop_finish(controller):
    node = controller.current_node
    instance = controller.instance
    state = controller.loop_state
    output = {
        "count": len(state["items"]),
        "results": state["results"],
        "errors": state["errors"],
    }
    _store_node_output(node, output, instance)
    _apply_output_mapping(node, output, instance)
    failed = len(state["errors"])
    message = f"processed {output['count']} items"
    if failed:
        message += f" · {failed} failed"
    _log(
        instance,
        WorkflowInstanceLog.EventType.LOOP_COMPLETED,
        node=node,
        message=message,
        data=_truncate_log_data(output),
    )
    controller.loop_state = {}
    controller.save(update_fields=["loop_state", "updated_at"])
    _advance(controller)


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
    """Persist the node's output for {{nodes.<ref>.<path>}} references and the
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

    if node.type == WorkflowNode.Type.CONDITION:
        # Exclusive routing by branch (spec D25): evaluate branches in order,
        # default last (always matches), first match wins; follow its wire.
        chosen = []
        branches = sorted(node.branches.all(), key=lambda b: (b.is_default, b.order))
        for branch in branches:
            if _evaluate_branch(branch, _render_context(instance)):
                edge = branch.edges.first()
                if edge is None:
                    raise EngineError(
                        f"Branch '{branch}' of '{node}' matched but has no wire"
                    )
                chosen = [edge]
                break
        if not chosen:
            raise EngineError(f"No branch of '{node}' matched")
    elif node.type == WorkflowNode.Type.LOOP:
        # Controller release: each-port edges are controller-managed; done
        # fires every wire (n8n semantics).
        chosen = [e for e in edges if e.source_port == "done"]
        if not chosen:
            raise EngineError(f"Loop '{node}' has no edge on its 'done' port")
    else:
        # Fan-out is always parallel (n8n semantics): every wired output runs.
        # Exclusive routing is the condition node's job.
        chosen = edges

    token.status = WorkflowToken.Status.CONSUMED
    token.save(update_fields=["status", "updated_at"])
    for edge in chosen:
        _arrive(
            instance,
            edge,
            iteration_context=token.iteration_context,
            loop_controller=token.loop_controller,
        )


def _arrive(instance, edge, iteration_context=None, loop_controller=None):
    # Tokens are per-hop rows: iteration context and the controller pointer
    # travel with the moving token (spec D29).
    context = {
        "iteration_context": iteration_context or [],
        "loop_controller": loop_controller,
    }
    target = edge.target_node
    if target.join_type == WorkflowNode.JoinType.NONE:
        WorkflowToken.objects.create(
            instance=instance, current_node=target, arrived_via_edge=edge, **context
        )
        return

    WorkflowToken.objects.create(
        instance=instance,
        current_node=target,
        arrived_via_edge=edge,
        status=WorkflowToken.Status.WAITING,
        **context,
    )
    _log(instance, WorkflowInstanceLog.EventType.JOIN_ARRIVAL, node=target, edge=edge)
    incoming_count = target.incoming_edges.count()
    waiting = instance.tokens.filter(
        status=WorkflowToken.Status.WAITING, current_node=target
    )

    arrived_edges = set(waiting.values_list("arrived_via_edge_id", flat=True))
    if len(arrived_edges) < incoming_count:
        return

    sample = waiting.first()
    waiting.update(status=WorkflowToken.Status.CONSUMED)
    _log(instance, WorkflowInstanceLog.EventType.JOIN_FIRED, node=target)
    WorkflowToken.objects.create(
        instance=instance,
        current_node=target,
        iteration_context=(sample.iteration_context or []) if sample else [],
        loop_controller=sample.loop_controller if sample else None,
    )


def _evaluate_branch(branch, variables):
    root_groups = [
        g for g in branch.condition_groups.all() if g.parent_group_id is None
    ]
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
    # The compared value may itself be a template ({{item.severity}}, spec D29).
    expected = _coerce(render(condition.value, variables), condition.variable.type)
    op = condition.op

    if op == "is_null":
        return runtime is None
    if runtime is None:
        return False
    if condition.variable.type == "number":
        try:
            runtime = float(runtime)
        except TypeError, ValueError:
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
        except TypeError, ValueError:
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
