"""Token-based execution engine (spec §7).

Advancement is synchronous inside the triggering request, guarded by a
row lock on the instance (PG) / SQLite's writer lock, with a max-steps
guard against runaway action loops. Task and event nodes park their token
as `waiting`; everything else executes and advances in the same call.
"""

import contextvars
import re
from collections.abc import Callable
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from .actions import (
    ActionError,
    DeferredTask,
    FatalActionError,
    _read_scope_folder_ids,
    _render_context,
    dig,
    execute_action,
    render,
)
from .context import temporal_seeds
from .models import (
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowNode,
    WorkflowToken,
    WorkflowVariable,
    WorkflowVersion,
)

# Loops multiply node visits (100 items x body size), so the runaway guard
# sits far above any legitimate run.
MAX_STEPS = 5000

# Subprocess calls recurse synchronously (a nested run_instance per level), so
# a subprocess cycle would blow the Python stack / exhaust DB connections. Cap
# nesting depth; publish validation catches direct self-reference, this catches
# cross-workflow cycles that can't be detected statically.
MAX_SUBPROCESS_DEPTH = 10

# Token states that still represent work in progress: what a run has to have
# none of to be finished, and what terminating a run has to consume.
LIVE_TOKEN_STATUSES = [
    WorkflowToken.Status.ACTIVE,
    WorkflowToken.Status.WAITING,
    WorkflowToken.Status.RETRYING,
]

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
    trigger_depth=0,
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
        trigger_depth=trigger_depth,
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
    initial_variables=None,
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
        initial_variables=initial_variables,
    )
    if getattr(settings, "WORKFLOWS_ASYNC_EXECUTION", False):
        from .tasks import run_instance_task

        run_instance_task(str(instance.id))
    else:
        run_instance(instance)
    instance.refresh_from_db()
    return instance


def _lock_instance_tree(instance_id):
    """Lock an instance row after locking its ancestors, root first.

    Two flows cross instance boundaries in opposite directions: a finishing
    child hands control back to its parent (child lock held, parent lock
    acquired in _refresh_status), while a terminating/timing-out parent
    abandons its children (parent lock held, child rows updated). Acquiring
    the same two rows in opposite orders deadlocks on PostgreSQL. Locking
    top-down from the root ancestor at every transaction entry point makes
    all acquisition follow one tree order, so no cycle can form; the price
    is that runs within one subprocess tree serialize, which matches the
    engine's single-token-at-a-time model anyway. The parent chain is set at
    creation and never changes, so walking it unlocked is safe.
    """
    chain = [instance_id]
    while len(chain) <= MAX_SUBPROCESS_DEPTH + 2:
        parent_id = (
            WorkflowInstance.objects.filter(id=chain[-1])
            .values_list("parent_token__instance_id", flat=True)
            .first()
        )
        if parent_id is None:
            break
        chain.append(parent_id)
    locked = None
    for ancestor_id in reversed(chain):
        locked = (
            WorkflowInstance.objects.select_for_update()
            .select_related("version")
            .get(id=ancestor_id)
        )
    return locked


def run_instance(instance):
    # Expose this run's event-chain depth so changes its actions make can be
    # attributed by the internal-event producer (loop containment).
    depth_token = current_trigger_depth.set(instance.trigger_depth)
    try:
        with transaction.atomic():
            _run(_lock_instance_tree(instance.id))
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


def run_identity(instance):
    """The identity a run acts as: the version's run_as (definer
    rights, stamped at publish), or the invoker for drafts — run_as only
    exists after publish and drafts are manual-only. Returns None when no
    live identity resolves (fail closed at the caller). Memoized per
    in-memory instance so retry/resume paths share one resolution."""
    if not hasattr(instance, "_run_identity"):
        version = instance.version
        identity = version.run_as
        if identity is None and version.status == WorkflowVersion.Status.DRAFT:
            identity = instance.initiated_by
        if identity is not None and not identity.is_active:
            identity = None
        instance._run_identity = identity
    return instance._run_identity


