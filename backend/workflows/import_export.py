"""Portable YAML import/export of workflow definitions.

The exported document is meant for humans and cross-instance sharing, so it
carries no UUIDs: nodes are identified by their ref slug, edge conditions
reference variables by key, and cross-object links (task templates, subprocess
workflows, roles) travel by name. Secrets are referenced by name only — the
`requires.secrets` manifest lists what the workflow expects without carrying
values. Import creates a brand-new workflow with a draft v1 and returns
warnings for anything that could not be resolved on this instance; publish
validation remains the safety net for incomplete graphs.
"""

import json
import re
from uuid import uuid4

from django.db import transaction

from .graph import REF_RE, GraphValidationError, save_graph, serialize_graph
from .models import (
    Workflow,
    WorkflowNode,
    WorkflowSecret,
    WorkflowVariable,
    WorkflowVersion,
)

SCHEMA_VERSION = 1
MAX_CONDITION_DEPTH = 5

# Capability manifest (spec D28): the forward-compat gate. Exports tag every
# semantics-bearing feature the document uses; importers hard-reject unknown
# tags instead of silently dropping behavior. Every future feature whose
# absence would silently change execution MUST register a tag here.
KNOWN_CAPABILITIES = {"read_objects", "loop"}

SECRET_NAME_RE = re.compile(r"\{\{\s*secrets\.(\w+)")
UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b")

NODE_JSON_FIELDS = [
    "action_config",
    "loop_config",
    "trigger_config",
    "input_mapping",
    "output_mapping",
    "event_filters",
    "position",
]

# Positions never travel: the builder auto-lays-out graphs that arrive without
# them (dagre), so exports stay small and diff-clean. Import still accepts
# `position` for hand-written files (NODE_JSON_FIELDS keeps it).
EXPORTED_NODE_JSON_FIELDS = [f for f in NODE_JSON_FIELDS if f != "position"]


class WorkflowImportError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


# ---------- export ----------


def export_workflow(workflow):
    version = (
        workflow.draft_version
        or workflow.published_version
        or workflow.versions.first()
    )
    document = serialize_graph(version)
    refs = _ref_map(document["nodes"])
    variable_keys = {v["id"]: v["key"] for v in document["variables"]}
    taxonomies = _role_taxonomies(document["nodes"])

    data = {"schema_version": SCHEMA_VERSION, "name": workflow.name}
    if workflow.ref_id:
        data["ref_id"] = workflow.ref_id
    if workflow.description:
        data["description"] = workflow.description

    requires = {}
    secret_names = _referenced_secrets(document["nodes"])
    if secret_names:
        requires["secrets"] = secret_names
    capabilities = _used_capabilities(document["nodes"])
    if capabilities:
        requires["capabilities"] = capabilities
    if requires:
        data["requires"] = requires

    # Edges reference their branch BY NAME (spec D28 — positional references
    # are where LLM edits silently rewire graphs). The exporter guarantees a
    # unique-per-node name for every branch, synthesizing one when blank.
    branch_names = _branch_name_map(document["nodes"])

    data["graph"] = {
        "variables": [_export_variable(v) for v in document["variables"]],
        "nodes": [
            _export_node(n, refs, taxonomies, variable_keys, branch_names)
            for n in document["nodes"]
        ],
        "edges": [_export_edge(e, refs, branch_names) for e in document["edges"]],
    }
    return data


def _ref_map(nodes):
    """Node id → ref. Legacy rows saved before refs existed get one synthesized
    with the model's own algorithm so the YAML never falls back to UUIDs."""
    refs = {}
    taken = {n["ref"] for n in nodes if n["ref"]}
    for node in nodes:
        ref = node["ref"]
        if not ref:
            from django.utils.text import slugify

            base = (
                slugify(node["label"] or node["type"]).replace("-", "_")[:80]
                or node["type"]
            )
            ref, suffix = base, 2
            while ref in taken:
                ref = f"{base}_{suffix}"
                suffix += 1
            taken.add(ref)
        refs[node["id"]] = ref
    return refs


def _role_taxonomies(nodes):
    from pmbok.models import ResponsibilityRole

    role_ids = {
        a["role"] for node in nodes for a in node["assignments"] if a.get("role")
    }
    roles = ResponsibilityRole.objects.in_bulk(role_ids)
    return {str(pk): role.taxonomy for pk, role in roles.items()}


def _referenced_secrets(nodes):
    blob = json.dumps([n["action_config"] for n in nodes])
    return sorted(set(SECRET_NAME_RE.findall(blob)))


