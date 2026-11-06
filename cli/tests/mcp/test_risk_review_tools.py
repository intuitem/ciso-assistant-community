"""Unit tests for the MCP risk-review write tools and their resolvers.

Network calls are mocked at their import sites (ca_mcp.resolvers.*,
ca_mcp.tools.write_tools.*, ca_mcp.tools.update_tools.*).
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from ca_mcp import resolvers  # noqa: E402
from ca_mcp.tools import update_tools, write_tools  # noqa: E402

UUID_A = "11111111-1111-1111-1111-111111111111"
UUID_B = "22222222-2222-2222-2222-222222222222"
UUID_C = "33333333-3333-3333-3333-333333333333"
UUID_D = "44444444-4444-4444-4444-444444444444"
UUID_RA = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
UUID_MX = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
UUID_PE = "cccccccc-cccc-cccc-cccc-cccccccccccc"

QUALIFICATIONS = [
    {"id": "q-conf", "name": "confidentiality", "translations": {}},
    {"id": "q-int", "name": "integrity", "translations": {}},
    {"id": "q-avail", "name": "availability", "translations": {}},
    {"id": "q-proof", "name": "proof", "translations": {}},
    {
        "id": "q-custom",
        "name": "sovereignty",
        "translations": {"fr": {"name": "Souveraineté"}},
    },
]

MATRIX = {
    "id": UUID_MX,
    "json_definition": {
        "risk": [
            {"abbreviation": "L", "name": "Low"},
            {"abbreviation": "M", "name": "Medium"},
            {"abbreviation": "H", "name": "High"},
            {"abbreviation": "VH", "name": "Very High"},
        ]
    },
}


def _response(status_code=200, json_data=None, text=""):
    res = Mock()
    res.status_code = status_code
    res.json.return_value = json_data if json_data is not None else {}
    res.text = text
    return res


def _router(routes):
    """fetch_all_results stand-in: routes maps endpoint -> list or callable(params)."""
    calls = []

    def fake(endpoint, params=None, **kwargs):
        calls.append((endpoint, dict(params or {})))
        value = routes.get(endpoint, [])
        if callable(value):
            value = value(params or {})
        return value, None

    fake.calls = calls
    return fake


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# resolve_actor_id
# ---------------------------------------------------------------------------


class TestResolveActor:
    def test_uuid_passthrough(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_actor_id(UUID_A) == UUID_A
            fetch.assert_not_called()

    def test_owner_by_email_via_specific_email(self):
        actors = [
            {
                "id": UUID_A,
                "str": "Enzo Ferrari",
                "type": "user",
                "specific": {
                    "id": "u1",
                    "str": "Enzo Ferrari",
                    "email": "enzo@acme.io",
                },
            },
            {
                "id": UUID_B,
                "str": "Lorenzo Medici",
                "type": "user",
                "specific": {
                    "id": "u2",
                    "str": "Lorenzo Medici",
                    "email": "lorenzo@acme.io",
                },
            },
        ]
        fake = _router({"/actors/": actors})
        with patch.object(resolvers, "fetch_all_results", fake):
            assert resolvers.resolve_actor_id("enzo@acme.io") == UUID_A
        assert fake.calls[0] == ("/actors/", {"search": "enzo@acme.io"})

    def test_owner_by_email_via_users_lookup(self):
        # /actors/ only returns {id, str} in `specific`: map the email through /users/
        actors = [
            {
                "id": UUID_A,
                "str": "Enzo Ferrari",
                "type": "user",
                "specific": {"id": "u1", "str": "Enzo Ferrari"},
            },
            {
                "id": UUID_B,
                "str": "Lorenzo Medici",
                "type": "user",
                "specific": {"id": "u2", "str": "Lorenzo Medici"},
            },
        ]
        users = [{"id": "u1", "email": "enzo@acme.io"}]
        fake = _router({"/actors/": actors, "/users/": users})
        with patch.object(resolvers, "fetch_all_results", fake):
            assert resolvers.resolve_actor_id("Enzo@acme.io") == UUID_A
        assert ("/users/", {"email__icontains": "Enzo@acme.io"}) in fake.calls

    def test_uuid_like_36_char_email_is_resolved(self):
        ref = "first-name-last-name@example-corp.io"
        assert len(ref) == 36
        actors = [{"id": UUID_A, "str": ref, "type": "user", "specific": {"id": "u1"}}]
        fake = _router({"/actors/": actors, "/users/": []})
        with patch.object(resolvers, "fetch_all_results", fake):
            assert resolvers.resolve_actor_id(ref) == UUID_A
        assert fake.calls[0] == ("/actors/", {"search": ref})

    def test_partial_name_single_hit(self):
        actors = [
            {
                "id": UUID_A,
                "str": "Enzo Ferrari",
                "type": "user",
                "specific": {"id": "u1", "str": "Enzo Ferrari"},
            }
        ]
        with patch.object(
            resolvers, "fetch_all_results", _router({"/actors/": actors})
        ):
            assert resolvers.resolve_actor_id("Enzo") == UUID_A

    def test_exact_str_wins_over_other_hits(self):
        actors = [
            {"id": UUID_A, "str": "Security", "type": "team", "specific": {}},
            {"id": UUID_B, "str": "Security Ops", "type": "team", "specific": {}},
        ]
        with patch.object(
            resolvers, "fetch_all_results", _router({"/actors/": actors})
        ):
            assert resolvers.resolve_actor_id("security") == UUID_A

    def test_partial_name_ambiguous_lists_up_to_five(self):
        actors = [
            {
                "id": f"{i:08d}-0000-0000-0000-000000000000",
                "str": f"Enzo {i}",
                "type": "user",
                "specific": {},
            }
            for i in range(7)
        ]
        with patch.object(
            resolvers, "fetch_all_results", _router({"/actors/": actors})
        ):
            with pytest.raises(ValueError) as exc:
                resolvers.resolve_actor_id("Enzo")
        msg = str(exc.value)
        assert "Ambiguous" in msg and "found 7" in msg
        assert "Enzo 4" in msg and "Enzo 5" not in msg

    def test_unknown_email_does_not_fall_back_to_partial_match(self):
        actors = [
            {
                "id": UUID_A,
                "str": "Jo Ann",
                "type": "user",
                "specific": {"id": "u1", "str": "Jo Ann"},
            }
        ]
        users = [{"id": "u1", "email": "joann@corp.com"}]
        fake = _router({"/actors/": actors, "/users/": users})
        with patch.object(resolvers, "fetch_all_results", fake):
            with pytest.raises(ValueError, match="not found"):
                resolvers.resolve_actor_id("ann@corp.com")

    def test_not_found(self):
        with patch.object(resolvers, "fetch_all_results", _router({"/actors/": []})):
            with pytest.raises(ValueError, match="not found"):
                resolvers.resolve_actor_id("nobody")


# ---------------------------------------------------------------------------
# resolve_user_id / resolve_user_ids
# ---------------------------------------------------------------------------


class TestResolveUser:
    def test_uuid_passthrough(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_user_id(UUID_A) == UUID_A
            fetch.assert_not_called()

    def test_by_email_uses_email_param(self):
        users = [{"id": UUID_A, "email": "enzo@acme.io"}]
        fake = _router({"/users/": users})
        with patch.object(resolvers, "fetch_all_results", fake):
            assert resolvers.resolve_user_id("enzo@acme.io") == UUID_A
        assert fake.calls == [("/users/", {"email__icontains": "enzo@acme.io"})]

    def test_email_match_ignores_case(self):
        users = [{"id": UUID_A, "email": "enzo@acme.io"}]
        with patch.object(resolvers, "fetch_all_results", _router({"/users/": users})):
            assert resolvers.resolve_user_id("Enzo@Acme.io") == UUID_A

    def test_partial_email_match_is_rejected(self):
        users = [{"id": UUID_A, "email": "lorenzo@acme.io"}]
        with patch.object(resolvers, "fetch_all_results", _router({"/users/": users})):
            with pytest.raises(ValueError, match="exact"):
                resolvers.resolve_user_id("enzo@acme.io")

    def test_by_name_uses_search_param(self):
        users = [{"id": UUID_A, "email": "enzo@acme.io", "first_name": "Enzo"}]
        fake = _router({"/users/": users})
        with patch.object(resolvers, "fetch_all_results", fake):
            assert resolvers.resolve_user_id("Enzo") == UUID_A
        assert fake.calls == [("/users/", {"search": "Enzo"})]

    def test_lookup_is_not_capped(self):
        users = [{"id": UUID_A, "email": "enzo@acme.io", "first_name": "Enzo"}]
        with patch.object(
            resolvers, "fetch_all_results", return_value=(users, None)
        ) as fetch:
            resolvers.resolve_user_id("Enzo")
        fetch.assert_called_once_with(
            "/users/", params={"search": "Enzo"}, max_items=None
        )

    def test_single_partial_match_is_rejected(self):
        # ?search= is fuzzy: "Ann" must not silently resolve to "Joanna Smith".
        users = [
            {
                "id": UUID_A,
                "email": "joanna@acme.io",
                "first_name": "Joanna",
                "last_name": "Smith",
            }
        ]
        with patch.object(resolvers, "fetch_all_results", _router({"/users/": users})):
            with pytest.raises(ValueError, match="not found as an exact"):
                resolvers.resolve_user_id("Ann")

    def test_exact_full_name_among_several(self):
        users = [
            {
                "id": UUID_A,
                "email": "a@acme.io",
                "first_name": "Ann",
                "last_name": "Lee",
            },
            {
                "id": UUID_B,
                "email": "b@acme.io",
                "first_name": "Joanna",
                "last_name": "Ann",
            },
        ]
        with patch.object(resolvers, "fetch_all_results", _router({"/users/": users})):
            assert resolvers.resolve_user_id("ann lee") == UUID_A

    def test_ambiguous(self):
        users = [
            {"id": UUID_A, "email": "a@acme.io", "first_name": "Enzo"},
            {"id": UUID_B, "email": "b@acme.io", "first_name": "Enzo"},
        ]
        with patch.object(resolvers, "fetch_all_results", _router({"/users/": users})):
            with pytest.raises(ValueError, match="Ambiguous"):
                resolvers.resolve_user_id("enzo")

    def test_not_found(self):
        with patch.object(resolvers, "fetch_all_results", _router({"/users/": []})):
            with pytest.raises(ValueError, match="not found"):
                resolvers.resolve_user_id("nobody")

    def test_resolve_user_ids_accepts_single_string(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_user_ids(UUID_A) == [UUID_A]
            fetch.assert_not_called()


# ---------------------------------------------------------------------------
# resolve_reference_control_id
# ---------------------------------------------------------------------------


class TestResolveReferenceControl:
    def test_urn(self):
        urn = "urn:intuitem:risk:req_node:doc-pol:pol.ai"
        fake = _router({"/reference-controls/": [{"id": UUID_A, "urn": urn}]})
        with patch.object(resolvers, "fetch_all_results", fake):
            assert resolvers.resolve_reference_control_id(urn) == UUID_A
        assert fake.calls == [("/reference-controls/", {"urn": urn})]

    def test_ref_id_exact_case_insensitive(self):
        controls = [
            {"id": UUID_A, "ref_id": "POL.AI", "name": "AI policy"},
            {"id": UUID_B, "ref_id": "POL.AIX", "name": "Other"},
        ]
        fake = _router({"/reference-controls/": controls})
        with patch.object(resolvers, "fetch_all_results", fake):
            assert resolvers.resolve_reference_control_id("pol.ai") == UUID_A
        assert fake.calls == [("/reference-controls/", {"search": "pol.ai"})]

    def test_name_exact_after_ref_id(self):
        controls = [
            {"id": UUID_A, "ref_id": "POL.1", "name": "Access control policy"},
            {"id": UUID_B, "ref_id": "POL.2", "name": "Access control policy v2"},
        ]
        with patch.object(
            resolvers, "fetch_all_results", _router({"/reference-controls/": controls})
        ):
            assert (
                resolvers.resolve_reference_control_id("access control policy")
                == UUID_A
            )

    def test_no_exact_match(self):
        controls = [{"id": UUID_A, "ref_id": "POL.AIX", "name": "Other"}]
        with patch.object(
            resolvers, "fetch_all_results", _router({"/reference-controls/": controls})
        ):
            with pytest.raises(ValueError, match="not found"):
                resolvers.resolve_reference_control_id("POL.AI")

    def test_several_exact_matches(self):
        controls = [
            {"id": UUID_A, "ref_id": "POL.AI", "name": "A"},
            {"id": UUID_B, "ref_id": "pol.ai", "name": "B"},
        ]
        with patch.object(
            resolvers, "fetch_all_results", _router({"/reference-controls/": controls})
        ):
            with pytest.raises(ValueError, match="Ambiguous"):
                resolvers.resolve_reference_control_id("POL.AI")


# ---------------------------------------------------------------------------
# resolve_qualification_ids
# ---------------------------------------------------------------------------


class TestResolveQualifications:
    def _patch(self):
        return patch.object(
            resolvers, "fetch_all_results", _router({"/terminologies/": QUALIFICATIONS})
        )

    def test_letters(self):
        fake = _router({"/terminologies/": QUALIFICATIONS})
        with patch.object(resolvers, "fetch_all_results", fake):
            ids = resolvers.resolve_qualification_ids(["D", "I", "C", "T"])
        assert ids == ["q-avail", "q-int", "q-conf", "q-proof"]
        assert fake.calls == [
            ("/terminologies/", {"field_path": "qualifications", "is_visible": "true"})
        ]

    def test_letter_aliases(self):
        with self._patch():
            assert resolvers.resolve_qualification_ids(["A", "P", "d"]) == [
                "q-avail",
                "q-proof",
            ]

    def test_names_and_translations(self):
        with self._patch():
            assert resolvers.resolve_qualification_ids(
                ["integrity", "Intégrité", "Souveraineté", "CONFIDENTIALITY"]
            ) == ["q-int", "q-custom", "q-conf"]

    def test_uuid_passthrough(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_qualification_ids([UUID_A]) == [UUID_A]
            fetch.assert_not_called()

    def test_unknown_lists_visible_names(self):
        with self._patch():
            with pytest.raises(ValueError) as exc:
                resolvers.resolve_qualification_ids(["X-factor"])
        assert "confidentiality" in str(exc.value) and "sovereignty" in str(exc.value)


# ---------------------------------------------------------------------------
# resolve_risk_level_index
# ---------------------------------------------------------------------------


class TestResolveRiskLevel:
    def test_int_passthrough(self):
        with patch.object(resolvers, "make_get_request") as get:
            assert resolvers.resolve_risk_level_index(2, UUID_MX) == 2
            assert resolvers.resolve_risk_level_index(-1) == -1
            get.assert_not_called()

    def test_name_and_abbreviation(self):
        with patch.object(
            resolvers, "make_get_request", return_value=_response(200, MATRIX)
        ) as get:
            assert resolvers.resolve_risk_level_index("High", UUID_MX) == 2
            assert resolvers.resolve_risk_level_index("vh", UUID_MX) == 3
        get.assert_called_with(f"/risk-matrices/{UUID_MX}/")

    def test_translated_names(self):
        # json_definition comes back localized; other locales are in translations
        matrix = {
            "id": UUID_MX,
            "json_definition": {
                "risk": [
                    {
                        "abbreviation": "F",
                        "name": "Faible",
                        "translations": {"en": {"name": "Low", "abbreviation": "L"}},
                    },
                    {
                        "abbreviation": "E",
                        "name": "Élevé",
                        "translations": {"en": {"name": "High", "abbreviation": "H"}},
                    },
                ]
            },
        }
        with patch.object(
            resolvers, "make_get_request", return_value=_response(200, matrix)
        ):
            assert resolvers.resolve_risk_level_index("High", UUID_MX) == 1
            assert resolvers.resolve_risk_level_index("l", UUID_MX) == 0
            assert resolvers.resolve_risk_level_index("élevé", UUID_MX) == 1

    def test_empty_input_rejected(self):
        matrix = {
            "id": UUID_MX,
            "json_definition": {"risk": [{"abbreviation": "", "name": ""}]},
        }
        with patch.object(
            resolvers, "make_get_request", return_value=_response(200, matrix)
        ):
            with pytest.raises(ValueError):
                resolvers.resolve_risk_level_index("   ", UUID_MX)

    def test_no_match_lists_levels(self):
        with patch.object(
            resolvers, "make_get_request", return_value=_response(200, MATRIX)
        ):
            with pytest.raises(ValueError) as exc:
                resolvers.resolve_risk_level_index("Critical", UUID_MX)
        assert "Very High" in str(exc.value)


# ---------------------------------------------------------------------------
# create_applied_control
# ---------------------------------------------------------------------------


class TestCreateAppliedControl:
    def _call(self, **kwargs):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "x"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
        ):
            result = run(write_tools.create_applied_control(**kwargs))
        return result, post

    def test_old_parameters_payload_without_status(self):
        result, post = self._call(name="MFA", description="d", eta="2026-12-31")
        assert "Created applied control" in result
        assert post.call_args.args == (
            "/applied-controls/",
            {
                "name": "MFA",
                "description": "d",
                "category": "technical",
                "eta": "2026-12-31",
            },
        )

    @pytest.mark.parametrize(
        "given,sent",
        [
            ("planned", "to_do"),
            ("inactive", "deprecated"),
            ("active", "active"),
            ("--", "--"),
        ],
    )
    def test_status_mapping(self, given, sent):
        _, post = self._call(name="MFA", status=given)
        assert post.call_args.args[1]["status"] == sent

    def test_unknown_status(self):
        result, post = self._call(name="MFA", status="bogus")
        post.assert_not_called()
        assert "to_do" in result and "degraded" in result

    def test_new_fields_resolved(self):
        with (
            patch.object(
                write_tools, "resolve_reference_control_id", return_value=UUID_B
            ),
            patch.object(
                write_tools, "resolve_asset_id", return_value=UUID_C
            ) as resolve_asset,
            patch.object(write_tools, "resolve_actor_ids", return_value=[UUID_D]),
        ):
            _, post = self._call(
                name="AI policy",
                folder_id=UUID_PE,
                status="planned",
                category="policy",
                reference_control="POL.AI",
                assets=["ERP"],
                owner=["enzo@acme.io"],
                priority=1,
                ref_id="AC-1",
                csf_function="govern",
            )
        resolve_asset.assert_called_once_with("ERP", folder_id=UUID_PE)
        payload = post.call_args.args[1]
        assert payload["folder"] == UUID_PE
        assert payload["reference_control"] == UUID_B
        assert payload["assets"] == [UUID_C]
        assert payload["owner"] == [UUID_D]
        assert payload["priority"] == 1
        assert payload["ref_id"] == "AC-1"
        assert payload["csf_function"] == "govern"
        assert payload["category"] == "policy"
        assert payload["status"] == "to_do"


# ---------------------------------------------------------------------------
# create_team
# ---------------------------------------------------------------------------


class TestCreateTeam:
    def test_full_payload_resolved(self):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "SOC"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
            patch.object(write_tools, "resolve_folder_id", return_value=UUID_PE),
            patch.object(
                resolvers, "resolve_user_id", return_value=UUID_D
            ) as resolve_leader,
            patch.object(
                resolvers,
                "resolve_user_ids",
                side_effect=lambda refs: (
                    [UUID_B] if refs == ["Jo"] else [UUID_B, UUID_C]
                ),
            ),
        ):
            result = run(
                write_tools.create_team(
                    name="SOC",
                    description="d",
                    folder_id="Engineering",
                    team_email="soc@acme.io",
                    leader="enzo@acme.io",
                    deputies=["Jo"],
                    members=["Jo", "Ann"],
                )
            )
        assert "Created team" in result
        resolve_leader.assert_called_once_with("enzo@acme.io")
        assert post.call_args.args == (
            "/teams/",
            {
                "name": "SOC",
                "description": "d",
                "folder": UUID_PE,
                "team_email": "soc@acme.io",
                "leader": UUID_D,
                "deputies": [UUID_B],
                "members": [UUID_B, UUID_C],
            },
        )

    def test_minimal_payload(self):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "SOC"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
        ):
            run(write_tools.create_team(name="SOC"))
        assert post.call_args.args == (
            "/teams/",
            {"name": "SOC", "description": ""},
        )


# ---------------------------------------------------------------------------
# resolve_managed_document_id
# ---------------------------------------------------------------------------


class TestResolveManagedDocument:
    def test_uuid_passthrough(self):
        with patch.object(resolvers, "fetch_all_results") as fetch:
            assert resolvers.resolve_managed_document_id(UUID_A) == UUID_A
            fetch.assert_not_called()

    def test_by_name_uses_search_and_exact_match(self):
        docs = [
            {"id": UUID_A, "display_name": "AI policy"},
            {"id": UUID_B, "display_name": "AI policy v2"},
        ]
        fake = _router({"/managed-documents/": docs})
        with patch.object(resolvers, "fetch_all_results", fake):
            assert resolvers.resolve_managed_document_id("AI policy") == UUID_A
        assert fake.calls == [("/managed-documents/", {"search": "AI policy"})]

    def test_ambiguous(self):
        docs = [
            {"id": UUID_A, "display_name": "AI policy"},
            {"id": UUID_B, "display_name": "AI policy"},
        ]
        with patch.object(
            resolvers, "fetch_all_results", _router({"/managed-documents/": docs})
        ):
            with pytest.raises(ValueError, match="Ambiguous"):
                resolvers.resolve_managed_document_id("AI policy")

    def test_not_found(self):
        with patch.object(
            resolvers, "fetch_all_results", _router({"/managed-documents/": []})
        ):
            with pytest.raises(ValueError, match="not found"):
                resolvers.resolve_managed_document_id("nobody")


# ---------------------------------------------------------------------------
# create_document
# ---------------------------------------------------------------------------


class TestCreateDocument:
    def test_full_payload_sets_content(self):
        post = Mock(
            return_value=_response(
                201,
                {
                    "id": UUID_A,
                    "name": "AI policy",
                    "display_name": "AI policy",
                    "current_revision": {"id": UUID_D, "version_number": 1},
                },
            )
        )
        patch_req = Mock(return_value=_response(200, {}))
        with (
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "make_patch_request", patch_req),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
            patch.object(write_tools, "resolve_folder_id", return_value=UUID_PE),
            patch.object(resolvers, "resolve_id_or_name", return_value=UUID_B),
        ):
            result = run(
                write_tools.create_document(
                    name="AI policy",
                    document_type="policy",
                    description="d",
                    folder_id="Engineering",
                    content="# AI policy\n\ncontent",
                    locale="en",
                    policy="POL-AI",
                )
            )
        assert "Created document" in result
        assert "revision: 1" in result
        assert post.call_args.args == (
            "/managed-documents/",
            {
                "name": "AI policy",
                "description": "d",
                "document_type": "policy",
                "folder": UUID_PE,
                "locale": "en",
                "policy": UUID_B,
            },
        )
        assert patch_req.call_args.args == (
            f"/document-revisions/{UUID_D}/",
            {"content": "# AI policy\n\ncontent"},
        )

    def test_minimal_payload_no_content_patch(self):
        post = Mock(
            return_value=_response(
                201, {"id": UUID_A, "name": "Doc", "current_revision": {"id": UUID_D}}
            )
        )
        patch_req = Mock()
        with (
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "make_patch_request", patch_req),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
        ):
            result = run(write_tools.create_document(name="Doc"))
        assert "Created document" in result
        assert post.call_args.args == (
            "/managed-documents/",
            {"name": "Doc", "description": "", "document_type": "policy"},
        )
        patch_req.assert_not_called()

    def test_invalid_document_type(self):
        post = Mock()
        with patch.object(write_tools, "make_post_request", post):
            result = run(write_tools.create_document(name="Doc", document_type="bogus"))
        post.assert_not_called()
        assert "Invalid document_type" in result


# ---------------------------------------------------------------------------
# _get_latest_revision
# ---------------------------------------------------------------------------


class TestGetLatestRevision:
    def test_returns_first_result(self):
        get_req = Mock(
            return_value=_response(
                200, {"results": [{"id": UUID_D, "version_number": 2}, {"id": UUID_B}]}
            )
        )
        with patch.object(write_tools, "make_get_request", get_req):
            revision, error = write_tools._get_latest_revision(UUID_A)
        assert error is None
        assert revision == {"id": UUID_D, "version_number": 2}
        get_req.assert_called_once_with(
            "/document-revisions/", params={"document": UUID_A}
        )

    def test_no_revisions(self):
        with patch.object(
            write_tools,
            "make_get_request",
            return_value=_response(200, {"results": []}),
        ):
            revision, error = write_tools._get_latest_revision(UUID_A)
        assert revision is None
        assert "no revisions" in error

    def test_http_error(self):
        with patch.object(
            write_tools, "make_get_request", return_value=_response(404, text="nope")
        ):
            revision, error = write_tools._get_latest_revision(UUID_A)
        assert revision is None
        assert "404" in error


# ---------------------------------------------------------------------------
# document review workflow
# ---------------------------------------------------------------------------


class TestDocumentWorkflow:
    def _mock_latest(self, revision_id=UUID_D, version=3):
        return patch.object(
            write_tools,
            "_get_latest_revision",
            return_value=({"id": revision_id, "version_number": version}, None),
        )

    def _mock_resolve(self):
        return patch.object(
            resolvers, "resolve_managed_document_id", return_value=UUID_A
        )

    def test_submit_document_for_review(self):
        post = Mock(return_value=_response(200, {"status": "in_review"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            self._mock_latest(),
            self._mock_resolve(),
        ):
            result = run(write_tools.submit_document_for_review("My policy"))
        assert "Submitted for review" in result
        assert "revision 3" in result
        assert post.call_args.args == (
            f"/document-revisions/{UUID_D}/submit-for-review/",
            {},
        )

    def test_approve_document(self):
        post = Mock(return_value=_response(200, {"status": "validated"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            self._mock_latest(),
            self._mock_resolve(),
        ):
            result = run(write_tools.approve_document(UUID_A))
        assert "Approved" in result
        assert post.call_args.args == (
            f"/document-revisions/{UUID_D}/approve/",
            {},
        )

    def test_request_document_changes_with_comments(self):
        post = Mock(return_value=_response(200, {"status": "change_requested"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            self._mock_latest(),
            self._mock_resolve(),
        ):
            result = run(
                write_tools.request_document_changes(UUID_A, comments="Fix section 2")
            )
        assert "Requested changes" in result
        assert post.call_args.args == (
            f"/document-revisions/{UUID_D}/request-changes/",
            {"reviewer_comments": "Fix section 2"},
        )

    def test_request_document_changes_without_comments(self):
        post = Mock(return_value=_response(200, {"status": "change_requested"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            self._mock_latest(),
            self._mock_resolve(),
        ):
            run(write_tools.request_document_changes(UUID_A))
        assert post.call_args.args == (
            f"/document-revisions/{UUID_D}/request-changes/",
            {},
        )

    def test_publish_document(self):
        post = Mock(return_value=_response(200, {"status": "published"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            self._mock_latest(),
            self._mock_resolve(),
        ):
            result = run(write_tools.publish_document(UUID_A))
        assert "Published" in result
        assert post.call_args.args == (
            f"/document-revisions/{UUID_D}/publish/",
            {},
        )

    def test_workflow_action_rejected_by_backend_surfaces_error(self):
        rejected = _response(400, text="Only in-review revisions can be approved.")
        with (
            patch.object(write_tools, "make_post_request", return_value=rejected),
            self._mock_latest(),
            self._mock_resolve(),
        ):
            result = run(write_tools.approve_document(UUID_A))
        assert "Error approving document" in result
        assert "Only in-review revisions" in result

    def test_create_document_draft(self):
        post = Mock(
            return_value=_response(
                201, {"id": UUID_D, "version_number": 2, "status": "draft"}
            )
        )
        with (
            patch.object(write_tools, "make_post_request", post),
            self._mock_resolve(),
        ):
            result = run(write_tools.create_document_draft(UUID_A))
        assert "Created draft" in result
        assert "revision 2" in result
        assert post.call_args.args == (
            f"/managed-documents/{UUID_A}/create-new-draft/",
            {},
        )

    def test_create_document_draft_conflict_surfaces_error(self):
        conflict = _response(
            400, text="A draft revision already exists for this document."
        )
        with (
            patch.object(write_tools, "make_post_request", return_value=conflict),
            self._mock_resolve(),
        ):
            result = run(write_tools.create_document_draft(UUID_A))
        assert "Error creating draft" in result
        assert "already exists" in result


# ---------------------------------------------------------------------------
# create_risk_scenario / create_risk_assessment / create_task_template
# ---------------------------------------------------------------------------


class TestCreateRiskScenario:
    def test_full_payload(self):
        actors = [
            {
                "id": UUID_D,
                "str": "Enzo Ferrari",
                "type": "user",
                "specific": {"id": "u1", "email": "enzo@acme.io"},
            }
        ]
        fake = _router({"/terminologies/": QUALIFICATIONS, "/actors/": actors})
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "S1"}))
        with (
            patch.object(resolvers, "fetch_all_results", fake),
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
        ):
            result = run(
                write_tools.create_risk_scenario(
                    name="S1",
                    risk_assessment_id=UUID_RA,
                    qualifications=["C", "I"],
                    owner=["enzo@acme.io"],
                    inherent_proba=3,
                    inherent_impact=3,
                    current_proba=2,
                    current_impact=2,
                    residual_proba=1,
                    residual_impact=1,
                    treatment="mitigate",
                    ref_id="R.1",
                    justification="because",
                )
            )
        assert "Created Risk scenario" in result
        endpoint, payload = post.call_args.args
        assert endpoint == "/risk-scenarios/"
        assert payload == {
            "name": "S1",
            "description": "",
            "risk_assessment": UUID_RA,
            "current_proba": 2,
            "current_impact": 2,
            "inherent_proba": 3,
            "inherent_impact": 3,
            "residual_proba": 1,
            "residual_impact": 1,
            "treatment": "mitigate",
            "ref_id": "R.1",
            "justification": "because",
            "qualifications": ["q-conf", "q-int"],
            "owner": [UUID_D],
        }

    def test_old_parameters_unchanged(self):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "S1"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
        ):
            run(write_tools.create_risk_scenario(name="S1", current_proba=1))
        assert post.call_args.args[1] == {
            "name": "S1",
            "description": "",
            "current_proba": 1,
        }


class TestCreateRiskAssessment:
    def _call(self, **kwargs):
        post = Mock(return_value=_response(201, {"id": UUID_RA, "name": "RA"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "GLOBAL_FOLDER_ID", None),
            patch.object(
                resolvers, "make_get_request", return_value=_response(200, MATRIX)
            ),
        ):
            run(
                write_tools.create_risk_assessment(
                    name="RA", risk_matrix_id=UUID_MX, perimeter_id=UUID_PE, **kwargs
                )
            )
        return post.call_args.args[1]

    def test_int_tolerance(self):
        assert self._call(risk_tolerance=2)["risk_tolerance"] == 2

    def test_named_tolerance(self):
        assert self._call(risk_tolerance="High")["risk_tolerance"] == 2

    def test_no_tolerance_not_sent(self):
        assert "risk_tolerance" not in self._call()


class TestCreateTaskTemplate:
    def test_assigned_to_and_assets_resolved(self):
        post = Mock(return_value=_response(201, {"id": UUID_A, "name": "T"}))
        with (
            patch.object(write_tools, "make_post_request", post),
            patch.object(write_tools, "resolve_actor_ids", return_value=[UUID_D]) as ra,
            patch.object(
                write_tools, "resolve_asset_id", return_value=UUID_C
            ) as resolve_asset,
        ):
            run(
                write_tools.create_task_template(
                    name="T", folder_id=UUID_PE, assigned_to=["Enzo"], assets=["ERP"]
                )
            )
        payload = post.call_args.args[1]
        assert payload["assigned_to"] == [UUID_D]
        assert payload["assets"] == [UUID_C]
        ra.assert_called_once_with(["Enzo"])
        resolve_asset.assert_called_once_with("ERP", folder_id=UUID_PE)


# ---------------------------------------------------------------------------
# update tools
# ---------------------------------------------------------------------------


class TestUpdateTools:
    def _patch_ok(self, body=None):
        return patch.object(
            update_tools,
            "make_patch_request",
            return_value=_response(200, body or {"id": UUID_A, "name": "x"}),
        )

    @pytest.mark.parametrize(
        "given,sent", [("planned", "to_do"), ("inactive", "deprecated")]
    )
    def test_update_applied_control_legacy_status(self, given, sent):
        with self._patch_ok() as patch_req:
            run(update_tools.update_applied_control(control_id=UUID_A, status=given))
        assert patch_req.call_args.args[1] == {"status": sent}

    def test_update_applied_control_new_fields(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(update_tools, "resolve_actor_ids", return_value=[UUID_D]),
            patch.object(
                update_tools, "resolve_reference_control_id", return_value=UUID_B
            ),
            patch.object(update_tools, "resolve_asset_id", return_value=UUID_C),
        ):
            run(
                update_tools.update_applied_control(
                    control_id=UUID_A,
                    owner=["Enzo"],
                    reference_control="POL.AI",
                    assets=["ERP", "CRM"],
                )
            )
        assert patch_req.call_args.args == (
            f"/applied-controls/{UUID_A}/",
            {
                "owner": [UUID_D],
                "reference_control": UUID_B,
                "assets": [UUID_C, UUID_C],
            },
        )

    def test_update_risk_scenario_qualifications_owner(self):
        fake = _router({"/terminologies/": QUALIFICATIONS})
        with (
            self._patch_ok() as patch_req,
            patch.object(resolvers, "fetch_all_results", fake),
        ):
            run(
                update_tools.update_risk_scenario(
                    risk_scenario_id=UUID_A,
                    qualifications=["A"],
                    owner=[UUID_D],
                    treatment="cancelled",
                )
            )
        assert patch_req.call_args.args[1] == {
            "treatment": "cancelled",
            "qualifications": ["q-avail"],
            "owner": [UUID_D],
        }

    def test_update_asset_owner_resolved(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(update_tools, "resolve_actor_ids", return_value=[UUID_D]),
        ):
            run(update_tools.update_asset(asset_id=UUID_A, owner=["enzo@acme.io"]))
        assert patch_req.call_args.args[1] == {"owner": [UUID_D]}

    def test_update_task_template_assigned_to_resolved(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(update_tools, "resolve_actor_ids", return_value=[UUID_D]),
        ):
            run(update_tools.update_task_template(task_id=UUID_A, assigned_to=["Enzo"]))
        assert patch_req.call_args.args[1] == {"assigned_to": [UUID_D]}

    def test_update_risk_assessment_payload(self):
        with self._patch_ok() as patch_req:
            result = run(
                update_tools.update_risk_assessment(
                    risk_assessment_id=UUID_RA,
                    name="RA v2",
                    description="d",
                    version="2.0",
                    ref_id="RA-1",
                    status="in_review",
                    risk_tolerance=1,
                    eta="2026-12-31",
                    due_date="2027-01-31",
                )
            )
        assert "Updated Risk assessment" in result
        assert patch_req.call_args.args == (
            f"/risk-assessments/{UUID_RA}/",
            {
                "name": "RA v2",
                "description": "d",
                "version": "2.0",
                "ref_id": "RA-1",
                "status": "in_review",
                "eta": "2026-12-31",
                "due_date": "2027-01-31",
                "risk_tolerance": 1,
            },
        )

    def test_update_risk_assessment_named_tolerance(self):
        ra = _response(200, {"id": UUID_RA, "risk_matrix": {"id": UUID_MX, "str": "M"}})
        with (
            self._patch_ok() as patch_req,
            patch.object(update_tools, "make_get_request", return_value=ra),
            patch.object(
                resolvers, "make_get_request", return_value=_response(200, MATRIX)
            ),
        ):
            run(
                update_tools.update_risk_assessment(
                    risk_assessment_id=UUID_RA, risk_tolerance="Medium"
                )
            )
        assert patch_req.call_args.args[1] == {"risk_tolerance": 1}

    def test_update_risk_assessment_unknown_level(self):
        ra = _response(200, {"id": UUID_RA, "risk_matrix": UUID_MX})
        with (
            self._patch_ok() as patch_req,
            patch.object(update_tools, "make_get_request", return_value=ra),
            patch.object(
                resolvers, "make_get_request", return_value=_response(200, MATRIX)
            ),
        ):
            result = run(
                update_tools.update_risk_assessment(
                    risk_assessment_id=UUID_RA, risk_tolerance="Extreme"
                )
            )
        patch_req.assert_not_called()
        assert "Very High" in result

    def test_update_perimeter_payload(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(update_tools, "resolve_actor_ids", return_value=[UUID_D]),
        ):
            result = run(
                update_tools.update_perimeter(
                    perimeter_id=UUID_PE,
                    name="Prod",
                    description="d",
                    ref_id="P1",
                    lc_status="in_prod",
                    default_assignee=["Enzo"],
                )
            )
        assert "Updated Perimeter" in result
        assert patch_req.call_args.args == (
            f"/perimeters/{UUID_PE}/",
            {
                "name": "Prod",
                "description": "d",
                "ref_id": "P1",
                "lc_status": "in_prod",
                "default_assignee": [UUID_D],
            },
        )

    def test_update_perimeter_rejects_slash_and_bad_status(self):
        with self._patch_ok() as patch_req:
            assert "Error" in run(update_tools.update_perimeter(UUID_PE, name="a/b"))
            assert "Error" in run(update_tools.update_perimeter(UUID_PE, lc_status="x"))
        patch_req.assert_not_called()

    def test_update_team_payload(self):
        with (
            self._patch_ok({"id": UUID_A, "name": "SOC v2"}) as patch_req,
            patch.object(update_tools, "resolve_team_id", return_value=UUID_A),
            patch.object(update_tools, "resolve_user_id", return_value=UUID_D),
            patch.object(update_tools, "resolve_user_ids", return_value=[UUID_B]),
        ):
            result = run(
                update_tools.update_team(
                    team_id="SOC",
                    name="SOC v2",
                    team_email="soc@acme.io",
                    leader="enzo@acme.io",
                    members=["Jo"],
                )
            )
        assert "Updated team" in result
        assert patch_req.call_args.args == (
            f"/teams/{UUID_A}/",
            {
                "name": "SOC v2",
                "team_email": "soc@acme.io",
                "leader": UUID_D,
                "members": [UUID_B],
            },
        )

    def test_update_team_no_fields(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(update_tools, "resolve_team_id", return_value=UUID_A),
        ):
            result = run(update_tools.update_team(team_id=UUID_A))
        patch_req.assert_not_called()
        assert "No fields" in result

    def test_update_document_metadata_and_content(self):
        with (
            self._patch_ok({"id": UUID_A, "display_name": "AI policy v2"}) as patch_req,
            patch.object(
                update_tools, "resolve_managed_document_id", return_value=UUID_A
            ),
            patch.object(
                update_tools,
                "_get_latest_revision",
                return_value=({"id": UUID_D, "version_number": 2}, None),
            ),
        ):
            result = run(
                update_tools.update_document(
                    document_id="AI policy",
                    name="AI policy v2",
                    content="# new content",
                )
            )
        assert "Updated document" in result
        assert "Updated content (revision 2)" in result
        assert patch_req.call_args_list[0].args == (
            f"/managed-documents/{UUID_A}/",
            {"name": "AI policy v2"},
        )
        assert patch_req.call_args_list[1].args == (
            f"/document-revisions/{UUID_D}/",
            {"content": "# new content"},
        )

    def test_update_document_content_only_fetches_latest_revision(self):
        get_latest = Mock(return_value=({"id": UUID_D}, None))
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools, "resolve_managed_document_id", return_value=UUID_A
            ),
            patch.object(update_tools, "_get_latest_revision", get_latest),
        ):
            run(update_tools.update_document(document_id=UUID_A, content="body"))
        get_latest.assert_called_once_with(UUID_A)
        assert patch_req.call_args.args == (
            f"/document-revisions/{UUID_D}/",
            {"content": "body"},
        )

    def test_update_document_no_revision_surfaces_error(self):
        with (
            patch.object(update_tools, "make_patch_request") as patch_req,
            patch.object(
                update_tools, "resolve_managed_document_id", return_value=UUID_A
            ),
            patch.object(
                update_tools,
                "_get_latest_revision",
                return_value=(None, "Error: Document has no revisions"),
            ),
        ):
            result = run(update_tools.update_document(document_id=UUID_A, content="x"))
        patch_req.assert_not_called()
        assert "no revisions" in result

    def test_update_document_locked_revision_surfaces_backend_error(self):
        locked = _response(400, text="This revision is locked.")
        with (
            patch.object(update_tools, "make_patch_request", return_value=locked),
            patch.object(
                update_tools, "resolve_managed_document_id", return_value=UUID_A
            ),
            patch.object(
                update_tools,
                "_get_latest_revision",
                return_value=({"id": UUID_D}, None),
            ),
        ):
            result = run(update_tools.update_document(document_id=UUID_A, content="x"))
        assert "locked" in result

    def test_update_document_no_fields(self):
        with (
            self._patch_ok() as patch_req,
            patch.object(
                update_tools, "resolve_managed_document_id", return_value=UUID_A
            ),
        ):
            result = run(update_tools.update_document(document_id=UUID_A))
        patch_req.assert_not_called()
        assert "No fields" in result


# ---------------------------------------------------------------------------
# server registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def _tool_names(self, read_only):
        from mcp.server.mcpserver import MCPServer

        import ca_mcp.server as server

        fresh = MCPServer("test")
        with (
            patch.object(server, "mcp", fresh),
            patch.object(server, "_registered", False),
        ):
            server.register_tools(read_only=read_only)
            tools = asyncio.run(fresh.list_tools())
        return {t.name for t in tools}

    def test_full_profile_has_new_tools(self):
        names = self._tool_names(read_only=False)
        assert {
            "update_risk_assessment",
            "update_perimeter",
            "get_teams",
            "create_team",
            "update_team",
            "get_documents",
            "create_document",
            "update_document",
            "submit_document_for_review",
            "approve_document",
            "request_document_changes",
            "publish_document",
            "create_document_draft",
        } <= names

    def test_read_only_profile_hides_new_tools(self):
        names = self._tool_names(read_only=True)
        assert "update_risk_assessment" not in names
        assert "update_perimeter" not in names
        assert "create_team" not in names
        assert "update_team" not in names
        assert "create_document" not in names
        assert "update_document" not in names
        assert "submit_document_for_review" not in names
        assert "approve_document" not in names
        assert "request_document_changes" not in names
        assert "publish_document" not in names
        assert "create_document_draft" not in names
        assert "get_users" in names
        assert "get_teams" in names
        assert "get_documents" in names
