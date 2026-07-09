"""Publish-time graph validation (spec D7).

Drafts can be saved in any state; publishing requires a sound graph. Each
error carries the offending node/edge id so the canvas can surface it in
place.
"""

from .models import NodeAssignment, WorkflowNode, WorkflowVersion


def validate_graph(version):
    errors = []
    nodes = list(version.nodes.prefetch_related("assignments"))
    edges = list(version.edges.all())
    variable_keys = set(version.variables.values_list("key", flat=True))
    nodes_by_id = {node.id: node for node in nodes}

    start_nodes = [n for n in nodes if n.type == WorkflowNode.Type.START]
    end_nodes = [n for n in nodes if n.type == WorkflowNode.Type.END]

    if len(start_nodes) != 1:
        errors.append(
            _error("start_node_count", "The graph needs exactly one start node")
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

    if start_nodes:
        reachable = _traverse(start_nodes[0].id, outgoing)
        for node in nodes:
            if node.id not in reachable:
                errors.append(
                    _error(
                        "node_unreachable",
                        "This node cannot be reached from the start node",
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
        if node.type == WorkflowNode.Type.START and incoming[node.id]:
            errors.append(
                _error(
                    "start_has_incoming",
                    "The start node cannot have incoming edges",
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