def _used_capabilities(nodes):
    used = set()
    for node in nodes:
        config = node["action_config"] or {}
        if config.get("type") == "read_objects":
            used.add("read_objects")
        if node["type"] == "loop":
            used.add("loop")
    return sorted(used)


def _branch_name_map(nodes):
    """Branch id → unique-per-node exported name. Blank names synthesize as
    'otherwise' (default branch) or 'branch_<position>'."""
    names = {}
    for node in nodes:
        taken = set()
        for position, branch in enumerate(node["branches"]):
            base = str(branch["name"]).strip() or (
                "otherwise" if branch["is_default"] else f"branch_{position + 1}"
            )
            candidate, suffix = base, 2
            while candidate in taken:
                candidate = f"{base}_{suffix}"
                suffix += 1
            taken.add(candidate)
            names[branch["id"]] = candidate
    return names


def _strip_empty(value):
    """Canonical exports carry no empty values (spec D28): '', None, {} and []
    are dropped recursively; a filter-tree dict reduced to bare {'operator'}
    is empty too. Booleans and numbers always survive."""
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            stripped = _strip_empty(item)
            if stripped in ("", None) or stripped == {} or stripped == []:
                continue
            cleaned[key] = stripped
        if set(cleaned) == {"operator"}:
            return {}
        return cleaned
    if isinstance(value, list):
        return [
            stripped
            for stripped in (_strip_empty(item) for item in value)
            if not (stripped in ("", None) or stripped == {} or stripped == [])
        ]
    return value


def _export_variable(variable):
    out = {"key": variable["key"], "type": variable["type"]}
    if variable["default_value"] is not None:
        out["default_value"] = variable["default_value"]
    return out


def _export_node(node, refs, taxonomies, variable_keys, branch_names):
    out = {"ref": refs[node["id"]], "type": node["type"]}
    if node["label"]:
        out["label"] = node["label"]
    if node["join_type"] != WorkflowNode.JoinType.NONE:
        out["join_type"] = node["join_type"]
    for field in EXPORTED_NODE_JSON_FIELDS:
        value = _strip_empty(node[field])
        if value:
            out[field] = value

    if node["event_key"]:
        out["event_key"] = node["event_key"]
    if node["retry_max_attempts"]:
        out["retry"] = {
            "max_attempts": node["retry_max_attempts"],
            "delay_seconds": node["retry_delay_seconds"],
            "backoff": node["retry_backoff"],
        }
    if node["task_template_name"]:
        out["task_template"] = node["task_template_name"]
    if node["subprocess_workflow_name"]:
        out["subprocess_workflow"] = node["subprocess_workflow_name"]
    assignments = [
        _export_assignment(a, taxonomies)
        for a in node["assignments"]
        if a.get("role") and str(a["role"]) in taxonomies
    ]
    if assignments:
        out["assignments"] = assignments
    if node["presentation"]:
        presentation = {
            k: v for k, v in node["presentation"].items() if v not in ("", {}, None)
        }
        if presentation:
            out["presentation"] = presentation
    # Condition nodes own their routing branches (spec D25); the branch order is
    # the list order, so edges can reference a branch by index.
    branches = [
        _export_branch(b, variable_keys, branch_names) for b in node["branches"]
    ]
    if branches:
        out["branches"] = branches
    return out


def _export_branch(branch, variable_keys, branch_names):
    out = {"name": branch_names[branch["id"]]}
    if branch["is_default"]:
        out["is_default"] = True
    groups = _export_condition_groups(branch["condition_groups"], variable_keys)
    if groups:
        out["condition_groups"] = groups
    return out


def _export_assignment(assignment, taxonomies):
    # Actors are instance-specific and never travel; the role does.
    out = {
        "role": {
            "taxonomy": taxonomies[str(assignment["role"])],
            "code": assignment["role_code"],
        }
    }
    if assignment["resolve_type"] != "actor":
        out["resolve_type"] = assignment["resolve_type"]
    if assignment["variable_key"]:
        out["variable_key"] = assignment["variable_key"]
    if not assignment["is_blocking"]:
        out["is_blocking"] = False
    if assignment["participation"] != "task":
        out["participation"] = assignment["participation"]
    return out


def _export_edge(edge, refs, branch_names):
    out = {"source": refs[edge["source"]], "target": refs[edge["target"]]}
    if edge["label"]:
        out["label"] = edge["label"]
    # An edge leaving a condition node names the branch it wires.
    if edge["source_branch"] is not None:
        out["source_branch"] = branch_names[edge["source_branch"]]
    if edge["source_port"]:
        out["source_port"] = edge["source_port"]
    return out


