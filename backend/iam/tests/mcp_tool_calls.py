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


def tool_calls() -> set[tuple[str, str]]:
    """(method, path) pairs, with "{}" wherever the path takes a value."""
    calls = set()
    for source in sorted(CA_MCP.rglob("*.py")):
        tree = ast.parse(source.read_text())
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if function.name in LOCAL_ONLY:
                continue
            strings = _local_strings(function)
            for node in ast.walk(function):
                if not isinstance(node, ast.Call):
                    continue
                name = getattr(node.func, "id", None) or getattr(
                    node.func, "attr", None
                )
                if name in METHOD_OF:
                    for path in _path(node.args[0], strings) if node.args else []:
                        calls.add((METHOD_OF[name], path))
                    continue
                # resolvers take the collection to search as an argument
                for arg in node.args:
                    for path in _path(arg, {}):
                        if _is_api_path(path) and not path.startswith("/" + ANY):
                            calls.add(("GET", path))
    for collection in _objects_registry():
        calls.add(("GET", f"/{collection}/"))
        calls.add(("GET", f"/{collection}/{ANY}/"))
    # generic placeholders are expanded above
    return {
        (method, path)
        for method, path in calls
        if _is_api_path(path) and not path.startswith("/" + ANY)
    }
