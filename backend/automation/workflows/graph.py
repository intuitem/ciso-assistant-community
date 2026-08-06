"""Graph document serialization for the workflow builder.

The canvas edits a whole workflow version as one JSON document and saves it
atomically. Rows are matched by client-generated UUIDs: ids present in the
payload are upserted, rows absent from the payload are deleted. Condition
trees, assignments and presentations are recreated on every save (they are
small and have no identity worth preserving).
"""

import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError

from .models import (
    Condition,
    ConditionBranch,
    ConditionGroup,
    NodeAssignment,
    NodePresentation,
    WorkflowEdge,
    WorkflowNode,
    WorkflowVariable,
)

NODE_FIELDS = [
    "type",
    "label",
    "ref",
    "action_config",
    "loop_config",
    "trigger_config",
    "input_mapping",
    "output_mapping",
    "event_key",
    "event_filters",
    "position",
    "retry_max_attempts",
    "retry_delay_seconds",
    "retry_backoff",
]

REF_RE = re.compile(r"^[a-z][a-z0-9_]{0,99}$")

VARIABLE_FIELDS = ["key", "type", "default_value"]
EDGE_FIELDS = ["label", "source_port"]
ASSIGNMENT_FIELDS = [
    "resolve_type",
    "variable_key",
    "is_blocking",
    "participation",
]
PRESENTATION_FIELDS = [
    "type",
    "redirect_path",
    "redirect_params",
    "completion_cta",
    "instructions",
]
CONDITION_FIELDS = ["op", "value", "order"]
BRANCH_FIELDS = ["name", "order", "is_default"]


def serialize_graph(version):
    nodes = []
    for node in version.nodes.prefetch_related(
        "assignments__role",
        "assignments__actor",
        "branches__condition_groups__conditions",
    ).select_related("presentation", "task_template", "subprocess_workflow"):
        assignments = [
            {
                "id": str(a.id),
                "role": str(a.role_id),
                "role_code": a.role.code,
                "actor": str(a.actor_id) if a.actor_id else None,
                "actor_name": str(a.actor) if a.actor_id else None,
                **{f: getattr(a, f) for f in ASSIGNMENT_FIELDS},
            }
            for a in node.assignments.all()
        ]
        presentation = None
        if hasattr(node, "presentation"):
            presentation = {
                f: getattr(node.presentation, f) for f in PRESENTATION_FIELDS
            }
        nodes.append(
            {
                "id": str(node.id),
                "task_template": str(node.task_template_id)
                if node.task_template_id
                else None,
                "task_template_name": node.task_template.name
                if node.task_template_id
                else None,
                "subprocess_workflow": str(node.subprocess_workflow_id)
                if node.subprocess_workflow_id
                else None,
                "subprocess_workflow_name": node.subprocess_workflow.name
                if node.subprocess_workflow_id
                else None,
                "assignments": assignments,
                "presentation": presentation,
                "branches": [
                    {
                        "id": str(branch.id),
                        "condition_groups": _serialize_condition_tree(branch),
                        **{f: getattr(branch, f) for f in BRANCH_FIELDS},
                    }
                    for branch in node.branches.all()
                ],
                **{f: getattr(node, f) for f in NODE_FIELDS},
            }
        )

    edges = []
    for edge in version.edges.all():
        edges.append(
            {
                "id": str(edge.id),
                "source": str(edge.source_node_id),
                "target": str(edge.target_node_id),
                "source_branch": str(edge.source_branch_id)
                if edge.source_branch_id
                else None,
                **{f: getattr(edge, f) for f in EDGE_FIELDS},
            }
        )

    variables = [
        {
            "id": str(v.id),
            **{f: getattr(v, f) for f in VARIABLE_FIELDS},
        }
        for v in version.variables.all()
    ]

    return {
        "id": str(version.id),
        "version_number": version.version_number,
        "status": version.status,
        "nodes": nodes,
        "edges": edges,
        "variables": variables,
    }


def _serialize_condition_tree(branch):
    groups = list(branch.condition_groups.all())
    by_parent = {}
    for group in groups:
        by_parent.setdefault(group.parent_group_id, []).append(group)

    def build(group):
        return {
            "operator": group.operator,
            "order": group.order,
            "conditions": [
                {
                    "variable": str(c.variable_id),
                    **{f: getattr(c, f) for f in CONDITION_FIELDS},
                }
                for c in group.conditions.all()
            ],
            "children": [build(child) for child in by_parent.get(group.id, [])],
        }

    return [build(group) for group in by_parent.get(None, [])]


class GraphValidationError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


