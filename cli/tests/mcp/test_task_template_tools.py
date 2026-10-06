"""Unit tests for the MCP task template update tool: asset resolution.

Network calls are mocked at their import sites, as in
test_risk_review_tools.py.
"""

import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp.tools import (  # noqa: E402
    update_tools,
)
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    UUID_C,
    UUID_F,
    _response,
    run,
)


class TestUpdateTaskTemplate:
    def _patch_ok(self):
        return patch.object(
            update_tools,
            "make_patch_request",
            return_value=_response(200, {"id": UUID_A, "name": "T"}),
        )

    def test_assets_resolved_in_folder(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools, "resolve_asset_id", return_value=UUID_C
            ) as resolve_asset,
        ):
            run(
                update_tools.update_task_template(
                    task_id=UUID_A, folder_id=UUID_F, assets=["ERP"]
                )
            )
        resolve_asset.assert_called_once_with("ERP", folder_id=UUID_F)
        assert patch_req.call_args.args[1] == {"folder": UUID_F, "assets": [UUID_C]}

    def test_assets_unscoped_without_folder(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools, "resolve_asset_id", return_value=UUID_C
            ) as resolve_asset,
        ):
            run(update_tools.update_task_template(task_id=UUID_A, assets=["ERP"]))
        resolve_asset.assert_called_once_with("ERP", folder_id=None)
        assert patch_req.call_args.args[1] == {"assets": [UUID_C]}