def _export_condition_groups(groups, variable_keys):
    out = []
    for group in groups:
        item = {"operator": group["operator"]}
        if group["order"]:
            item["order"] = group["order"]
        conditions = []
        for condition in group["conditions"]:
            entry = {
                "variable": variable_keys[condition["variable"]],
                "op": condition["op"],
            }
            if condition["value"]:
                entry["value"] = condition["value"]
            if condition["order"]:
                entry["order"] = condition["order"]
            conditions.append(entry)
        if conditions:
            item["conditions"] = conditions
        children = _export_condition_groups(group["children"], variable_keys)
        if children:
            item["children"] = children
        out.append(item)
    return out


# ---------- import ----------


def import_workflow(data, folder, user=None):
    """Create a new workflow in `folder` from an exported document.

    Returns (workflow, warnings). Structural problems raise WorkflowImportError
    and roll everything back; resolution problems (unknown task template, role,
    out-of-scope folder filter...) degrade to warnings so the draft always
    lands in the builder.
    """
    _validate_structure(data)
    warnings = []
    with transaction.atomic():
        name = _free_name(Workflow, str(data["name"]).strip(), folder)
        if name != str(data["name"]).strip():
            warnings.append(
                f"A workflow named '{data['name']}' already exists — imported as '{name}'"
            )
        workflow = Workflow.objects.create(
            name=name,
            description=str(data.get("description") or ""),
            ref_id=str(data.get("ref_id") or "")[:100],
            folder=folder,
            # Marketplace/catalog provenance (spec D28): the document divorces
            # at import, these only record where it came from.
            source_urn=str(data.get("urn") or "")[:255],
            source_version=str(data.get("version") or "")[:50],
        )
        version = WorkflowVersion.objects.create(workflow=workflow)
        payload = _build_graph_payload(data["graph"], workflow, folder, warnings)
        try:
            save_graph(version, payload)
        except GraphValidationError as e:
            raise WorkflowImportError(e.message)
        _post_import_warnings(data, workflow, folder, warnings)
    return workflow, warnings


