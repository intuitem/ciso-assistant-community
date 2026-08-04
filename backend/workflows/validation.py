"""Publish-time graph validation (spec D7).

Drafts can be saved in any state; publishing requires a sound graph. Each
error carries the offending node/edge id so the canvas can surface it in
place.
"""

import json
import re

from .models import (
    NodeAssignment,
    WorkflowNode,
    WorkflowSecret,
    WorkflowVersion,
)
from .actions import validate_read_config as _validate_read_config
from .triggers import validate_trigger_config

SECRET_NAME_RE = re.compile(r"\{\{\s*secrets\.(\w+)")
NODE_REF_RE = re.compile(r"\{\{\s*nodes\.([A-Za-z_]\w*)")


def validate_graph(version):
    errors = []
    nodes = list(version.nodes.prefetch_related("assignments", "branches"))
    edges = list(version.edges.all())
    variable_keys = set(version.variables.values_list("key", flat=True))
    nodes_by_id = {node.id: node for node in nodes}
    existing_secrets = _existing_secret_names(version, nodes)
    # Which branches carry a wire (a branch with a condition but no wire is a
    # defined-but-unrouted case — spec D25).
    wired_branch_ids = {
        e.source_branch_id for e in edges if e.source_branch_id is not None
    }

    loop_ids = {n.id for n in nodes if n.type == WorkflowNode.Type.LOOP}
    for edge in edges:
        is_loop_source = edge.source_node_id in loop_ids
        if is_loop_source and edge.source_port not in ("each", "done"):
            errors.append(
                _error(
                    "loop_port_missing",
                    "Edges leaving a loop node must use its 'each' or 'done' port",
                    edge=edge,
                )
            )
        if not is_loop_source and edge.source_port:
            errors.append(
                _error(
                    "loop_port_missing",
                    "Only edges leaving a loop node may carry a source_port",
                    edge=edge,
                )
            )

    known_refs = {n.ref for n in nodes if n.ref}
    trigger_nodes = [n for n in nodes if n.type == WorkflowNode.Type.TRIGGER]
    end_nodes = [n for n in nodes if n.type == WorkflowNode.Type.END]

    if not trigger_nodes:
        errors.append(
            _error("trigger_node_missing", "The graph needs at least one trigger node")
        )
    if not end_nodes:
        errors.append(
            _error("end_node_missing", "The graph needs at least one end node")
        )

    outgoing = {node.id: [] for node in nodes}
    incoming = {node.id: [] for node in nodes}
    for edge in edges:
        outgoing[edge.source_node_id].append(edge.target_node_id)
        incoming[edge.target_node_id].append(edge.source_node_id)

    if trigger_nodes:
        reachable = set()
        for trigger_node in trigger_nodes:
            reachable |= _traverse(trigger_node.id, outgoing)
        for node in nodes:
            if node.id not in reachable:
                errors.append(
                    _error(
                        "node_unreachable",
                        "This node cannot be reached from any trigger node",
                        node=node,
                    )
                )

    if end_nodes:
        reaches_end = set()
        for end in end_nodes:
            reaches_end |= _traverse(end.id, incoming)
        for node in nodes:
            if node.id not in reaches_end:
                errors.append(
                    _error(
                        "dead_end",
                        "No path from this node reaches an end node",
                        node=node,
                    )
                )

    for node in nodes:
        if node.type != WorkflowNode.Type.END and not outgoing[node.id]:
            errors.append(
                _error(
                    "missing_outgoing_edge",
                    "Only end nodes may have no outgoing edge",
                    node=node,
                )
            )
        if node.type == WorkflowNode.Type.TRIGGER:
            if incoming[node.id]:
                errors.append(
                    _error(
                        "trigger_has_incoming",
                        "Trigger nodes cannot have incoming edges",
                        node=node,
                    )
                )
            for code, message in validate_trigger_config(node, version.workflow):
                errors.append(_error(code, message, node=node))
        if node.type == WorkflowNode.Type.ACTION:
            for name in sorted(_referenced_secret_names(node)):
                if name not in existing_secrets:
                    errors.append(
                        _error(
                            "secret_missing",
                            f"Secret '{name}' does not exist — add it in the "
                            "secrets panel before publishing",
                            node=node,
                        )
                    )
            for code, message in _validate_read_config(node):
                errors.append(_error(code, message, node=node))
        for ref in sorted(_referenced_node_refs(node) - known_refs):
            errors.append(
                _error(
                    "node_reference_missing",
                    f"'{{{{nodes.{ref}}}}}' references a node that does not exist",
                    node=node,
                )
            )
        if node.type == WorkflowNode.Type.CONDITION:
            branches = list(node.branches.all())
            # Exactly one default (otherwise) branch guarantees exhaustiveness:
            # it always matches, so the exclusive fork can never strand a token
            # at runtime (engine raises "No branch matched" otherwise).
            if not any(b.is_default for b in branches):
                errors.append(
                    _error(
                        "condition_default_missing",
                        "This branch node has no default (otherwise) branch — "
                        "add one so no case is left unhandled",
                        node=node,
                    )
                )
            # A branch that is defined but not wired routes nowhere.
            if any(b.id not in wired_branch_ids for b in branches):
                errors.append(
                    _error(
                        "branch_unwired",
                        "A branch is not connected to a next step — wire every "
                        "branch or remove it",
                        node=node,
                    )
                )
        if node.type == WorkflowNode.Type.LOOP:
            for code, message in _validate_loop(node, edges, outgoing, nodes_by_id):
                errors.append(_error(code, message, node=node))
        if node.type == WorkflowNode.Type.TASK and not node.task_template_id:
            errors.append(
                _error(
                    "task_template_missing",
                    "Task nodes need a task template",
                    node=node,
                )
            )
        if node.type == WorkflowNode.Type.EVENT and not node.event_key:
            errors.append(
                _error(
                    "event_key_missing",
                    "Event nodes need an event key",
                    node=node,
                )
            )
        if node.type == WorkflowNode.Type.SUBPROCESS:
            target = node.subprocess_workflow
            if target is None:
                errors.append(
                    _error(
                        "subprocess_missing",
                        "Subprocess nodes need a target workflow",
                        node=node,
                    )
                )
            elif target.id == version.workflow_id:
                errors.append(
                    _error(
                        "subprocess_self_reference",
                        "A subprocess node cannot call its own workflow "
                        "(infinite recursion)",
                        node=node,
                    )
                )
            elif not target.versions.filter(
                status=WorkflowVersion.Status.PUBLISHED
            ).exists():
                errors.append(
                    _error(
                        "subprocess_unpublished",
                        "The subprocess workflow has no published version",
                        node=node,
                    )
                )
            elif not target.is_active:
                errors.append(
                    _error(
                        "subprocess_inactive",
                        "The subprocess workflow is inactive — enable it "
                        "before publishing",
                        node=node,
                    )
                )
            elif target.published_version.run_as is None:
                # Same TOCTOU caveat as subprocess_inactive: the child
                # republishes independently; the engine re-checks at run time.
                errors.append(
                    _error(
                        "subprocess_missing_identity",
                        "The subprocess workflow has no run identity — "
                        "republish it first",
                        node=node,
                    )
                )
            else:
                # Best effort (the child republishes independently, same
                # TOCTOU as subprocess_unpublished): the child's current
                # published version must resolve an unambiguous entry.
                from .engine import EngineError, default_entry_node

                try:
                    default_entry_node(target.published_version)
                except EngineError:
                    errors.append(
                        _error(
                            "subprocess_entry_ambiguous",
                            "The subprocess workflow has no unambiguous entry "
                            "trigger (give it a single manual trigger node)",
                            node=node,
                        )
                    )
        for assignment in node.assignments.all():
            if (
                assignment.resolve_type == NodeAssignment.ResolveType.ACTOR
                and assignment.actor_id is None
            ):
                errors.append(
                    _error(
                        "assignment_actor_missing",
                        "An assignment has no actor selected",
                        node=node,
                    )
                )
            if (
                assignment.resolve_type == NodeAssignment.ResolveType.VARIABLE
                and assignment.variable_key not in variable_keys
            ):
                errors.append(
                    _error(
                        "assignment_variable_undeclared",
                        f"Assignment variable '{assignment.variable_key}' is not declared",
                        node=node,
                    )
                )

    for edge in edges:
        source = nodes_by_id.get(edge.source_node_id)
        if source and source.type == WorkflowNode.Type.END:
            errors.append(
                _error(
                    "end_has_outgoing",
                    "End nodes cannot have outgoing edges",
                    edge=edge,
                )
            )

    return errors


