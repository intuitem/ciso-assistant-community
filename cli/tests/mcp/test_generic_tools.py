"""Unit tests for the MCP generic list_objects / get_object types.

Network calls are mocked at their import sites, as in
test_risk_review_tools.py.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp.tools import (  # noqa: E402
    generic_tools,
)
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    _response,
    run,
)


class TestListObjectsTypes:
    @pytest.mark.parametrize(
        "object_type,path",
        [
            ("reference_controls", "reference-controls"),
            ("terminologies", "terminologies"),
            ("representatives", "representatives"),
        ],
    )
    def test_registered(self, object_type, path):
        assert generic_tools.OBJECTS[object_type] == path

    def test_list_reference_controls(self):
        get = Mock(
            return_value=_response(
                200, {"count": 1, "results": [{"id": UUID_A, "name": "MFA"}]}
            )
        )
        with patch.object(generic_tools, "make_get_request", get):
            result = run(generic_tools.list_objects("reference_controls"))
        assert get.call_args.args[0] == "/reference-controls/"
        assert "MFA" in result