def coerce_variable_value(value, variable_type):
    """Validate/coerce a user-supplied initial value against the declared
    variable type. Raises ValueError on mismatch. Dates stay ISO
    strings (variables live in a JSONField)."""
    if variable_type == WorkflowVariable.Type.STRING:
        if isinstance(value, str):
            return value
    elif variable_type == WorkflowVariable.Type.NUMBER:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return float(value)
    elif variable_type == WorkflowVariable.Type.BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
    elif variable_type == WorkflowVariable.Type.DATE:
        if isinstance(value, str):
            date.fromisoformat(value)
            return value
    elif variable_type == WorkflowVariable.Type.JSON:
        return value
    raise ValueError(f"not a valid {variable_type} value")


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
    initial_variables=None,
    trigger_cid="",
):
    if entry_node is None:
        entry_node = default_entry_node(version)

    payload = payload or {}
    variables = {v.key: v.default_value for v in version.variables.all()}
    for variable_key, path in (entry_node.input_mapping or {}).items():
        value = dig(payload, path)
        if value is not None:
            variables[variable_key] = value
    # Explicit debug seeds beat defaults and input mapping. The
    # caller (manual-run endpoint) validates keys and types beforehand.
    if initial_variables:
        variables.update(initial_variables)
    # Engine-owned last; these keys are reserved, so nothing authored is lost.
    variables.update(temporal_seeds(trigger_registration))
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
            trigger_cid=trigger_cid,
        )
        _log(
            instance,
            WorkflowInstanceLog.EventType.INSTANCE_STARTED,
            node=entry_node,
            message=f"Triggered by {trigger}",
            # seeded_variables keeps debugged runs distinguishable.
            data={
                "variables": variables,
                **(
                    {"seeded_variables": initial_variables} if initial_variables else {}
                ),
            },
        )
        WorkflowToken.objects.create(instance=instance, current_node=entry_node)
    return instance


def resume_token(token):
    """Wake a waiting token (event received, subprocess finished, ...)."""
    with transaction.atomic():
        instance = _lock_instance_tree(token.instance_id)
        # Re-read under the lock: broadcast_event lists waiters without one, so
        # two concurrent emits could both reach here for the same token. Only
        # the first (still WAITING) resume is allowed to advance it.
        token.refresh_from_db()
        if token.status != WorkflowToken.Status.WAITING:
            return
        token.status = WorkflowToken.Status.ACTIVE
        token.save(update_fields=["status", "updated_at"])
        _advance(token)
        _run(instance)


def claim_deferred_action(token_id: str, dispatch_id: str) -> WorkflowToken | None:
    """Exclusive claim on a parked token's dispatch, returning None when
    another delivery already took it. Same CAS pattern as retry_token_task:
    huey may deliver a task twice, and a read-then-act window would let both
    deliveries run the side effect. The token stays WAITING while in flight,
    so _run never picks it up mid-delivery."""
    claimed = WorkflowToken.objects.filter(
        id=token_id,
        status=WorkflowToken.Status.WAITING,
        dispatch_id=dispatch_id,
    ).update(dispatch_id=None)
    if not claimed:
        return None
    return WorkflowToken.objects.select_related("instance").get(id=token_id)


def _resume_deferred(
    token: WorkflowToken, on_resume: Callable[[WorkflowInstance], None]
) -> None:
    """Shared scaffolding for a deferred action's task handing its token
    back: run `on_resume` then the instance under the tree lock and the
    instance's trigger depth. The WAITING re-check makes duplicate task
    deliveries and operator interference no-ops."""
    depth_token = current_trigger_depth.set(token.instance.trigger_depth)
    try:
        with transaction.atomic():
            instance = _lock_instance_tree(token.instance_id)
            token.refresh_from_db()
            if token.status != WorkflowToken.Status.WAITING:
                return
            token.instance = instance
            on_resume(instance)
            _run(instance)
    finally:
        current_trigger_depth.reset(depth_token)


