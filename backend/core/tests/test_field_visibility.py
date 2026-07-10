"""Unit tests for the per-role field visibility helpers."""

import pytest

from core.utils import (
    AUDITOR_ONLY,
    DEFAULT_VISIBILITY,
    EVERYONE_EDIT,
    HIDDEN,
    build_initial_field_visibility,
    is_field_editable_by,
    is_field_visible_to,
    resolve_field_visibility,
)


class _CA:
    """Tiny stand-in for ComplianceAssessment used by the resolver helpers."""

    def __init__(self, field_visibility=None):
        self.field_visibility = field_visibility or {}


class _FW:
    """Tiny stand-in for Framework used by build_initial_field_visibility."""

    def __init__(self, field_visibility=None):
        self.field_visibility = field_visibility or {}


# ---------------------------------------------------------------------------
# resolve_field_visibility
# ---------------------------------------------------------------------------


class TestResolveFieldVisibility:
    def test_explicit_override_wins(self):
        ca = _CA({"result": dict(AUDITOR_ONLY)})
        assert resolve_field_visibility(ca, "result") == AUDITOR_ONLY

    def test_falls_back_to_default_visibility(self):
        # 'score' is not on the CA but DEFAULT_VISIBILITY says HIDDEN.
        ca = _CA({})
        assert resolve_field_visibility(ca, "score") == HIDDEN
        assert resolve_field_visibility(ca, "documentation_score") == HIDDEN
        assert resolve_field_visibility(ca, "extended_result") == AUDITOR_ONLY
        assert resolve_field_visibility(ca, "status") == AUDITOR_ONLY

    def test_unknown_field_resolves_to_everyone_edit(self):
        ca = _CA({})
        assert resolve_field_visibility(ca, "totally_unknown") == EVERYONE_EDIT

    def test_non_dict_value_treated_as_unknown(self):
        # Defensive: legacy string values that escaped normalization mustn't
        # crash the resolver.
        ca = _CA({"result": "everyone"})  # legacy string, not a pair
        # Not a dict → falls through to DEFAULT_VISIBILITY (no entry for result)
        # → EVERYONE_EDIT.
        assert resolve_field_visibility(ca, "result") == EVERYONE_EDIT

    def test_handles_none_field_visibility(self):
        ca = _CA(None)
        assert resolve_field_visibility(ca, "score") == HIDDEN

    def test_default_visibility_constants_match_documented_shape(self):
        # If these change, the migration's setdefault logic, the frontend
        # DEFAULT_VISIBILITY mirror in helpers.ts, and the editor cascade
        # rules all need to be revisited together.
        assert DEFAULT_VISIBILITY["score"] == HIDDEN
        assert DEFAULT_VISIBILITY["is_scored"] == HIDDEN
        assert DEFAULT_VISIBILITY["documentation_score"] == HIDDEN
        assert DEFAULT_VISIBILITY["extended_result"] == AUDITOR_ONLY
        assert DEFAULT_VISIBILITY["status"] == AUDITOR_ONLY
        assert DEFAULT_VISIBILITY["respondent_alignment"] == HIDDEN


# ---------------------------------------------------------------------------
# is_field_visible_to / is_field_editable_by
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pair,role,expected_visible,expected_editable",
    [
        # Auditor + Respondent: both can see and edit.
        (EVERYONE_EDIT, "auditor", True, True),
        (EVERYONE_EDIT, "respondent", True, True),
        # Auditor only: auditor sees and edits, respondent blind.
        (AUDITOR_ONLY, "auditor", True, True),
        (AUDITOR_ONLY, "respondent", False, False),
        # Hidden: no role sees or edits.
        (HIDDEN, "auditor", False, False),
        (HIDDEN, "respondent", False, False),
        # Future "read" state: visible but not editable.
        (
            {"auditor": "edit", "respondent": "read"},
            "respondent",
            True,
            False,
        ),
        (
            {"auditor": "read", "respondent": "edit"},
            "auditor",
            True,
            False,
        ),
    ],
)
def test_role_access_matrix(pair, role, expected_visible, expected_editable):
    ca = _CA({"result": pair})
    assert is_field_visible_to(ca, "result", role) is expected_visible
    assert is_field_editable_by(ca, "result", role) is expected_editable


def test_missing_field_uses_default_visibility_per_role():
    ca = _CA({})
    # score defaults to HIDDEN: invisible to both roles.
    assert is_field_visible_to(ca, "score", "auditor") is False
    assert is_field_visible_to(ca, "score", "respondent") is False
    # status defaults to AUDITOR_ONLY: auditor sees, respondent doesn't.
    assert is_field_visible_to(ca, "status", "auditor") is True
    assert is_field_visible_to(ca, "status", "respondent") is False


def test_unknown_field_defaults_permissive():
    # Unknown keys fall through to EVERYONE_EDIT — both roles can read+edit.
    ca = _CA({})
    assert is_field_visible_to(ca, "future_field", "respondent") is True
    assert is_field_editable_by(ca, "future_field", "respondent") is True


# ---------------------------------------------------------------------------
# build_initial_field_visibility
# ---------------------------------------------------------------------------


class TestBuildInitialFieldVisibility:
    def test_no_framework_overrides_returns_defaults(self):
        fw = _FW({})
        result = build_initial_field_visibility(fw)
        assert result["score"] == HIDDEN
        assert result["status"] == AUDITOR_ONLY
        # Every key from DEFAULT_VISIBILITY is present.
        assert set(DEFAULT_VISIBILITY).issubset(result)

    def test_framework_full_pair_overrides_default(self):
        fw = _FW({"score": dict(EVERYONE_EDIT)})
        result = build_initial_field_visibility(fw)
        assert result["score"] == EVERYONE_EDIT  # framework wins

    def test_framework_partial_pair_merges_per_role(self):
        # Framework only specifies the auditor role for score; the respondent
        # role must come from DEFAULT_VISIBILITY (hidden), not be dropped.
        fw = _FW({"score": {"auditor": "edit"}})
        result = build_initial_field_visibility(fw)
        assert result["score"] == {"auditor": "edit", "respondent": "hidden"}

    def test_framework_can_introduce_new_field(self):
        # A field not in DEFAULT_VISIBILITY but present on the framework gets
        # seeded as EVERYONE_EDIT before the framework's pair is merged in.
        fw = _FW({"observation": {"respondent": "read"}})
        result = build_initial_field_visibility(fw)
        # Auditor still defaults to edit (from EVERYONE_EDIT base), respondent
        # gets the framework's value.
        assert result["observation"] == {"auditor": "edit", "respondent": "read"}

    def test_non_dict_framework_entry_skipped(self):
        # Legacy single-string entries on a framework don't poison the merge.
        fw = _FW({"score": "everyone"})
        result = build_initial_field_visibility(fw)
        assert result["score"] == HIDDEN  # falls through to DEFAULT

    def test_handles_none_framework(self):
        # Caller may pass None when a CA is created without a framework FK
        # populated (defensive — shouldn't happen in practice).
        result = build_initial_field_visibility(None)
        assert result["score"] == HIDDEN
        assert set(DEFAULT_VISIBILITY).issubset(result)

    def test_returns_independent_copies(self):
        # Mutating the result must not affect DEFAULT_VISIBILITY.
        fw = _FW({})
        result = build_initial_field_visibility(fw)
        result["score"]["auditor"] = "read"
        assert DEFAULT_VISIBILITY["score"] == HIDDEN