@transaction.atomic
def save_graph(version, payload):
    """Replace the version's graph with the payload. Draft versions only."""
    nodes_data = payload.get("nodes", [])
    edges_data = payload.get("edges", [])
    variables_data = payload.get("variables", [])

    node_ids = {n.get("id") for n in nodes_data}
    edge_ids = {e.get("id") for e in edges_data}
    variable_ids = {v.get("id") for v in variables_data}
    branch_ids = {b.get("id") for n in nodes_data for b in (n.get("branches") or [])}
    if None in node_ids | edge_ids | variable_ids | branch_ids:
        raise GraphValidationError("Every node, edge, variable and branch needs an id")

    # Deletions FIRST, so a same-key variable (or same-position row) can be
    # dropped and recreated with a new id in a single save without tripping
    # unique constraints. Condition trees are wiped wholesale: they are
    # recreated for every branch in the payload, and clearing them up front
    # releases the PROTECT on removed variables.
    ConditionGroup.objects.filter(branch__node__version=version).delete()
    version.edges.exclude(id__in=edge_ids).delete()
    ConditionBranch.objects.filter(node__version=version).exclude(
        id__in=branch_ids
    ).delete()
    version.nodes.exclude(id__in=node_ids).delete()
    try:
        version.variables.exclude(id__in=variable_ids).delete()
    except ProtectedError:
        raise GraphValidationError(
            "A removed variable is still referenced by a branch condition"
        )

    # Upsert variables first: conditions reference them.
    variables = {}
    existing_variables = {str(v.id): v for v in version.variables.all()}
    for data in variables_data:
        variable = existing_variables.get(data["id"]) or WorkflowVariable(
            id=data["id"], version=version
        )
        for field in VARIABLE_FIELDS:
            if field in data:
                setattr(variable, field, data[field])
        _save_row(variable)
        variables[data["id"]] = variable

    nodes = {}
    branches = {}
    seen_refs = set()
    existing_nodes = {str(n.id): n for n in version.nodes.all()}
    for data in nodes_data:
        node = existing_nodes.get(data["id"]) or WorkflowNode(
            id=data["id"], version=version
        )
        for field in NODE_FIELDS:
            if field in data:
                setattr(node, field, data[field])
        if node.ref and not REF_RE.match(node.ref):
            raise GraphValidationError(
                f"Invalid node ref '{node.ref}': lowercase letters, digits and "
                "underscores only, starting with a letter"
            )
        node.task_template_id = data.get("task_template") or None
        node.subprocess_workflow_id = data.get("subprocess_workflow") or None
        _save_row(node)
        if node.ref in seen_refs:
            raise GraphValidationError(f"Duplicate node ref '{node.ref}'")
        seen_refs.add(node.ref)
        nodes[data["id"]] = node

        # Assignments and presentation are recreated wholesale.
        node.assignments.all().delete()
        for assignment_data in data.get("assignments", []):
            assignment = NodeAssignment(
                node=node,
                role_id=assignment_data.get("role"),
                actor_id=assignment_data.get("actor") or None,
            )
            for field in ASSIGNMENT_FIELDS:
                if field in assignment_data:
                    setattr(assignment, field, assignment_data[field])
            _save_row(assignment)
        NodePresentation.objects.filter(node=node).delete()
        if data.get("presentation"):
            presentation = NodePresentation(node=node)
            for field in PRESENTATION_FIELDS:
                if field in data["presentation"]:
                    setattr(presentation, field, data["presentation"][field])
            _save_row(presentation)

        # Branches are upserted by id (edges reference them via source_branch);
        # each branch's condition tree is recreated wholesale.
        existing_branches = {str(b.id): b for b in node.branches.all()}
        for branch_data in data.get("branches", []):
            branch = existing_branches.get(branch_data["id"]) or ConditionBranch(
                id=branch_data["id"], node=node
            )
            for field in BRANCH_FIELDS:
                if field in branch_data:
                    setattr(branch, field, branch_data[field])
            _save_row(branch)
            branches[branch_data["id"]] = branch
            for group_data in branch_data.get("condition_groups", []):
                _save_condition_tree(branch, group_data, None, variables)

    edges = {}
    existing_edges = {str(e.id): e for e in version.edges.all()}
    for data in edges_data:
        if data.get("source") not in nodes or data.get("target") not in nodes:
            raise GraphValidationError("Edge references a node absent from the payload")
        source_branch_id = data.get("source_branch")
        if source_branch_id is not None and source_branch_id not in branches:
            raise GraphValidationError(
                "Edge references a branch absent from the payload"
            )
        edge = existing_edges.get(data["id"]) or WorkflowEdge(
            id=data["id"], version=version
        )
        for field in EDGE_FIELDS:
            if field in data:
                setattr(edge, field, data[field])
        edge.source_node = nodes[data["source"]]
        edge.target_node = nodes[data["target"]]
        edge.source_branch = (
            branches.get(source_branch_id) if source_branch_id else None
        )
        _save_row(edge)
        edges[data["id"]] = edge

    return serialize_graph(version)


def _save_condition_tree(branch, group_data, parent, variables):
    group = ConditionGroup(
        branch=branch,
        parent_group=parent,
        operator=group_data.get("operator", ConditionGroup.Operator.AND),
        order=group_data.get("order", 0),
    )
    _save_row(group)
    for condition_data in group_data.get("conditions", []):
        if condition_data.get("variable") not in variables:
            raise GraphValidationError(
                "Condition references a variable absent from the payload"
            )
        condition = Condition(
            group=group,
            variable=variables[condition_data["variable"]],
        )
        for field in CONDITION_FIELDS:
            if field in condition_data:
                setattr(condition, field, condition_data[field])
        _save_row(condition)
    for child_data in group_data.get("children", []):
        _save_condition_tree(branch, child_data, group, variables)


def _save_row(instance):
    try:
        instance.save()
    except ValidationError as e:
        raise GraphValidationError("; ".join(e.messages))
