"""Unit tests for the MCP library tools.

Network calls are mocked at their import sites, as in
test_risk_review_tools.py.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp.tools import library_tools  # noqa: E402
from tests.mcp.helpers import _router, run  # noqa: E402


class TestGetStoredLibraries:
    @pytest.mark.parametrize(
        "asked,sent",
        [
            ("framework", "frameworks"),
            ("risk_matrix", "risk_matrices"),
            ("requirement_mapping_set", "requirement_mapping_sets"),
            ("frameworks", "frameworks"),
            ("threats", "threats"),
        ],
    )
    def test_object_type_is_sent_plural(self, asked, sent):
        fake = _router({})
        with patch.object(library_tools, "fetch_all_results", fake):
            run(library_tools.get_stored_libraries(object_type=asked))
        assert fake.calls == [("/stored-libraries/", {"object_type": sent})]