def _referenced_secret_names(node):
    return set(SECRET_NAME_RE.findall(json.dumps(node.action_config or {})))


LOOP_COLLECTION_RE = re.compile(r"^\{\{\s*[\w.]+\s*\}\}$")


def _validate_loop(node, edges, outgoing, nodes_by_id):
    """Loop rules (spec D29): a valid collection expression, both ports wired,
    every `each` path returns to the loop, and no `each` path escapes into the
    rest of the graph."""
    results = []
    config = node.loop_config or {}
    collection = config.get("collection") or ""
    if not isinstance(collection, str) or not LOOP_COLLECTION_RE.match(collection):
        results.append(
            (
                "loop_collection_invalid",
                "The loop needs a collection: a single {{path}} expression "
                "resolving to a list",
            )
        )
    if config.get("on_item_error", "continue") not in ("continue", "stop"):
        results.append(
            (
                "loop_collection_invalid",
                f"Unknown on_item_error '{config.get('on_item_error')}'",
            )
        )

    own_edges = [e for e in edges if e.source_node_id == node.id]
    each_edges = [e for e in own_edges if e.source_port == "each"]
    done_edges = [e for e in own_edges if e.source_port == "done"]
    if not each_edges:
        results.append(
            ("loop_body_no_return", "Nothing is wired to the loop's 'each' port")
        )
    if not done_edges:
        results.append(
            ("loop_body_no_return", "Nothing is wired to the loop's 'done' port")
        )
    if not each_edges:
        return results

    # Walk forward from the each targets; the loop node itself is the only
    # legal exit. Reaching a dead end (or an end node) without coming home is
    # an escape; the loop would wait forever.
    body = set()
    stack = [e.target_node_id for e in each_edges]
    escapes = False
    returns = False
    while stack:
        current = stack.pop()
        if current == node.id:
            returns = True
            continue
        if current in body:
            continue
        body.add(current)
        next_ids = outgoing.get(current, [])
        if not next_ids:
            escapes = True
            continue
        stack.extend(next_ids)
    done_reachable = set()
    stack = [e.target_node_id for e in done_edges]
    while stack:
        current = stack.pop()
        if current in done_reachable or current == node.id:
            continue
        done_reachable.add(current)
        stack.extend(outgoing.get(current, []))
    if body & done_reachable:
        escapes = True
    # Parallel fan-out inside the body breaks the controller's per-iteration
    # accounting (one emitted token, N returning tokens), so forbid it. A
    # condition node is exempt: exactly one branch fires, so one token returns.
    for body_id in body:
        body_node = nodes_by_id.get(body_id)
        if body_node is None or body_node.type == WorkflowNode.Type.CONDITION:
            continue
        if len(outgoing.get(body_id, [])) > 1:
            results.append(
                (
                    "loop_body_fan_out",
                    "A loop body step branches into parallel paths; parallel "
                    "fan-out inside a loop body is not supported — use a "
                    "condition node to choose a single path",
                )
            )
            break
    if not returns:
        results.append(
            (
                "loop_body_no_return",
                "The loop body never returns to the loop node — wire the last "
                "step back to the loop",
            )
        )
    if escapes:
        results.append(
            (
                "loop_body_escape",
                "A path from the loop's 'each' port leaves the body without "
                "returning to the loop",
            )
        )
    return results


