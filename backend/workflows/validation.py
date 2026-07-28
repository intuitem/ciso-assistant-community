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
from .actions import validate_iteration_config as _validate_iteration_config
from .actions import validate_read_config as _validate_read_config
from .triggers import validate_trigger_config

SECRET_NAME_RE = re.compile(r"\{\{\s*secrets\.(\w+)")


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
            for code, message in _validate_iteration_config(node):
                errors.append(_error(code, message, node=node))
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


def _existing_secret_names(version, nodes):
    """Names resolvable at runtime: the engine looks secrets up within the
    instance folder's ancestors + subtree (actions._secrets_context)."""
    referenced = set()
    for node in nodes:
        if node.type == WorkflowNode.Type.ACTION:
            referenced |= _referenced_secret_names(node)
    if not referenced:
        return set()
    from .actions import _accessible_folder_ids

    return set(
        WorkflowSecret.objects.filter(
            folder_id__in=_accessible_folder_ids(version.folder),
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
