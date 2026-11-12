"""Tool arguments that go into an API path stay one path segment: a "/" or
".." would send the call to another route."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp.tools import library_tools, read_tools  # noqa: E402


@pytest.mark.parametrize("task_id", ["../../iam/auth-tokens", "abc", ""])
def test_a_task_template_id_must_be_a_uuid(task_id):
    with patch.object(read_tools, "make_get_request") as get:
        answer = asyncio.run(read_tools.get_task_template_details(task_id))
    get.assert_not_called()
    assert answer.startswith("Error")


@pytest.mark.parametrize("urn", ["../../folders/x", "a/b", ""])
def test_a_library_urn_stays_in_its_route(urn):
    with patch.object(library_tools, "make_post_request") as post:
        answer = asyncio.run(library_tools.import_stored_library(urn))
    post.assert_not_called()
    assert answer.startswith("Error")


def test_a_library_urn_is_accepted():
    with patch.object(library_tools, "make_post_request") as post:
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"status": "success"}
        asyncio.run(
            library_tools.import_stored_library(
                "urn:intuitem:risk:library:nist-csf-2.0"
            )
        )
    assert post.call_args.args[0] == (
        "/stored-libraries/urn:intuitem:risk:library:nist-csf-2.0/import/"
    )


# 36 characters with a "-": what the old "is it a UUID?" test let through
TRAVERSAL = "../../iam/auth-tokens/aaaaaaaaaaa-aa"


def _single_argument_resolvers():
    import inspect

    from ca_mcp import resolvers

    for name, fn in inspect.getmembers(resolvers, inspect.isfunction):
        if not name.startswith("resolve_") or fn.__module__ != resolvers.__name__:
            continue
        required = [
            p
            for p in inspect.signature(fn).parameters.values()
            if p.default is inspect.Parameter.empty
        ]
        if len(required) == 1:
            yield name, fn


def test_the_traversal_value_has_the_old_uuid_shape():
    assert len(TRAVERSAL) == 36 and "-" in TRAVERSAL


@pytest.mark.parametrize(
    "name,resolve", list(_single_argument_resolvers()), ids=lambda v: str(v)
)
def test_a_resolver_never_passes_a_path_through(name, resolve):
    from ca_mcp import resolvers

    nothing = type("R", (), {"status_code": 200, "json": lambda self: {"results": []}})
    with (
        patch.object(resolvers, "fetch_all_results", return_value=([], None)),
        patch.object(resolvers, "make_get_request", return_value=nothing()),
    ):
        try:
            resolved = resolve(TRAVERSAL)
        except ValueError, KeyError, TypeError:
            return
    assert resolved != TRAVERSAL


def test_no_tool_guesses_a_uuid_from_its_length():
    import re

    tools = Path(__file__).parents[2] / "ca_mcp"
    guess = re.compile(r"len\([^)]*\)\s*==\s*36")
    found = [
        f"{path.name}:{number}"
        for path in tools.rglob("*.py")
        for number, line in enumerate(path.read_text().splitlines(), 1)
        if guess.search(line)
    ]
    assert not found, "use _is_uuid instead"