def _validate_structure(data):
    if not isinstance(data, dict):
        raise WorkflowImportError("The document must be a mapping")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise WorkflowImportError(
            f"Unsupported schema_version: expected {SCHEMA_VERSION}"
        )
    requested = (data.get("requires") or {}).get("capabilities") or []
    unknown = sorted(set(map(str, requested)) - KNOWN_CAPABILITIES)
    if unknown:
        raise WorkflowImportError(
            f"This document requires capabilities this version of CISO Assistant "
            f"does not support: {', '.join(unknown)} — update the application "
            "or re-export from a matching version"
        )
    if not str(data.get("name") or "").strip():
        raise WorkflowImportError("The document needs a non-empty name")
    graph = data.get("graph")
    if not isinstance(graph, dict):
        raise WorkflowImportError("The document needs a graph section")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise WorkflowImportError("graph.nodes must be a non-empty list")
    variables = graph.get("variables") or []
    edges = graph.get("edges") or []
    if not isinstance(variables, list) or not isinstance(edges, list):
        raise WorkflowImportError("graph.variables and graph.edges must be lists")

    keys = set()
    for variable in variables:
        if not isinstance(variable, dict) or not str(variable.get("key") or "").strip():
            raise WorkflowImportError("Every variable needs a non-empty key")
        key = variable["key"]
        if key in keys:
            raise WorkflowImportError(f"Duplicate variable key '{key}'")
        keys.add(key)

    node_types = set(WorkflowNode.Type.values)
    refs = set()
    node_type = {}
    branch_count = {}
    branch_names_by_ref = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise WorkflowImportError(f"graph.nodes[{index}] must be a mapping")
        ref = node.get("ref")
        if not isinstance(ref, str) or not REF_RE.match(ref):
            raise WorkflowImportError(
                f"graph.nodes[{index}].ref {ref!r} is invalid: lowercase "
                "letters, digits and underscores only, starting with a letter"
            )
        if ref in refs:
            raise WorkflowImportError(f"Duplicate node ref '{ref}'")
        refs.add(ref)
        if node.get("type") not in node_types:
            if node.get("type") == "start":
                raise WorkflowImportError(
                    "This file predates trigger nodes (it contains a 'start' "
                    "node) — re-export the workflow and import that file"
                )
            raise WorkflowImportError(
                f"Node '{ref}' has an unknown type {node.get('type')!r}"
            )
        node_type[ref] = node.get("type")
        branches = node.get("branches") or []
        if not isinstance(branches, list):
            raise WorkflowImportError(f"Node '{ref}' branches must be a list")
        for branch in branches:
            if not isinstance(branch, dict):
                raise WorkflowImportError(
                    f"Node '{ref}': every branch must be a mapping"
                )
            for group in branch.get("condition_groups") or []:
                _validate_condition_group(group, keys, depth=0)
        branch_count[ref] = len(branches)
        branch_names_by_ref[ref] = [str(b.get("name") or "").strip() for b in branches]
        named = [n for n in branch_names_by_ref[ref] if n]
        duplicates = {n for n in named if named.count(n) > 1}
        if duplicates:
            raise WorkflowImportError(
                f"Node '{ref}' has duplicate branch names: "
                f"{', '.join(sorted(duplicates))} — branch names must be "
                "unique within a node"
            )

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise WorkflowImportError(f"graph.edges[{index}] must be a mapping")
        for endpoint in ("source", "target"):
            if edge.get(endpoint) not in refs:
                raise WorkflowImportError(
                    f"graph.edges[{index}].{endpoint} {edge.get(endpoint)!r} "
                    "is not the ref of any node in graph.nodes"
                )
        source = edge.get("source")
        source_port = edge.get("source_port")
        if node_type.get(source) == WorkflowNode.Type.LOOP:
            if source_port not in ("each", "done"):
                raise WorkflowImportError(
                    f"graph.edges[{index}].source_port must be 'each' or "
                    f"'done' on edges leaving loop node '{source}'"
                )
        elif source_port is not None:
            raise WorkflowImportError(
                f"graph.edges[{index}].source_port is only valid on edges "
                "leaving a loop node"
            )
        is_condition = node_type.get(source) == WorkflowNode.Type.CONDITION
        source_branch = edge.get("source_branch")
        if source_branch is None:
            if is_condition:
                raise WorkflowImportError(
                    f"Edge from condition node '{source}' has no source_branch"
                )
        else:
            if not is_condition:
                raise WorkflowImportError(
                    f"Edge from '{source}' carries a source_branch but its source "
                    "is not a condition node"
                )
            if isinstance(source_branch, str):
                if source_branch not in branch_names_by_ref.get(source, []):
                    raise WorkflowImportError(
                        f"Edge from '{source}' references branch "
                        f"{source_branch!r}, which is not a branch name of "
                        "that node"
                    )
            elif (
                not isinstance(source_branch, int)
                or isinstance(source_branch, bool)
                or not 0 <= source_branch < branch_count.get(source, 0)
            ):
                raise WorkflowImportError(
                    f"Edge from '{source}' references branch {source_branch!r} "
                    "outside the node's branch list (use the branch name or a "
                    "0-based index)"
                )


def _validate_condition_group(group, variable_keys, depth):
    if depth > MAX_CONDITION_DEPTH:
        raise WorkflowImportError("Condition groups are nested too deeply")
    if not isinstance(group, dict):
        raise WorkflowImportError("Every condition group must be a mapping")
    for condition in group.get("conditions") or []:
        if not isinstance(condition, dict):
            raise WorkflowImportError("Every condition must be a mapping")
        if condition.get("variable") not in variable_keys:
            raise WorkflowImportError(
                f"Condition references unknown variable {condition.get('variable')!r}"
            )
    for child in group.get("children") or []:
        _validate_condition_group(child, variable_keys, depth + 1)


def _free_name(model, name, folder):
    candidate, suffix = name, 2
    while model.objects.filter(folder=folder, name__iexact=candidate).exists():
        candidate = f"{name} ({suffix})"
        suffix += 1
    return candidate


