"""Tests for ``_refine_verdict_against_citations``.

Belt-and-braces guard that downgrades / refines verdicts based on what the
LLM actually cited. Tested as a pure function with stubbed AC/RA/CA managers
— no DB hit needed.
"""

import pytest

from chat.questionnaire import _refine_verdict_against_citations


def _ref(idx, kind="model", obj_id="obj-1"):
    return {
        "index": idx,
        "kind": kind,
        "id": obj_id,
        "name": "",
        "ref_id": "",
        "score": 0.5,
        "snippet": "...",
    }


class _FakeAC:
    def __init__(self, status):
        self.status = status


class _FakeRA:
    def __init__(self, result):
        self.result = result


class _FakeCA:
    def __init__(self, status):
        self.status = status


class _BulkStub:
    """Emulates ``.filter(id__in=...).values_list("id", <field>)`` on a
    Django manager. Returns iterables of (id, field_value) tuples drawn from
    the per-fixture state map.
    """

    def __init__(self, bucket: dict, field: str):
        # bucket maps id -> object with attribute `field`
        self._bucket = bucket
        self._field = field
        self._ids: list = []

    def filter(self, **kw):
        # Honor id__in=[...]; if id= is given, single-id filter still works.
        ids = kw.get("id__in")
        if ids is None and "id" in kw:
            ids = [kw["id"]]
        self._ids = list(ids or [])
        return self

    def values_list(self, *fields, **_kw):
        # The refiner calls values_list("id", "<status_or_result>")
        # — return tuples in that order.
        out = []
        for ref_id in self._ids:
            obj = self._bucket.get(ref_id)
            if obj is None:
                continue
            out.append((ref_id, getattr(obj, self._field)))
        return out


@pytest.fixture
def patched(monkeypatch):
    """Install AC / RA / CA lookup stubs keyed by id."""
    state = {"ac": {}, "ra": {}, "ca": {}}

    def _install(ac_map=None, ra_map=None, ca_map=None):
        state["ac"] = ac_map or {}
        state["ra"] = ra_map or {}
        state["ca"] = ca_map or {}

    def _make_manager(bucket: str, field: str):
        class M:
            def filter(self, **kw):
                stub = _BulkStub(state[bucket], field)
                return stub.filter(**kw)

        return M()

    monkeypatch.setattr(
        "core.models.AppliedControl.objects", _make_manager("ac", "status")
    )
    monkeypatch.setattr(
        "core.models.RequirementAssessment.objects",
        _make_manager("ra", "result"),
    )
    monkeypatch.setattr(
        "core.models.ComplianceAssessment.objects",
        _make_manager("ca", "status"),
    )
    return _install


class TestRefiner:
    def test_no_citations_left_alone(self, patched):
        patched()
        new_status, note = _refine_verdict_against_citations("yes", [], [])
        assert new_status == "yes"
        assert note == ""

    def test_yes_with_active_ac_kept(self, patched):
        patched(ac_map={"ac-1": _FakeAC("active")})
        refs = [_ref(1, obj_id="ac-1")]
        new_status, note = _refine_verdict_against_citations("yes", [1], refs)
        assert new_status == "yes"
        assert note == ""

    def test_yes_with_only_to_do_downgraded_to_needs_info(self, patched):
        patched(ac_map={"ac-1": _FakeAC("to_do")})
        refs = [_ref(1, obj_id="ac-1")]
        new_status, note = _refine_verdict_against_citations("yes", [1], refs)
        assert new_status == "needs_info"
        assert "planned" in note.lower() or "unverified" in note.lower()

    def test_yes_with_only_in_progress_downgraded_to_partial(self, patched):
        patched(ac_map={"ac-1": _FakeAC("in_progress")})
        refs = [_ref(1, obj_id="ac-1")]
        new_status, note = _refine_verdict_against_citations("yes", [1], refs)
        assert new_status == "partial"

    def test_partial_with_partially_compliant_ra_kept(self, patched):
        patched(ra_map={"ra-1": _FakeRA("partially_compliant")})
        refs = [_ref(1, obj_id="ra-1")]
        new_status, note = _refine_verdict_against_citations("partial", [1], refs)
        assert new_status == "partial"

    def test_partial_with_not_assessed_ra_downgraded(self, patched):
        patched(ra_map={"ra-1": _FakeRA("not_assessed")})
        refs = [_ref(1, obj_id="ra-1")]
        new_status, note = _refine_verdict_against_citations("partial", [1], refs)
        assert new_status == "needs_info"

    def test_document_evidence_supports_verdict(self, patched):
        # A document chunk citation has no AC/RA/CA backing — it's an
        # uploaded evidence file, treated as supporting.
        patched()
        refs = [_ref(1, kind="document", obj_id="doc-1")]
        new_status, note = _refine_verdict_against_citations("yes", [1], refs)
        assert new_status == "yes"
        assert note == ""

    def test_library_only_treated_as_no_evidence(self, patched):
        # Reference material from a framework — does not justify yes.
        patched()
        refs = [_ref(1, kind="requirement_node", obj_id="rn-1")]
        new_status, note = _refine_verdict_against_citations("yes", [1], refs)
        assert new_status == "needs_info"

    def test_neutral_internal_kind_does_not_downgrade(self, patched):
        # Internal records that aren't status-bearing (evidence, vulnerability,
        # incident, asset, …) should be neutral — they shouldn't push a "yes"
        # to "needs_info" just because they don't fit the AC/RA/CA buckets.
        patched()
        for neutral_kind in ("evidence", "vulnerability", "incident", "asset"):
            refs = [_ref(1, kind=neutral_kind, obj_id=f"x-{neutral_kind}")]
            new_status, _ = _refine_verdict_against_citations("yes", [1], refs)
            assert new_status == "yes", (
                f"kind={neutral_kind!r} should not trigger a downgrade"
            )

    def test_compliance_assessment_in_progress_supports_partial(self, patched):
        patched(ca_map={"ca-1": _FakeCA("in_progress")})
        refs = [_ref(1, obj_id="ca-1")]
        new_status, note = _refine_verdict_against_citations("partial", [1], refs)
        assert new_status == "partial"
        assert note == ""

    def test_no_verdict_never_modified(self, patched):
        patched(ac_map={"ac-1": _FakeAC("to_do")})
        refs = [_ref(1, obj_id="ac-1")]
        new_status, _ = _refine_verdict_against_citations("no", [1], refs)
        assert new_status == "no"

    def test_needs_info_never_modified(self, patched):
        patched(ac_map={"ac-1": _FakeAC("active")})
        refs = [_ref(1, obj_id="ac-1")]
        new_status, _ = _refine_verdict_against_citations("needs_info", [1], refs)
        # Refiner only downgrades — needs_info is the floor.
        assert new_status == "needs_info"

    def test_mix_active_and_to_do_keeps_yes(self, patched):
        # If at least one citation is active, yes is supported.
        patched(
            ac_map={
                "ac-1": _FakeAC("active"),
                "ac-2": _FakeAC("to_do"),
            }
        )
        refs = [_ref(1, obj_id="ac-1"), _ref(2, obj_id="ac-2")]
        new_status, _ = _refine_verdict_against_citations("yes", [1, 2], refs)
        assert new_status == "yes"