def complete_deferred_action(token: WorkflowToken, output: dict) -> None:
    """A deferred action's task reports success: persist the output, log the
    execution and advance."""

    def on_resume(instance):
        node = token.current_node
        _persist_node_output(node, output, instance)
        _log(
            instance,
            WorkflowInstanceLog.EventType.ACTION_EXECUTED,
            node=node,
            message=(node.action_config or {}).get("type", ""),
            data=_truncate_log_data(output),
        )
        _advance(token)

    _resume_deferred(token, on_resume)


def fail_deferred_action(token: WorkflowToken, message: str) -> None:
    """A deferred action's task reports failure: route through the node's
    retry policy exactly like a synchronous ActionError (mirrors the failed
    async-subprocess path in _refresh_status)."""

    def on_resume(instance):
        token.status = WorkflowToken.Status.ACTIVE
        token.save(update_fields=["status", "updated_at"])
        _handle_failure(token, message)

    _resume_deferred(token, on_resume)


def _reopen(instance):
    """A failed/abandoned instance goes back to ACTIVE so _run proceeds after
    an operator unsticks one of its tokens."""
    if instance.status != WorkflowInstance.Status.ACTIVE:
        instance.status = WorkflowInstance.Status.ACTIVE
        instance.save(update_fields=["status", "updated_at"])


def retry_token(token):
    """Operator recovery: re-run an errored token from its node."""
    with transaction.atomic():
        instance = _lock_instance_tree(token.instance_id)
        token.refresh_from_db()
        if token.status != WorkflowToken.Status.ERROR:
            raise EngineError("Only an errored token can be retried")
        token.instance = instance
        token.status = WorkflowToken.Status.ACTIVE
        token.retry_count = 0
        token.error_message = ""
        token.save(
            update_fields=["status", "retry_count", "error_message", "updated_at"]
        )
        _reopen(instance)
        _log(
            instance,
            WorkflowInstanceLog.EventType.ERROR,
            node=token.current_node,
            message="Token retried by operator",
        )
        _run(instance)


def skip_token(token):
    """Operator recovery: skip an errored node and advance past it."""
    with transaction.atomic():
        instance = _lock_instance_tree(token.instance_id)
        token.refresh_from_db()
        if token.status != WorkflowToken.Status.ERROR:
            raise EngineError("Only an errored token can be skipped")
        token.instance = instance
        token.status = WorkflowToken.Status.ACTIVE
        token.error_message = ""
        token.save(update_fields=["status", "error_message", "updated_at"])
        _reopen(instance)
        _log(
            instance,
            WorkflowInstanceLog.EventType.ERROR,
            node=token.current_node,
            message=f"Node '{token.current_node.label or token.current_node.type}' "
            "skipped by operator",
        )
        try:
            _advance(token)
        except EngineError:
            # A dead-end node (no wired successor) just ends this branch.
            token.status = WorkflowToken.Status.CONSUMED
            token.save(update_fields=["status", "updated_at"])
        _run(instance)


def abort_token(token):
    """Operator recovery: abandon the run. Consumes every live token
    and marks the instance ABANDONED (a manual terminal state)."""
    with transaction.atomic():
        instance = _lock_instance_tree(token.instance_id)
        instance.tokens.filter(
            status__in=[*LIVE_TOKEN_STATUSES, WorkflowToken.Status.ERROR]
        ).update(status=WorkflowToken.Status.CONSUMED)
        instance.status = WorkflowInstance.Status.ABANDONED
        instance.save(update_fields=["status", "updated_at"])
        _log(
            instance,
            WorkflowInstanceLog.EventType.ERROR,
            node=token.current_node,
            message="Run abandoned by operator",
        )


