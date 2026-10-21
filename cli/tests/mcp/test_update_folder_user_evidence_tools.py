"""Unit tests for the update_folder, update_user and update_evidence MCP tools.

Network calls are mocked at their import sites (ca_mcp.resolvers.*,
ca_mcp.tools.update_tools.*).
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import resolvers  # noqa: E402
from ca_mcp.tools import update_tools  # noqa: E402

UUID_A = "11111111-1111-1111-1111-111111111111"
UUID_B = "22222222-2222-2222-2222-222222222222"


def _response(status_code=200, json_data=None, text=""):
    res = Mock()
    res.status_code = status_code
    res.json.return_value = json_data if json_data is not None else {}
    res.text = text
    return res


def _patch_ok(body=None):
    return patch.object(
        update_tools,
        "make_patch_request",
        return_value=_response(200, body or {"id": UUID_A, "name": "x"}),
    )


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# resolve_evidence_id
# ---------------------------------------------------------------------------


class TestResolveEvidenceId:
    def test_uuid_passthrough(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_evidence_id(UUID_A) == UUID_A
        fetch.assert_not_called()

    def test_name_lookup(self):
        with patch.object(
            resolvers,
            "fetch_all_results",
            return_value=([{"id": UUID_A, "name": "Policy.pdf"}], None),
        ) as fetch:
            assert resolvers.resolve_evidence_id("Policy.pdf") == UUID_A
        fetch.assert_called_once_with("/evidences/", params={"name": "Policy.pdf"})

    def test_not_found(self):
        with (
            patch.object(resolvers, "fetch_all_results", return_value=([], None)),
            pytest.raises(ValueError, match="not found"),
        ):
            resolvers.resolve_evidence_id("Nope")

    def test_ambiguous(self):
        with (
            patch.object(
                resolvers,
                "fetch_all_results",
                return_value=(
                    [
                        {"id": UUID_A, "name": "Dup", "folder": {"str": "Legal"}},
                        {"id": UUID_B, "name": "Dup", "folder": {"str": "HR"}},
                    ],
                    None,
                ),
            ),
            pytest.raises(ValueError, match="Ambiguous") as exc,
        ):
            resolvers.resolve_evidence_id("Dup")
        message = str(exc.value)
        assert UUID_A in message
        assert UUID_B in message
        assert "Legal" in message
        assert "HR" in message

    @pytest.mark.parametrize("ref", ["", "   "])
    def test_blank_reference(self, ref):
        with (
            patch.object(resolvers, "fetch_all_results") as fetch,
            pytest.raises(ValueError, match="Evidence reference is empty"),
        ):
            resolvers.resolve_evidence_id(ref)
        fetch.assert_not_called()

    def test_strips_reference(self):
        with patch.object(
            resolvers,
            "fetch_all_results",
            return_value=([{"id": UUID_A, "name": "Policy.pdf"}], None),
        ) as fetch:
            assert resolvers.resolve_evidence_id("  Policy.pdf ") == UUID_A
        fetch.assert_called_once_with("/evidences/", params={"name": "Policy.pdf"})

    def test_api_error(self):
        with (
            patch.object(resolvers, "fetch_all_results", return_value=([], "boom")),
            pytest.raises(ValueError, match="API error"),
        ):
            resolvers.resolve_evidence_id("Policy.pdf")


class TestResolveFolderId:
    def test_uuid_passthrough(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_folder_id(UUID_A) == UUID_A
        fetch.assert_not_called()

    def test_uuid_shaped_name_is_looked_up(self):
        # 36 chars with hyphens, but not a valid UUID: must resolve by name.
        name = "my-folder-name-that-is-36-chars-long"
        assert len(name) == 36
        with patch.object(
            resolvers,
            "fetch_all_results",
            return_value=([{"id": UUID_B, "name": name}], None),
        ) as fetch:
            assert resolvers.resolve_folder_id(name) == UUID_B
        fetch.assert_called_once_with("/folders/", params={"name": name})


# ---------------------------------------------------------------------------
# update_folder
# ---------------------------------------------------------------------------


class TestUpdateFolder:
    def test_payload(self):
        with (
            _patch_ok({"id": UUID_A, "name": "Legal FR"}) as patch_req,
            patch.object(
                update_tools, "resolve_folder_id", return_value=UUID_A
            ) as resolve_folder,
        ):
            result = run(update_tools.update_folder("Legal", name="Legal FR"))
        resolve_folder.assert_called_once_with("Legal")
        assert result == f"Updated folder: Legal FR (ID: {UUID_A})"
        assert patch_req.call_args.args == (f"/folders/{UUID_A}/", {"name": "Legal FR"})

    def test_description_only(self):
        with (
            _patch_ok() as patch_req,
            patch.object(update_tools, "resolve_folder_id", return_value=UUID_A),
        ):
            run(update_tools.update_folder(UUID_A, description="Legal team"))
        assert patch_req.call_args.args[1] == {"description": "Legal team"}

    def test_no_fields(self):
        with (
            _patch_ok() as patch_req,
            patch.object(update_tools, "resolve_folder_id", return_value=UUID_A),
        ):
            result = run(update_tools.update_folder(UUID_A))
        patch_req.assert_not_called()
        assert result == "Error: No fields provided to update"

    def test_backend_error(self):
        with (
            patch.object(
                update_tools,
                "make_patch_request",
                return_value=_response(403, text="forbidden"),
            ),
            patch.object(update_tools, "resolve_folder_id", return_value=UUID_A),
        ):
            result = run(update_tools.update_folder(UUID_A, name="x"))
        assert result == "Error updating folder: 403 - forbidden"

    def test_resolver_error(self):
        with (
            _patch_ok() as patch_req,
            patch.object(
                update_tools,
                "resolve_folder_id",
                side_effect=ValueError("Folder 'Nope' not found"),
            ),
        ):
            result = run(update_tools.update_folder("Nope", name="x"))
        patch_req.assert_not_called()
        assert result == "Error in update_folder: Folder 'Nope' not found"


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------


class TestUpdateUser:
    def test_payload(self):
        with (
            _patch_ok({"id": UUID_A, "email": "jo@acme.io"}) as patch_req,
            patch.object(
                update_tools, "resolve_user_id", return_value=UUID_A
            ) as resolve_user,
        ):
            result = run(
                update_tools.update_user("jo@acme.io", first_name="Jo", last_name="Doe")
            )
        resolve_user.assert_called_once_with("jo@acme.io")
        assert result == f"Updated user: jo@acme.io (ID: {UUID_A})"
        assert patch_req.call_args.args == (
            f"/users/{UUID_A}/",
            {"first_name": "Jo", "last_name": "Doe"},
        )

    def test_email_only(self):
        with (
            _patch_ok() as patch_req,
            patch.object(update_tools, "resolve_user_id", return_value=UUID_A),
        ):
            run(update_tools.update_user(UUID_A, email="new@acme.io"))
        assert patch_req.call_args.args[1] == {"email": "new@acme.io"}

    def test_no_fields(self):
        with (
            _patch_ok() as patch_req,
            patch.object(update_tools, "resolve_user_id", return_value=UUID_A),
        ):
            result = run(update_tools.update_user(UUID_A))
        patch_req.assert_not_called()
        assert result == "Error: No fields provided to update"

    def test_backend_error(self):
        with (
            patch.object(
                update_tools,
                "make_patch_request",
                return_value=_response(400, text='{"email": ["invalid"]}'),
            ),
            patch.object(update_tools, "resolve_user_id", return_value=UUID_A),
        ):
            result = run(update_tools.update_user(UUID_A, email="bad"))
        assert result == 'Error updating user: 400 - {"email": ["invalid"]}'

    def test_resolver_error(self):
        with (
            _patch_ok() as patch_req,
            patch.object(
                update_tools,
                "resolve_user_id",
                side_effect=ValueError("Ambiguous user 'Jo'"),
            ),
        ):
            result = run(update_tools.update_user("Jo", first_name="Joe"))
        patch_req.assert_not_called()
        assert result == "Error in update_user: Ambiguous user 'Jo'"


# ---------------------------------------------------------------------------
# update_evidence
# ---------------------------------------------------------------------------


class TestUpdateEvidence:
    def test_move_to_folder(self):
        with (
            _patch_ok({"id": UUID_A, "name": "Policy.pdf"}) as patch_req,
            patch.object(
                update_tools, "resolve_evidence_id", return_value=UUID_A
            ) as resolve_evidence,
            patch.object(
                update_tools, "resolve_folder_id", return_value=UUID_B
            ) as resolve_folder,
        ):
            result = run(update_tools.update_evidence("Policy.pdf", folder_id="Legal"))
        resolve_evidence.assert_called_once_with("Policy.pdf")
        resolve_folder.assert_called_once_with("Legal")
        assert result == f"Updated evidence: Policy.pdf (ID: {UUID_A})"
        assert patch_req.call_args.args == (
            f"/evidences/{UUID_A}/",
            {"folder": UUID_B},
        )

    def test_name_and_description(self):
        with (
            _patch_ok() as patch_req,
            patch.object(update_tools, "resolve_evidence_id", return_value=UUID_A),
        ):
            run(update_tools.update_evidence(UUID_A, name="New", description="Desc"))
        assert patch_req.call_args.args[1] == {"name": "New", "description": "Desc"}

    def test_no_fields(self):
        with (
            _patch_ok() as patch_req,
            patch.object(update_tools, "resolve_evidence_id", return_value=UUID_A),
        ):
            result = run(update_tools.update_evidence(UUID_A))
        patch_req.assert_not_called()
        assert result == "Error: No fields provided to update"

    def test_backend_error(self):
        with (
            patch.object(
                update_tools,
                "make_patch_request",
                return_value=_response(403, text="forbidden"),
            ),
            patch.object(update_tools, "resolve_evidence_id", return_value=UUID_A),
        ):
            result = run(update_tools.update_evidence(UUID_A, name="x"))
        assert result == "Error updating evidence: 403 - forbidden"

    def test_unknown_evidence(self):
        with (
            _patch_ok() as patch_req,
            patch.object(resolvers, "fetch_all_results", return_value=([], None)),
        ):
            result = run(update_tools.update_evidence("Nope", name="x"))
        patch_req.assert_not_called()
        assert result == "Error in update_evidence: Evidence 'Nope' not found"

    def test_unknown_folder(self):
        with (
            _patch_ok() as patch_req,
            patch.object(update_tools, "resolve_evidence_id", return_value=UUID_A),
            patch.object(
                update_tools,
                "resolve_folder_id",
                side_effect=ValueError("Folder 'Nope' not found"),
            ),
        ):
            result = run(update_tools.update_evidence(UUID_A, folder_id="Nope"))
        patch_req.assert_not_called()
        assert result == "Error in update_evidence: Folder 'Nope' not found"


# ---------------------------------------------------------------------------
# server registration
# ---------------------------------------------------------------------------

NEW_TOOLS = {"update_folder", "update_user", "update_evidence"}


class TestRegistration:
    def _tools(self, read_only):
        from mcp.server.mcpserver import MCPServer

        import ca_mcp.server as server

        fresh = MCPServer("test")
        with (
            patch.object(server, "mcp", fresh),
            patch.object(server, "_registered", False),
        ):
            server.register_tools(read_only=read_only)
            tools = asyncio.run(fresh.list_tools())
        return {t.name: t for t in tools}

    def test_full_profile_exposes_tools_as_destructive(self):
        tools = self._tools(read_only=False)
        assert NEW_TOOLS <= set(tools)
        for name in NEW_TOOLS:
            ann = tools[name].annotations
            assert ann.read_only_hint is False
            assert ann.destructive_hint is True
            assert ann.idempotent_hint is True

    def test_read_only_profile_hides_tools(self):
        tools = self._tools(read_only=True)
        assert not NEW_TOOLS & set(tools)
