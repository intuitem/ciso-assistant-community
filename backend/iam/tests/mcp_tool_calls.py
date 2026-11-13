"""The API calls the ca_mcp tools make, read from their source: the MCP
listener's inventory must cover each of them, and nothing else."""

import ast
from pathlib import Path

from django.conf import settings

CA_MCP = Path(settings.BASE_DIR).parent / "cli" / "ca_mcp"

METHOD_OF = {
    "make_get_request": "GET",
    "fetch_all_results": "GET",
    "make_post_request": "POST",
    "make_patch_request": "PATCH",
    "make_delete_request": "DELETE",
    "make_upload_request": "POST",
}

# offered only to a local user with a PAT, never through the MCP server, and
# the helpers only they call
LOCAL_ONLY = {
    "create_evidence",
    "_delete_evidence_quietly",
    "create_folder",
    "update_folder",
    "update_user",
}

ANY = "{}"


def _path(node, strings):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return [
            "".join(
                part.value if isinstance(part, ast.Constant) else ANY
                for part in node.values
            )
        ]
    if isinstance(node, ast.Name):
        return strings.get(node.id, [])
    return []


def _local_strings(function) -> dict[str, list[str]]:
    """Paths a function puts in a variable, directly or by looping over pairs."""
    found: dict[str, list[str]] = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                found.setdefault(target.id, []).extend(_path(node.value, {}))
        if isinstance(node, ast.For) and isinstance(node.iter, (ast.Tuple, ast.List)):
            names = (
                [t.id for t in node.target.elts if isinstance(t, ast.Name)]
                if isinstance(node.target, ast.Tuple)
                else [node.target.id]
                if isinstance(node.target, ast.Name)
                else []
            )
            for item in node.iter.elts:
                values = item.elts if isinstance(item, ast.Tuple) else [item]
                for name, value in zip(names, values):
                    found.setdefault(name, []).extend(_path(value, {}))
    return found


def _objects_registry() -> list[str]:
    tree = ast.parse((CA_MCP / "tools" / "generic_tools.py").read_text())
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and getattr(node.targets[0], "id", None) == "OBJECTS"
        ):
            return [value.value for value in node.value.values]
    raise AssertionError("OBJECTS not found in generic_tools")


def _is_api_path(text: str) -> bool:
    return text.startswith("/") and text.endswith("/") and len(text) > 2


def _functions():
    """Every function of ca_mcp, nested ones included."""
    for source in sorted(CA_MCP.rglob("*.py")):
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield node


def _called(node) -> str | None:
    return getattr(node.func, "id", None) or getattr(node.func, "attr", None)


def _calls_in(function) -> set[tuple[str, str]]:
    """The API calls written in one function."""
    calls = set()
    strings = _local_strings(function)
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        name = _called(node)
        if name in METHOD_OF:
            for path in _path(node.args[0], strings) if node.args else []:
                calls.add((METHOD_OF[name], path))
            continue
        # resolvers take the collection to search as an argument
        for arg in node.args:
            for path in _path(arg, {}):
                if _is_api_path(path) and not path.startswith("/" + ANY):
                    calls.add(("GET", path))
    return calls


def _concrete(calls) -> set[tuple[str, str]]:
    # generic placeholders ("/{}/") are expanded from the objects registry
    return {
        (method, path)
        for method, path in calls
        if _is_api_path(path) and not path.startswith("/" + ANY)
    }


def tool_calls() -> set[tuple[str, str]]:
    """(method, path) pairs, with "{}" wherever the path takes a value."""
    calls = set()
    for function in _functions():
        if function.name not in LOCAL_ONLY:
            calls |= _calls_in(function)
    for collection in _objects_registry():
        calls.add(("GET", f"/{collection}/"))
        calls.add(("GET", f"/{collection}/{ANY}/"))
    return _concrete(calls)


TOOL_LISTS = {
    "READ_TOOLS": "read",
    "CREATE_TOOLS": "create",
    "UPDATE_TOOLS": "update",
    "DELETE_TOOLS": "delete",
}


def tool_actions() -> dict[str, set[str]]:
    """The actions each tool needs, as cli/ca_mcp/server.py declares them: the
    one of its list, plus what ALSO_NEEDS adds."""
    tree = ast.parse((CA_MCP / "server.py").read_text())
    assigned = {
        node.targets[0].id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }
    needed = {
        tool.id: {action}
        for constant, action in TOOL_LISTS.items()
        for tool in assigned[constant].elts
    }
    # ALSO_NEEDS = {tool.__name__: {actions.CREATE}}
    also = assigned["ALSO_NEEDS"]
    for tool, extra in zip(also.keys, also.values):
        needed[tool.value.id] |= {action.attr.lower() for action in extra.elts}
    return needed


def calls_by_tool() -> dict[str, set[tuple[str, str]]]:
    """The calls of each tool the MCP server offers: its own, and those of the
    ca_mcp functions it calls by name (resolvers, helpers)."""
    functions: dict[str, list] = {}
    for function in _functions():
        functions.setdefault(function.name, []).append(function)

    def reach(name, seen):
        if name in seen or name in LOCAL_ONLY:
            return set()
        seen.add(name)
        calls = set()
        for function in functions.get(name, []):
            calls |= _calls_in(function)
            for node in ast.walk(function):
                # plain names only: `.json()` or `.add()` on an object is not
                # the ca_mcp function of that name
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in functions
                ):
                    calls |= reach(node.func.id, seen)
        return calls

    return {
        tool: _concrete(reach(tool, set()))
        for tool in tool_actions()
        if tool not in LOCAL_ONLY
    }
