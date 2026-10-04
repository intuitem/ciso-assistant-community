"""Unit tests for the MCP asset tools: objectives/capabilities, durations, security gaps.

Network calls are mocked at their import sites, as in
test_risk_review_tools.py.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import resolvers  # noqa: E402
from ca_mcp.tools import (  # noqa: E402
    read_tools,
    update_tools,
    write_tools,
)
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    UUID_B,
    UUID_D,
    UUID_F,
    _response,
    _router,
    run,
)


def _obj(value, enabled=True):
    return {"value": value, "is_enabled": enabled}


# Stored asset as returned by GET /assets/{id}/object/
STORED_PR = {
    "id": UUID_A,
    "name": "ERP",
    "type": "PR",
    "description": "",
    "observation": "Initial note",
    "security_objectives": {
        "objectives": {
            "confidentiality": _obj(3),
            "integrity": _obj(2),
            "availability": _obj(1, False),
            "proof": _obj(4),
            "authenticity": _obj(0, False),
            "privacy": _obj(1),
            "safety": _obj(2),
        }
    },
    "disaster_recovery_objectives": {
        "objectives": {"rto": {"value": 3600}, "rpo": {"value": 600}}
    },
    "security_capabilities": {},
    "recovery_capabilities": {},
}

STORED_SP = {
    "id": UUID_A,
    "name": "DB server",
    "type": "SP",
    "description": "",
    "observation": "",
    "security_objectives": {},
    "disaster_recovery_objectives": {},
    "security_capabilities": {
        "objectives": {"confidentiality": _obj(1), "integrity": _obj(3)}
    },
    "recovery_capabilities": {"objectives": {"rpo": {"value": 60}}},
}


# ---------------------------------------------------------------------------
# parse_duration
# ---------------------------------------------------------------------------


class TestParseDuration:
    @pytest.mark.parametrize(
        "given,seconds",
        [
            (900, 900),
            ("90s", 90),
            ("30m", 1800),
            ("2h", 7200),
            ("1d", 86400),
            ("1h30m", 5400),
            ("1d2h3m4s", 93784),
            ("1h 30m", 5400),
            (" 1d 2h ", 93600),
            ("600", 600),
        ],
    )
    def test_accepted(self, given, seconds):
        assert resolvers.parse_duration(given) == seconds

    @pytest.mark.parametrize(
        "given", ["2 hours", "2 h ours", "-1h", "h", "", "1.5h", "30m 1h", -5, True]
    )
    def test_rejected(self, given):
        with pytest.raises(ValueError) as exc:
            resolvers.parse_duration(given)
        assert "1h30m" in str(exc.value)


# ---------------------------------------------------------------------------
# create_asset
# ---------------------------------------------------------------------------


class TestCreateAsset:
    def _call(self, **kwargs):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "x"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
        ):
            result = run(write_tools.create_asset(**kwargs))
        return result, post

    def test_only_touched_keys_sent(self):
        _, post = self._call(
            name="ERP", sec_confidentiality=3, sec_integrity_enabled=True, dro_rto=900
        )
        assert post.call_args.args == (
            "/assets/",
            {
                "name": "ERP",
                "description": "",
                "type": "PR",
                "security_objectives": {
                    "objectives": {
                        "confidentiality": _obj(3),
                        "integrity": _obj(0),
                    }
                },
                "disaster_recovery_objectives": {"objectives": {"rto": {"value": 900}}},
            },
        )

    def test_new_criteria_at_creation(self):
        result, post = self._call(
            name="ERP", asset_type="PR", sec_proof=3, sec_privacy=2
        )
        objectives = post.call_args.args[1]["security_objectives"]["objectives"]
        assert objectives["proof"] == _obj(3)
        assert objectives["privacy"] == _obj(2)
        assert "WARNING" not in result

    @pytest.mark.parametrize("bad", [5, -1, "3", True])
    def test_value_out_of_range_sends_nothing(self, bad):
        result, post = self._call(name="ERP", sec_safety=bad)
        post.assert_not_called()
        assert "sec_safety" in result and "0 and 4" in result

    def test_owner_parents_and_written_durations(self):
        with (
            patch.object(write_tools, "resolve_actor_ids", return_value=[UUID_D]) as ra,
            patch.object(
                write_tools, "resolve_asset_id", return_value=UUID_B
            ) as resolve_asset,
        ):
            _, post = self._call(
                name="DB",
                asset_type="SP",
                owner=["enzo@acme.io"],
                parent_assets=["ERP"],
                dro_rpo="1h30m",
                dro_mtd="1d",
                dro_rto=900,
            )
        ra.assert_called_once_with(["enzo@acme.io"])
        resolve_asset.assert_called_once_with("ERP")
        payload = post.call_args.args[1]
        assert payload["owner"] == [UUID_D]
        assert payload["parent_assets"] == [UUID_B]
        assert payload["disaster_recovery_objectives"]["objectives"] == {
            "rto": {"value": 900},
            "rpo": {"value": 5400},
            "mtd": {"value": 86400},
        }

    def test_bad_duration_sends_nothing(self):
        result, post = self._call(name="ERP", dro_rto="2 hours")
        post.assert_not_called()
        assert "1h30m" in result

    def test_capabilities_on_primary_warn(self):
        result, post = self._call(
            name="ERP", asset_type="PR", cap_integrity=2, rcap_rto="2h"
        )
        payload = post.call_args.args[1]
        assert payload["security_capabilities"] == {
            "objectives": {"integrity": _obj(2)}
        }
        # no rpo/mtd defaults on capabilities: only the touched key is sent
        assert payload["recovery_capabilities"] == {
            "objectives": {"rto": {"value": 7200}}
        }
        assert "disaster_recovery_objectives" not in payload
        warning = result.splitlines()[-1]
        assert warning.startswith("WARNING")
        assert "security_capabilities" in warning
        assert "recovery_capabilities" in warning

    def test_objectives_on_supporting_warn(self):
        result, _ = self._call(name="DB", asset_type="SP", sec_confidentiality=2)
        assert "security_objectives" in result.splitlines()[-1]


# ---------------------------------------------------------------------------
# update_asset
# ---------------------------------------------------------------------------


class TestUpdateAsset:
    def _call(self, stored=STORED_PR, get_status=200, **kwargs):
        get = Mock(return_value=_response(get_status, stored))
        patch_req = Mock(return_value=_response(200, {"id": UUID_A, "name": "x"}))
        with (
            patch.object(update_tools, "make_get_request", get),
            patch.object(update_tools, "make_patch_request", patch_req),
        ):
            result = run(update_tools.update_asset(asset_id=UUID_A, **kwargs))
        return result, get, patch_req

    def test_partial_update_keeps_stored_values(self):
        _, get, patch_req = self._call(sec_integrity=4, dro_mtd="1d")
        get.assert_called_once_with(f"/assets/{UUID_A}/object/")
        payload = patch_req.call_args.args[1]
        objectives = payload["security_objectives"]["objectives"]
        expected = dict(STORED_PR["security_objectives"]["objectives"])
        expected["integrity"] = _obj(4)
        assert objectives == expected
        assert payload["disaster_recovery_objectives"]["objectives"] == {
            "rto": {"value": 3600},
            "rpo": {"value": 600},
            "mtd": {"value": 86400},
        }
        assert "security_capabilities" not in payload

    def test_explicit_disable(self):
        _, _, patch_req = self._call(sec_safety_enabled=False)
        objectives = patch_req.call_args.args[1]["security_objectives"]["objectives"]
        assert objectives["safety"] == _obj(2, False)
        assert objectives["confidentiality"] == _obj(3)
        assert objectives["proof"] == _obj(4)

    def test_value_without_flag_enables(self):
        _, _, patch_req = self._call(sec_availability=2)
        objectives = patch_req.call_args.args[1]["security_objectives"]["objectives"]
        assert objectives["availability"] == _obj(2)

    def test_fetch_failure_sends_nothing(self):
        result, _, patch_req = self._call(get_status=500, sec_integrity=4)
        patch_req.assert_not_called()
        assert "Error" in result and "nothing sent" in result

    def test_capabilities_on_supporting(self):
        result, _, patch_req = self._call(
            stored=STORED_SP, cap_confidentiality=2, rcap_rto="2h"
        )
        payload = patch_req.call_args.args[1]
        assert payload["security_capabilities"]["objectives"] == {
            "confidentiality": _obj(2),
            "integrity": _obj(3),
        }
        assert payload["recovery_capabilities"]["objectives"] == {
            "rpo": {"value": 60},
            "rto": {"value": 7200},
        }
        assert "WARNING" not in result

    def test_capabilities_on_primary_warn_with_stored_type(self):
        result, _, _ = self._call(cap_integrity=1)
        assert result.splitlines()[-1].startswith("WARNING")
        assert "security_capabilities" in result.splitlines()[-1]

    def test_asset_type_param_wins_over_stored_type(self):
        result, _, _ = self._call(asset_type="SP", sec_integrity=1)
        assert "security_objectives" in result.splitlines()[-1]

    def test_bad_value_sends_nothing(self):
        result, get, patch_req = self._call(cap_proof=7)
        get.assert_not_called()
        patch_req.assert_not_called()
        assert "cap_proof" in result

    def test_no_objective_param_no_fetch(self):
        _, get, patch_req = self._call(name="ERP v2")
        get.assert_not_called()
        assert patch_req.call_args.args[1] == {"name": "ERP v2"}

    def test_text_field_sent_without_fetch(self):
        _, get, patch_req = self._call(observation="new")
        get.assert_not_called()
        assert patch_req.call_args.args[1] == {"observation": "new"}


# ---------------------------------------------------------------------------
# get_asset_security_gaps
# ---------------------------------------------------------------------------


def _detail(asset_id, name, security, recovery=()):
    return {
        "id": asset_id,
        "name": name,
        "type": "Primary",
        "security_objectives_comparison": [
            {"objective": k, "expectation": e, "reality": r, "verdict": v}
            for k, e, r, v in security
        ],
        "recovery_objectives_comparison": [
            {"objective": k, "expectation": e, "reality": r, "verdict": v}
            for k, e, r, v in recovery
        ],
    }


ERP = _detail(
    UUID_A,
    "ERP",
    [
        ("confidentiality", 3, 2, False),
        ("integrity", 2, 2, True),
        ("availability", 1, None, None),
        ("proof", None, None, None),
    ],
    [("rto", "1h", "2h", False), ("rpo", None, None, None)],
)
CRM = _detail(UUID_B, "CRM", [("confidentiality", 1, 2, True)])


class TestAssetSecurityGaps:
    def _get(self, details, listing=None, list_count=None):
        def fake(endpoint, params=None):
            if endpoint == "/assets/":
                results = listing or []
                return _response(
                    200,
                    {"count": list_count or len(results), "results": results},
                )
            asset_id = endpoint.split("/")[2]
            detail = details[asset_id]
            if isinstance(detail, int):
                return _response(detail, text="Forbidden")
            return _response(200, detail)

        return Mock(side_effect=fake)

    def test_one_asset(self):
        get = self._get({UUID_A: ERP})
        with (
            patch.object(read_tools, "make_get_request", get),
            patch.object(resolvers, "fetch_all_results", _router({"/assets/": [ERP]})),
        ):
            result = run(read_tools.get_asset_security_gaps(asset="ERP"))
        assert "|security|confidentiality|3|2|no|" in result
        assert "|security|integrity|2|2|yes|" in result
        assert "|security|availability|1|--|?|" in result
        assert "|recovery|rto|1h|2h|no|" in result
        assert "proof" not in result
        assert "rpo" not in result

    def test_asset_not_found(self):
        with (
            patch.object(read_tools, "make_get_request") as get,
            patch.object(resolvers, "fetch_all_results", _router({})),
        ):
            result = run(read_tools.get_asset_security_gaps(asset="Nope"))
        get.assert_not_called()
        assert "Asset 'Nope' not found" in result

    def test_folder_only_unmet(self):
        listing = [{"id": UUID_A}, {"id": UUID_B}]
        get = self._get({UUID_A: ERP, UUID_B: CRM}, listing=listing, list_count=120)
        with patch.object(read_tools, "make_get_request", get):
            result = run(
                read_tools.get_asset_security_gaps(folder=UUID_F, only_unmet=True)
            )
        list_call = get.call_args_list[0]
        assert list_call.args[0] == "/assets/"
        assert list_call.kwargs["params"] == {"limit": 50, "folder": UUID_F}
        assert "### ERP" in result
        assert "### CRM" not in result
        assert "2 of 120" in result

    def test_asset_scoped_to_folder(self):
        get = self._get({UUID_A: ERP})
        fake = _router({"/assets/": [ERP]})
        with (
            patch.object(read_tools, "make_get_request", get),
            patch.object(resolvers, "fetch_all_results", fake),
        ):
            run(read_tools.get_asset_security_gaps(asset="ERP", folder=UUID_F))
        assert fake.calls == [("/assets/", {"name": "ERP", "folder": UUID_F})]

    def test_partial_detail_failure(self):
        listing = [{"id": UUID_A}, {"id": UUID_B}]
        get = self._get({UUID_A: ERP, UUID_B: 403}, listing=listing)
        with patch.object(read_tools, "make_get_request", get):
            result = run(read_tools.get_asset_security_gaps(folder=UUID_F))
        assert "[SUCCESS]" in result
        assert "### ERP" in result
        assert "Could not read 1 asset(s)" in result

    def test_all_details_failed(self):
        listing = [{"id": UUID_A}, {"id": UUID_B}]
        get = self._get({UUID_A: 403, UUID_B: 500}, listing=listing)
        with patch.object(read_tools, "make_get_request", get):
            result = run(read_tools.get_asset_security_gaps(folder=UUID_F))
        assert "[ERROR]" in result
        assert "[SUCCESS]" not in result
        assert "0 asset(s)" not in result

    def test_folder_empty(self):
        get = self._get({}, listing=[])
        with patch.object(read_tools, "make_get_request", get):
            result = run(read_tools.get_asset_security_gaps(folder=UUID_F))
        assert "No assets found" in result

    def test_only_unmet_none_unmet(self):
        get = self._get({UUID_B: CRM}, listing=[{"id": UUID_B}])
        with patch.object(read_tools, "make_get_request", get):
            result = run(
                read_tools.get_asset_security_gaps(folder=UUID_F, only_unmet=True)
            )
        assert "No assets with unmet objectives found" in result

    def test_only_unmet_none_unmet_keeps_truncation(self):
        get = self._get({UUID_B: CRM}, listing=[{"id": UUID_B}], list_count=120)
        with patch.object(read_tools, "make_get_request", get):
            result = run(
                read_tools.get_asset_security_gaps(folder=UUID_F, only_unmet=True)
            )
        assert "1 of 120" in result
        assert "No assets with unmet objectives found" in result


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_read_only_profile_has_gaps_tool(self):
        from mcp.server.fastmcp import FastMCP

        import ca_mcp.server as server

        fresh = FastMCP("test")
        with (
            patch.object(server, "mcp", fresh),
            patch.object(server, "_registered", False),
        ):
            server.register_tools(read_only=True)
            tools = asyncio.run(fresh.list_tools())
        names = {t.name for t in tools}
        assert "get_asset_security_gaps" in names
        assert "update_asset" not in names