def _referenced_node_refs(node):
    """Refs named by {{nodes.<ref>...}} anywhere in the node's configs. The
    builder rewrites references on rename (spec D28); this is the safety net
    for imports and hand-written documents. loop_config is included: a loop's
    collection/collect expressions hold {{nodes.<ref>...}} too."""
    blob = json.dumps(
        [
            node.action_config or {},
            node.input_mapping or {},
            node.output_mapping or {},
            node.loop_config or {},
        ]
    )
    return set(NODE_REF_RE.findall(blob))


def _existing_secret_names(version, nodes):
    """Names resolvable at runtime: workflow-scoped, so the engine looks secrets
    up on the version's own workflow (actions._secrets_context)."""
    referenced = set()
    for node in nodes:
        if node.type == WorkflowNode.Type.ACTION:
            referenced |= _referenced_secret_names(node)
    if not referenced:
        return set()

    return set(
        WorkflowSecret.objects.filter(
            workflow_id=version.workflow_id,
            name__in=referenced,
        ).values_list("name", flat=True)
    )


def _traverse(start_id, adjacency):
    seen = {start_id}
    stack = [start_id]
    while stack:
        for neighbor in adjacency.get(stack.pop(), []):
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return seen


def _error(code, message, node=None, edge=None):
    return {
        "code": code,
        "message": message,
        "node_id": str(node.id) if node else None,
        "edge_id": str(edge.id) if edge else None,
    }