def _build_graph_payload(graph, workflow, folder, warnings):
    from .actions import _accessible_folder_ids

    accessible = _accessible_folder_ids(folder)
    variable_ids = {v["key"]: str(uuid4()) for v in graph.get("variables") or []}
    node_ids = {n["ref"]: str(uuid4()) for n in graph["nodes"]}
    # (node ref, branch index) → fresh branch uuid, so edges can resolve their
    # source_branch index to the branch built on the node.
    branch_ids = {
        (n["ref"], i): str(uuid4())
        for n in graph["nodes"]
        for i, _ in enumerate(n.get("branches") or [])
    }

    variables = []
    variable_types = set(WorkflowVariable.Type.values)
    for entry in graph.get("variables") or []:
        variables.append(
            {
                "id": variable_ids[entry["key"]],
                "key": entry["key"],
                "type": entry.get("type")
                if entry.get("type") in variable_types
                else WorkflowVariable.Type.STRING,
                "default_value": entry.get("default_value"),
            }
        )

    nodes = [
        _build_node(
            entry, node_ids, branch_ids, variable_ids, workflow, accessible, warnings
        )
        for entry in graph["nodes"]
    ]

    branch_positions = {
        n["ref"]: [str(b.get("name") or "").strip() for b in (n.get("branches") or [])]
        for n in graph["nodes"]
    }

    edges = []
    for entry in graph.get("edges") or []:
        source_branch = entry.get("source_branch")
        if isinstance(source_branch, str):
            source_branch = branch_positions[entry["source"]].index(source_branch)
        edges.append(
            {
                "id": str(uuid4()),
                "source": node_ids[entry["source"]],
                "target": node_ids[entry["target"]],
                "source_branch": branch_ids.get((entry["source"], source_branch))
                if source_branch is not None
                else None,
                "label": str(entry.get("label") or ""),
                "source_port": str(entry.get("source_port") or ""),
            }
        )

    return {"variables": variables, "nodes": nodes, "edges": edges}


def _build_node(
    entry, node_ids, branch_ids, variable_ids, workflow, accessible, warnings
):
    ref = entry["ref"]
    node = {
        "id": node_ids[ref],
        "ref": ref,
        "type": entry["type"],
        "label": str(entry.get("label") or ""),
        "join_type": entry.get("join_type")
        if entry.get("join_type") in WorkflowNode.JoinType.values
        else WorkflowNode.JoinType.NONE,
        "event_key": str(entry.get("event_key") or ""),
    }
    branches = []
    for i, branch in enumerate(entry.get("branches") or []):
        branches.append(
            {
                "id": branch_ids[(ref, i)],
                "name": str(branch.get("name") or ""),
                "order": i,
                "is_default": bool(branch.get("is_default")),
                "condition_groups": [
                    _build_condition_group(group, variable_ids)
                    for group in branch.get("condition_groups") or []
                ],
            }
        )
    if branches:
        node["branches"] = branches
    for field in NODE_JSON_FIELDS:
        value = entry.get(field)
        node[field] = value if isinstance(value, dict) else {}
    retry = entry.get("retry")
    if isinstance(retry, dict) and retry.get("max_attempts"):
        node["retry_max_attempts"] = retry["max_attempts"]
        node["retry_delay_seconds"] = retry.get("delay_seconds", 60)
        node["retry_backoff"] = retry.get("backoff", WorkflowNode.RetryBackoff.FIXED)

    if entry.get("task_template"):
        node["task_template"] = _resolve_by_name(
            _task_template_qs(accessible),
            entry["task_template"],
            f"node '{ref}': task template",
            warnings,
        )
    if entry.get("subprocess_workflow"):
        node["subprocess_workflow"] = _resolve_by_name(
            Workflow.objects.filter(folder_id__in=accessible).exclude(id=workflow.id),
            entry["subprocess_workflow"],
            f"node '{ref}': subprocess workflow",
            warnings,
        )

    assignments = []
    for assignment in entry.get("assignments") or []:
        built = _build_assignment(assignment, ref, warnings)
        if built:
            assignments.append(built)
    if assignments:
        node["assignments"] = assignments

    presentation = entry.get("presentation")
    if isinstance(presentation, dict) and presentation:
        node["presentation"] = presentation

    # Folder ids inside internal-event trigger filters are instance-specific:
    # keep only values that resolve in this workflow's scope.
    trigger_config = node.get("trigger_config") or {}
    if (
        entry.get("type") == WorkflowNode.Type.TRIGGER
        and trigger_config.get("type") == WorkflowNode.TriggerType.INTERNAL_EVENT
        and trigger_config.get("filters")
    ):
        node["trigger_config"] = {
            **trigger_config,
            "filters": _strip_foreign_folder_filters(
                trigger_config["filters"], workflow, f"node '{ref}'", warnings
            ),
        }
    return node


def _task_template_qs(accessible):
    from core.models import TaskTemplate

    return TaskTemplate.objects.filter(folder_id__in=accessible)