def broadcast_event(event_key, emitting_instance):
    """Wake every waiting event token matching the key within the emitting
    instance's folder SUBTREE (spec §7), not just its exact folder."""
    scope_ids = _read_scope_folder_ids(emitting_instance.folder)
    waiting = list(
        WorkflowToken.objects.filter(
            status=WorkflowToken.Status.WAITING,
            current_node__type=WorkflowNode.Type.EVENT,
            current_node__event_key=event_key,
            instance__status=WorkflowInstance.Status.ACTIVE,
            instance__folder_id__in=scope_ids,
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


def _is_over_ttl(instance):
    """Has the run exceeded its absolute time limit? Reads the
    frozen version copy; 0 = no limit."""
    timeout = instance.version.timeout_seconds
    return bool(timeout) and (
        timezone.now() - instance.created_at > timedelta(seconds=timeout)
    )


def _timeout_instance(instance):
    """Terminate an over-TTL run: mirror the max-steps branch — error live
    tokens, log RUN_TERMINATED (no TIMED_OUT status; reuse FAILED), cascade to
    subprocess children."""
    instance.tokens.filter(status__in=LIVE_TOKEN_STATUSES).update(
        status=WorkflowToken.Status.ERROR
    )
    _log(
        instance,
        WorkflowInstanceLog.EventType.RUN_TERMINATED,
        message=f"Run exceeded its {instance.version.timeout_seconds}s time limit",
    )
    instance.status = WorkflowInstance.Status.FAILED
    instance.save(update_fields=["status", "updated_at"])
    _abandon_children(instance)


def _run(instance):
    # A failed/completed instance must not resume (e.g. a duplicate task
    # enqueue after a max-steps failure would run another MAX_STEPS).
    if instance.status != WorkflowInstance.Status.ACTIVE:
        return
    # A run resuming after a long park (event/subprocess wait) is over its TTL
    # before it advances a single step.
    if _is_over_ttl(instance):
        _timeout_instance(instance)
        return
    for _ in range(MAX_STEPS):
        # Re-check each step: a long synchronous pass (big loop / subprocess
        # fan-out) could blow the wall clock inside one _run call.
        if _is_over_ttl(instance):
            _timeout_instance(instance)
            return
        # Deterministic pick: an unordered .first() lets SQLite and PG execute
        # parallel branches in different orders, so the last writer of a shared
        # variable diverges between backends. "id" breaks created_at ties
        # between siblings created in the same statement.
        token = (
            instance.tokens.filter(status=WorkflowToken.Status.ACTIVE)
            .order_by("created_at", "id")
            .first()
        )
        if token is None:
            break
        _process(token)
    else:
        # Leave no ACTIVE/WAITING tokens behind, or a later run resumes them.
        instance.tokens.filter(status__in=LIVE_TOKEN_STATUSES).update(
            status=WorkflowToken.Status.ERROR
        )
        _fail_instance(instance, "Max execution steps exceeded")
        return
    _refresh_status(instance)


def _set_iteration_overlay(token):
    """Expose the token's innermost iteration context to _render_context.
    Execution is single-token-at-a-time inside a run, so the transient
    instance attribute is safe."""
    stack = token.iteration_context or []
    token.instance._iteration_context = dict(stack[-1]) if stack else None


def _process(token):
    node = token.current_node
    instance = token.instance
    _log(instance, WorkflowInstanceLog.EventType.NODE_ENTERED, node=node)
    _set_iteration_overlay(token)

    failure = None
    failure_retryable = True
    try:
        # Savepoint: a DB error here would otherwise poison run_instance's
        # atomic block and take _handle_failure's error token down with it.
        # Deliberate failures are caught inside so the block exits clean and
        # keeps the writes explaining them (e.g. the authorization-denied log).
        with transaction.atomic():
            try:
                if node.type == WorkflowNode.Type.END:
                    _terminate_run(token, node)
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
                    if isinstance(output, DeferredTask):
                        output.dispatch(token)
                        return
                    _persist_node_output(node, output, instance)
                    _log(
                        instance,
                        WorkflowInstanceLog.EventType.ACTION_EXECUTED,
                        node=node,
                        message=config.get("type", ""),
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
            except FatalActionError as e:
                failure = str(e)
                failure_retryable = False
            except (ActionError, EngineError) as e:
                failure = str(e)
    except Exception as e:  # noqa: BLE001 — a buggy action must not 500 the request
        failure = f"{type(e).__name__}: {e}"
    if failure is not None:
        _handle_failure(token, failure, retryable=failure_retryable)


def _handle_failure(token, message, retryable=True):
    """Retry policy: schedule a delayed Huey re-execution while attempts
    remain on action/subprocess nodes, else park the token in error.
    retryable=False (permanent config/validation failures) skips the retry
    schedule and fails immediately — no retry can change the outcome."""
    node = token.current_node
    retryable = retryable and node.type in (
        WorkflowNode.Type.ACTION,
        WorkflowNode.Type.SUBPROCESS,
    )
    if not retryable or token.retry_count >= node.retry_max_attempts:
        controller = token.loop_controller
        if controller is not None and controller.status == WorkflowToken.Status.WAITING:
            controller.instance = token.instance
            policy = (controller.current_node.loop_config or {}).get(
                "on_item_error", "continue"
            )
            if policy == "continue":
                # continue policy: the iteration is recorded as
                # failed and the loop moves on instead of stalling the run.
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
            # stop policy: fail the body token AND the parked controller, or the
            # controller waits forever. Loop restart-from-item-0 via
            # controller retry is deliberately out of scope.
            _fail_token(token, message)
            _fail_token(controller, f"loop stopped on item error: {message}")
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

    # on_commit: the RETRYING row must be visible before the consumer runs, or
    # a fast (short-delay) task finds nothing to retry and the token strands.
    token_id = str(token.id)
    transaction.on_commit(
        lambda: retry_token_task.schedule(args=(token_id,), delay=delay)
    )


LOOP_MAX_ITEMS = 100
LOOP_TEMPLATE_RE = re.compile(r"^\{\{\s*([\w.]+)\s*\}\}$")


def _loop_each_edges(node):
    return [e for e in node.outgoing_edges.all() if e.source_port == "each"]


def _process_loop(token):
    """Loop node. The first token to arrive becomes the CONTROLLER:
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
    match = LOOP_TEMPLATE_RE.match(expression) if isinstance(expression, str) else None
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
    if not state or "outstanding" not in state:
        # The controller already finished this loop (publish validation forbids
        # body fan-out, so a late second return should be unreachable); ignore
        # rather than KeyError.
        return
    if failed:
        state["errors"].append({"index": state["index"], "message": failed})
    state["outstanding"] -= 1
    controller.loop_state = state
    controller.save(update_fields=["loop_state", "updated_at"])
    if state["outstanding"] > 0:
        return

    # Iteration complete: collect (unless it failed), then advance.
    iteration_failed = any(e["index"] == state["index"] for e in state["errors"])
    collect = (controller.current_node.loop_config or {}).get("collect")
    if collect and not iteration_failed:
        overlay = {
            "item": state["items"][state["index"]],
            "index": state["index"],
        }
        controller.instance._iteration_context = overlay
        ctx = _render_context(controller.instance)
        # A single {{path}} keeps the resolved value's TYPE (dict/list/number);
        # render() would json.dumps it into a string. Multi-token templates
        # (e.g. "id-{{item.id}}") still go through render().
        match = LOOP_TEMPLATE_RE.match(collect) if isinstance(collect, str) else None
        value = dig(ctx, match.group(1)) if match else render(collect, ctx)
        controller.instance._iteration_context = None
        state["results"].append(value)
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
    _persist_node_output(node, output, instance)
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
    # Scope guard (fail closed): the child must live within the calling
    # workflow's folder subtree. Without this a subprocess node could invoke a
    # workflow in an unrelated domain, running as THAT workflow's run_as and
    # piping its outputs back — a cross-domain confused deputy. Subprocess
    # authoring is disabled for users, so this only backstops seeded/legacy
    # graphs, but it stays as the load-bearing runtime boundary.
    if version.folder_id not in _read_scope_folder_ids(instance.folder):
        raise EngineError("Subprocess workflow is outside this workflow's scope")
    if not version.is_active:
        # Automatic execution must not tunnel through a paused child;
        # manual-run leniency applies to direct runs only.
        raise EngineError("Subprocess workflow is inactive")
    if version.run_as is None:
        # Child runs under the CHILD version's own identity (nested
        # definer) — no identity, no run.
        raise EngineError("Subprocess workflow has no run identity")
    # Bound recursion: a subprocess cycle would otherwise nest run_instance
    # calls until the Python stack blows. Publish validation blocks direct
    # self-reference; this catches cross-workflow cycles too.
    depth = instance.trigger_depth + 1
    if depth > MAX_SUBPROCESS_DEPTH:
        raise EngineError("Subprocess nesting is too deep (possible recursion)")
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
        # Increment so nested subprocesses climb toward MAX_SUBPROCESS_DEPTH
        # and a cycle terminates instead of recursing without bound.
        trigger_depth=depth,
    )
    if child.status == WorkflowInstance.Status.COMPLETED:
        _persist_node_output(node, child.variables, instance)
    elif child.status == WorkflowInstance.Status.ACTIVE:
        token.status = WorkflowToken.Status.WAITING
        token.save(update_fields=["status", "updated_at"])
    else:
        raise EngineError(f"Subprocess failed ({child})")


def _store_node_output(node, output, instance):
    """Record the node's output (in memory) for {{nodes.<ref>.<path>}} references
    and the builder's reference-run data browser. Structure-preserving: nested
    JSON stays navigable and referenceable; only oversized leaves and collections
    shrink. The display log truncates flat and harder. Persisting is the caller's
    job — see _persist_node_output."""
    key = node.ref or str(node.id)
    instance.node_outputs[key] = _cap_structure(output)


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
    """Map selected output paths into instance variables (in memory).
    Persisting is the caller's job — see _persist_node_output."""
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


def _persist_node_output(node, output, instance):
    """Store the node output and apply its output mapping, flushing both to the
    row in a single write (they always change together at the end of a node)."""
    _store_node_output(node, output, instance)
    _apply_output_mapping(node, output, instance)
    instance.save(update_fields=["node_outputs", "variables", "updated_at"])


def _advance(token):
    node = token.current_node
    instance = token.instance
    edges = list(node.outgoing_edges.all())
    if not edges:
        # A leaf is an implicit terminal: this branch is done, siblings keep
        # running. Stopping the WHOLE run is the end node's job.
        token.status = WorkflowToken.Status.COMPLETED
        token.save(update_fields=["status", "updated_at"])
        return

    if node.type == WorkflowNode.Type.CONDITION:
        # Exclusive routing by branch: evaluate branches in order,
        # default last (always matches), first match wins; follow its wire.
        # Prefetch the whole branch subtree so evaluation doesn't N+1 over
        # groups/conditions/variables (mirrors graph.serialize_graph's shape).
        chosen = []
        branches = sorted(
            node.branches.prefetch_related(
                "condition_groups__conditions__variable",
                "condition_groups__children",
            ),
            key=lambda b: (b.is_default, b.order),
        )
        context = _render_context(instance)
        for branch in branches:
            if _evaluate_branch(branch, context):
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
    # travel with the moving token.
    # Convergence = run once per arriving token (n8n default). Waiting for all
    # branches becomes the merge node's job.
    WorkflowToken.objects.create(
        instance=instance,
        current_node=edge.target_node,
        arrived_via_edge=edge,
        iteration_context=iteration_context or [],
        loop_controller=loop_controller,
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
    # The compared value may itself be a template ({{item.severity}});
    # render it ONCE and use it for every operator (in/not_in/contains used to
    # compare against the raw "{{...}}" string and silently mis-routed).
    rendered = render(condition.value, variables)
    expected = _coerce(rendered, condition.variable.type)
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
    elif condition.variable.type == "boolean":
        # Coerce runtime the same way as expected, so a payload-mapped "true"
        # string matches the boolean literal.
        runtime = _coerce(runtime, "boolean")
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
        return str(runtime) in [part.strip() for part in str(rendered).split(",")]
    if op == "not_in":
        return str(runtime) not in [part.strip() for part in str(rendered).split(",")]
    if op == "contains":
        return str(rendered) in str(runtime)
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


def _terminate_run(token, node):
    """End node = stop the run NOW.

    Consumes every other live token, so parallel branches, parked task/event
    tokens and loop controllers all stop. The final status is deliberately left
    to _refresh_status: a clean terminate completes, but a sibling branch that
    already errored still fails the run (terminate never launders a failure).
    """
    instance = token.instance
    cancelled = (
        instance.tokens.filter(status__in=LIVE_TOKEN_STATUSES)
        .exclude(pk=token.pk)
        .update(status=WorkflowToken.Status.CONSUMED)
    )
    token.status = WorkflowToken.Status.COMPLETED
    token.save(update_fields=["status", "updated_at"])
    _abandon_children(instance)
    message = "Run stopped"
    if cancelled:
        message += f" — {cancelled} running branch(es) cancelled"
    _log(
        instance,
        WorkflowInstanceLog.EventType.RUN_TERMINATED,
        node=node,
        message=message,
    )


def _abandon_children(instance):
    """Terminating a run cascades DOWN to subprocess children it started: they
    were cut short, so they land ABANDONED. Termination never
    propagates UP — a child hitting its own end node completes normally and the
    waiting parent carries on."""
    for child in instance.children.filter(status=WorkflowInstance.Status.ACTIVE):
        child.tokens.filter(status__in=LIVE_TOKEN_STATUSES).update(
            status=WorkflowToken.Status.CONSUMED
        )
        child.status = WorkflowInstance.Status.ABANDONED
        child.save(update_fields=["status", "updated_at"])
        _log(
            child,
            WorkflowInstanceLog.EventType.RUN_TERMINATED,
            message="Abandoned: the calling workflow stopped",
        )
        _abandon_children(child)


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
    if statuses & set(LIVE_TOKEN_STATUSES):
        return
    if WorkflowToken.Status.ERROR in statuses:
        instance.status = WorkflowInstance.Status.FAILED
    else:
        instance.status = WorkflowInstance.Status.COMPLETED
        _log(instance, WorkflowInstanceLog.EventType.INSTANCE_COMPLETED)
    instance.save(update_fields=["status", "updated_at"])

    # A finished subprocess hands control back to its parent. Only act on a
    # parent token that actually parked (async child); the synchronous path
    # already handed back inside _start_subprocess.
    if not instance.parent_token_id:
        return
    parent_token = instance.parent_token
    if not parent_token or parent_token.status != WorkflowToken.Status.WAITING:
        return
    if instance.status == WorkflowInstance.Status.COMPLETED:
        # Mirror the synchronous path: store the node output for
        # {{nodes.<subprocess>.<path>}} refs, THEN apply output_mapping — but
        # under the parent instance lock, or two sibling subprocesses finishing
        # together clobber each other's read-modify-write of the parent's
        # variables/node_outputs. The parent row is already held: every entry
        # point locks the whole ancestor chain root-first
        # (_lock_instance_tree), so this select_for_update is a re-acquire.
        with transaction.atomic():
            parent_instance = WorkflowInstance.objects.select_for_update().get(
                id=parent_token.instance_id
            )
            parent_token.refresh_from_db()
            if parent_token.status != WorkflowToken.Status.WAITING:
                return
            parent_token.instance = parent_instance
            _persist_node_output(
                parent_token.current_node, instance.variables, parent_instance
            )
            # resume_token re-acquires the same row lock in this transaction
            # (a no-op) and re-checks WAITING before advancing.
            resume_token(parent_token)
    elif instance.status == WorkflowInstance.Status.FAILED:
        # A failed async child must surface on the parent, or the parent token
        # waits forever. Route through the node's retry policy like the
        # synchronous EngineError path in _start_subprocess, under the parent
        # instance lock (mirrors resume_token).
        with transaction.atomic():
            parent_instance = WorkflowInstance.objects.select_for_update().get(
                id=parent_token.instance_id
            )
            parent_token.refresh_from_db()
            if parent_token.status != WorkflowToken.Status.WAITING:
                return
            parent_token.instance = parent_instance
            parent_token.status = WorkflowToken.Status.ACTIVE
            parent_token.save(update_fields=["status", "updated_at"])
            _handle_failure(parent_token, f"Subprocess failed ({instance})")
            _run(parent_instance)


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
