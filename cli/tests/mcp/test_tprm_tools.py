"""Unit tests for the MCP TPRM entity tools: relationship and address.

Network calls are mocked at their import sites, as in
test_risk_review_tools.py.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import resolvers  # noqa: E402
from ca_mcp.tools import (  # noqa: E402
    tprm_tools,
)
from tests.mcp.helpers import (  # noqa: E402
    UUID_A,
    UUID_C,
    UUID_F,
    _response,
    _router,
    run,
)


RELATIONSHIPS = [
    {
        "id": "r-supplier",
        "name": "supplier",
        "builtin": True,
        "translations": {"fr": "fournisseur"},
    },
    {"id": "r-client", "name": "client", "builtin": True, "translations": {}},
    {
        "id": "r-custom",
        "name": "Cloud provider",
        "builtin": False,
        "translations": {},
    },
]


class TestEntityRelationship:
    def test_create_entity_resolves_relationship(self):
        fake = _router({"/terminologies/": RELATIONSHIPS})
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "Acme"}))
        with (
            patch.object(resolvers, "fetch_all_results", fake),
            patch.object(tprm_tools, "make_post_request", post),
            patch.object(tprm_tools, "make_patch_request") as patch_req,
        ):
            run(
                tprm_tools.create_entity(
                    name="Acme",
                    folder_id=UUID_F,
                    relationship=["Supplier", "fournisseur", "cloud provider", UUID_C],
                    address="1 rue de la Paix",
                )
            )
        patch_req.assert_not_called()
        payload = post.call_args.args[1]
        assert payload["relationship"] == ["r-supplier", "r-custom", UUID_C]
        assert payload["address"] == "1 rue de la Paix"
        assert fake.calls == [
            (
                "/terminologies/",
                {"field_path": "entity.relationship", "is_visible": "true"},
            )
        ]

    def test_create_entity_old_payload_unchanged(self):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "Acme"}))
        with patch.object(tprm_tools, "make_post_request", post):
            run(tprm_tools.create_entity(name="Acme", folder_id=UUID_F))
        payload = post.call_args.args[1]
        assert "relationship" not in payload and "address" not in payload

    def test_unknown_relationship_never_creates(self):
        fake = _router({"/terminologies/": RELATIONSHIPS})
        post = Mock()
        with (
            patch.object(resolvers, "fetch_all_results", fake),
            patch.object(tprm_tools, "make_post_request", post),
        ):
            result = run(
                tprm_tools.create_entity(
                    name="Acme", folder_id=UUID_F, relationship=["Competitor"]
                )
            )
        post.assert_not_called()
        assert "Competitor" in result and "supplier" in result and "client" in result

    def test_update_entity(self):
        fake = _router({"/terminologies/": RELATIONSHIPS})
        patch_req = Mock(return_value=_response(200, {"id": UUID_A, "name": "Acme"}))
        with (
            patch.object(resolvers, "fetch_all_results", fake),
            patch.object(tprm_tools, "make_patch_request", patch_req),
        ):
            run(
                tprm_tools.update_entity(
                    entity_id=UUID_A, relationship=["client"], address="Paris"
                )
            )
        assert patch_req.call_args.args == (
            f"/entities/{UUID_A}/",
            {"relationship": ["r-client"], "address": "Paris"},
        )