def _resolve_by_name(queryset, name, label, warnings):
    matches = list(queryset.filter(name__iexact=str(name))[:2])
    if len(matches) == 1:
        return str(matches[0].id)
    reason = "no match" if not matches else "several matches"
    warnings.append(
        f"{label} '{name}' could not be resolved ({reason}) — re-select it in the builder"
    )
    return None


def _build_assignment(assignment, ref, warnings):
    from pmbok.models import ResponsibilityRole

    role_spec = assignment.get("role") if isinstance(assignment, dict) else None
    role = None
    if isinstance(role_spec, dict):
        role = (
            ResponsibilityRole.objects.filter(
                taxonomy=role_spec.get("taxonomy"),
                code__iexact=str(role_spec.get("code") or ""),
            )
            .order_by("-builtin", "created_at")
            .first()
        )
    if role is None:
        warnings.append(
            f"node '{ref}': assignment role {role_spec!r} not found — assignment dropped"
        )
        return None
    resolve_type = assignment.get("resolve_type") or "actor"
    if resolve_type == "actor":
        warnings.append(
            f"node '{ref}': assignees are not exported — re-select one in the builder"
        )
    return {
        "role": str(role.id),
        "actor": None,
        "resolve_type": resolve_type,
        "variable_key": str(assignment.get("variable_key") or ""),
        "is_blocking": bool(assignment.get("is_blocking", True)),
        "participation": assignment.get("participation") or "task",
    }


def _build_condition_group(group, variable_ids):
    out = {
        "operator": group.get("operator", "and"),
        "order": group.get("order") or 0,
        "conditions": [
            {
                "variable": variable_ids[condition["variable"]],
                "op": condition.get("op", "eq"),
                "value": str(condition.get("value") or ""),
                "order": condition.get("order") or 0,
            }
            for condition in group.get("conditions") or []
        ],
        "children": [
            _build_condition_group(child, variable_ids)
            for child in group.get("children") or []
        ],
    }
    return out


def _strip_foreign_folder_filters(filters, workflow, label, warnings):
    """Folder conditions carry folder ids from the source instance; keep only
    values that exist in this workflow's scope, dropping the condition (and any
    emptied group) when nothing survives. Trees without folder conditions pass
    through untouched (pruning normalizes the shape, which would break
    round-trip fidelity)."""
    from .events import _workflow_scope, walk_conditions

    if not isinstance(filters, dict) or not filters:
        return filters if isinstance(filters, dict) else {}
    if not any(
        isinstance(c, dict) and c.get("field") == "folder"
        for c in walk_conditions(filters)
    ):
        return filters
    scope = _workflow_scope(workflow)

    def prune(group):
        if not isinstance(group, dict):
            return None
        conditions = []
        for condition in group.get("conditions") or []:
            if (
                isinstance(condition, dict)
                and condition.get("field") == "folder"
                and condition.get("op", "eq") in ("eq", "in")
            ):
                values = [
                    v.strip()
                    for v in str(condition.get("value", "")).split(",")
                    if v.strip()
                ]
                kept = [v for v in values if v in scope]
                if kept != values:
                    warnings.append(
                        f"{label}: folder filter referenced folders that do "
                        "not exist here — condition adjusted"
                    )
                if not kept:
                    continue
                condition = {**condition, "value": ",".join(kept)}
            conditions.append(condition)
        children = [prune(child) for child in group.get("children") or []]
        children = [child for child in children if child is not None]
        if not conditions and not children:
            return None
        out = {**group, "conditions": conditions, "children": children}
        return out

    pruned = prune(filters)
    return pruned or {}


def _post_import_warnings(data, workflow, folder, warnings):
    from .actions import _accessible_folder_ids

    accessible = _accessible_folder_ids(folder)
    configs = {
        node["ref"]: node.get("action_config") or {}
        for node in data["graph"]["nodes"]
        if isinstance(node.get("action_config"), dict)
    }

    declared = data.get("requires") or {}
    needed = set(declared.get("secrets") or []) | set(
        SECRET_NAME_RE.findall(json.dumps(list(configs.values())))
    )
    if needed:
        existing = set(
            WorkflowSecret.objects.filter(
                folder_id__in=accessible, name__in=needed
            ).values_list("name", flat=True)
        )
        missing = sorted(needed - existing)
        if missing:
            warnings.append(
                "Missing secrets: "
                + ", ".join(missing)
                + " — create them before running the workflow"
            )

    for ref, config in configs.items():
        if config and UUID_RE.search(json.dumps(config)):
            warnings.append(
                f"node '{ref}' config contains ids from the source instance — "
                "review it before publishing"
            )
