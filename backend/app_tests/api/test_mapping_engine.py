"""
Unit tests for the MappingEngine class.

These tests exercise map_audit_results, best_mapping_inferences, and
_most_restrictive_result using plain dicts — no database required.
"""

import pytest
from collections import defaultdict
from unittest.mock import patch, MagicMock

# Patch DB access before importing the module (module-level `engine = MappingEngine()`)
with (
    patch("core.models.Framework.objects") as _fw_mock,
    patch("core.models.StoredLibrary.objects") as _sl_mock,
):
    _fw_mock.all.return_value = []
    _sl_mock.filter.return_value = []
    from core.mappings.engine import MappingEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine(**overrides) -> MappingEngine:
    """Build a MappingEngine without hitting the DB."""
    engine = object.__new__(MappingEngine)
    engine.all_rms = {}
    engine.framework_mappings = defaultdict(list)
    engine.frameworks = {}
    engine.direct_mappings = set()
    engine.fields_to_map = [
        "result",
        "status",
        "score",
        "is_scored",
        "observation",
        "documentation_score",
    ]
    engine.m2m_fields = [
        "applied_controls",
        "security_exceptions",
        "evidences",
    ]
    for k, v in overrides.items():
        setattr(engine, k, v)
    return engine


def _source_audit(
    requirement_assessments: dict,
    min_score: int = 0,
    max_score: int = 100,
) -> dict:
    ra = defaultdict(dict)
    ra.update(requirement_assessments)
    return {
        "min_score": min_score,
        "max_score": max_score,
        "requirement_assessments": ra,
    }


def _rms(
    source_framework_urn: str = "urn:fw:A",
    target_framework_urn: str = "urn:fw:B",
    requirement_mappings: list[dict] | None = None,
    **extra,
) -> dict:
    return {
        "source_framework_urn": source_framework_urn,
        "target_framework_urn": target_framework_urn,
        "requirement_mappings": requirement_mappings or [],
        "urn": extra.get("urn", "urn:rms:A-to-B"),
        "name": extra.get("name", "A to B mapping"),
        "ref_id": extra.get("ref_id", "RMS-001"),
        "id": extra.get("id", "lib-uuid-1"),
        "library_urn": extra.get("library_urn", "urn:lib:test"),
    }


# ---------------------------------------------------------------------------
# T10 / T11 / T12 — _most_restrictive_result
# ---------------------------------------------------------------------------


class TestMostRestrictiveResult:
    def setup_method(self):
        self.engine = _make_engine()

    def test_non_compliant_beats_compliant(self):
        assert (
            self.engine._most_restrictive_result("non_compliant", "compliant")
            == "non_compliant"
        )

    def test_none_vs_anything(self):
        assert self.engine._most_restrictive_result(None, "compliant") == "compliant"
        assert (
            self.engine._most_restrictive_result("non_compliant", None)
            == "non_compliant"
        )

    def test_partially_compliant_beats_compliant(self):
        assert (
            self.engine._most_restrictive_result("partially_compliant", "compliant")
            == "partially_compliant"
        )

    def test_both_none(self):
        assert self.engine._most_restrictive_result(None, None) is None


# ---------------------------------------------------------------------------
# T1–T7 — map_audit_results
# ---------------------------------------------------------------------------


class TestMapAuditResults:
    def setup_method(self):
        self.engine = _make_engine(
            frameworks={
                "urn:fw:A": {"min_score": 0, "max_score": 100},
                "urn:fw:B": {"min_score": 0, "max_score": 100},
            }
        )

    # T1: equal, scores_compatible, first encounter → full copy
    def test_equal_scores_compatible_first_encounter(self):
        src_ra = {
            "result": "compliant",
            "status": "done",
            "score": 80,
            "is_scored": True,
            "observation": "All good",
            "documentation_score": 90,
            "applied_controls": ["ctrl-1"],
            "security_exceptions": [],
            "evidences": ["ev-1"],
            "name": "RA-src",
            "id": "ra-src-id",
            "source_framework": {"id": "fw-a-id", "name": "Framework A"},
        }

        source = _source_audit({"urn:req:A1": src_ra})
        rms = _rms(
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:A1",
                    "target_requirement_urn": "urn:req:B1",
                    "relationship": "equal",
                }
            ]
        )

        result = self.engine.map_audit_results(
            source, rms, hop_index=1, path=["urn:fw:A", "urn:fw:B"]
        )

        target_ra = result["requirement_assessments"]["urn:req:B1"]
        assert target_ra["result"] == "compliant"
        assert target_ra["status"] == "done"
        assert target_ra["score"] == 80
        assert target_ra["is_scored"] is True
        assert target_ra["observation"] == "All good"
        assert target_ra["applied_controls"] == ["ctrl-1"]
        assert target_ra["evidences"] == ["ev-1"]

    # T2: equal, scores NOT compatible → score fields excluded
    def test_equal_scores_not_compatible(self):
        engine = _make_engine(
            frameworks={
                "urn:fw:A": {"min_score": 0, "max_score": 100},
                "urn:fw:B": {"min_score": 0, "max_score": 10},  # different range
            }
        )

        src_ra = {
            "result": "compliant",
            "status": "done",
            "score": 80,
            "is_scored": True,
            "observation": "Obs",
            "documentation_score": 90,
            "applied_controls": ["ctrl-1"],
            "security_exceptions": [],
            "evidences": [],
            "name": "RA-src",
            "id": "ra-src-id",
            "source_framework": {"id": "fw-a-id", "name": "Framework A"},
        }

        source = _source_audit({"urn:req:A1": src_ra})
        rms = _rms(
            target_framework_urn="urn:fw:B",
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:A1",
                    "target_requirement_urn": "urn:req:B1",
                    "relationship": "equal",
                }
            ],
        )

        result = engine.map_audit_results(
            source, rms, hop_index=1, path=["urn:fw:A", "urn:fw:B"]
        )

        target_ra = result["requirement_assessments"]["urn:req:B1"]
        assert target_ra["result"] == "compliant"
        assert target_ra["status"] == "done"
        assert target_ra["observation"] == "Obs"
        # Score fields must not be copied
        assert "score" not in target_ra or target_ra.get("score") is None
        assert "is_scored" not in target_ra or target_ra.get("is_scored") is None

    # T3: subset relationship → partially_compliant
    def test_subset_relationship(self):
        src_ra = {
            "result": "compliant",
            "status": "done",
            "score": 80,
            "is_scored": True,
            "observation": "OK",
            "documentation_score": 0,
            "applied_controls": ["ctrl-1", "ctrl-2"],
            "security_exceptions": [],
            "evidences": [],
            "name": "RA-src",
            "id": "ra-src-id",
            "source_framework": {"id": "fw-a-id", "name": "Framework A"},
        }

        source = _source_audit({"urn:req:A1": src_ra})
        rms = _rms(
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:A1",
                    "target_requirement_urn": "urn:req:B1",
                    "relationship": "subset",
                }
            ]
        )

        result = self.engine.map_audit_results(
            source, rms, hop_index=1, path=["urn:fw:A", "urn:fw:B"]
        )

        target_ra = result["requirement_assessments"]["urn:req:B1"]
        assert target_ra["result"] == "partially_compliant"
        assert set(target_ra["applied_controls"]) == {"ctrl-1", "ctrl-2"}

    # T4: collision — two sources to same target (equal)
    def test_collision_two_sources_equal(self):
        src_ra1 = {
            "result": "compliant",
            "status": "done",
            "score": 80,
            "is_scored": True,
            "observation": "First",
            "documentation_score": 80,
            "applied_controls": ["ctrl-1"],
            "security_exceptions": [],
            "evidences": ["ev-1"],
            "name": "RA-src-1",
            "id": "ra-1-id",
            "source_framework": {"id": "fw-a-id", "name": "Framework A"},
        }
        src_ra2 = {
            "result": "non_compliant",
            "status": "in_progress",
            "score": 20,
            "is_scored": True,
            "observation": "Second",
            "documentation_score": 20,
            "applied_controls": ["ctrl-2"],
            "security_exceptions": ["se-1"],
            "evidences": ["ev-2"],
            "name": "RA-src-2",
            "id": "ra-2-id",
            "source_framework": {"id": "fw-a-id", "name": "Framework A"},
        }

        source = _source_audit({"urn:req:A1": src_ra1, "urn:req:A2": src_ra2})
        rms = _rms(
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:A1",
                    "target_requirement_urn": "urn:req:B1",
                    "relationship": "equal",
                },
                {
                    "source_requirement_urn": "urn:req:A2",
                    "target_requirement_urn": "urn:req:B1",
                    "relationship": "equal",
                },
            ]
        )

        result = self.engine.map_audit_results(
            source, rms, hop_index=1, path=["urn:fw:A", "urn:fw:B"]
        )

        target_ra = result["requirement_assessments"]["urn:req:B1"]
        # Most restrictive result wins
        assert target_ra["result"] == "non_compliant"
        # M2M fields are merged (union)
        assert set(target_ra["applied_controls"]) == {"ctrl-1", "ctrl-2"}
        assert set(target_ra["evidences"]) == {"ev-1", "ev-2"}
        assert set(target_ra["security_exceptions"]) == {"se-1"}

    # T5: source requirement NOT in source audit → skipped entirely
    def test_missing_source_requirement_skipped(self):
        source = _source_audit(
            {
                "urn:req:A1": {
                    "result": "compliant",
                    "status": "done",
                    "score": 0,
                    "is_scored": False,
                    "observation": "",
                    "documentation_score": 0,
                    "applied_controls": [],
                    "security_exceptions": [],
                    "evidences": [],
                    "name": "RA-src",
                    "id": "ra-src-id",
                    "source_framework": {"id": "fw-a-id", "name": "Framework A"},
                }
            }
        )
        rms = _rms(
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:NONEXISTENT",
                    "target_requirement_urn": "urn:req:B1",
                    "relationship": "equal",
                }
            ]
        )

        result = self.engine.map_audit_results(
            source, rms, hop_index=1, path=["urn:fw:A", "urn:fw:B"]
        )

        # urn:req:B1 should NOT be in the target (no data to copy)
        ra_dict = result.get("requirement_assessments", {})
        assert "urn:req:B1" not in ra_dict or ra_dict["urn:req:B1"] == {}
        # Also, urn:req:NONEXISTENT must not have been auto-created in source
        assert "urn:req:NONEXISTENT" not in source["requirement_assessments"]

    # T6: mapping_inference populated correctly (hop_index=1)
    def test_mapping_inference_populated(self):
        src_ra = {
            "result": "compliant",
            "status": "done",
            "score": 85,
            "is_scored": True,
            "observation": "",
            "documentation_score": 0,
            "applied_controls": [],
            "security_exceptions": [],
            "evidences": [],
            "name": "RA-src",
            "id": "ra-src-id",
            "source_framework": {"id": "fw-a-id", "name": "Framework A"},
        }
        source = _source_audit({"urn:req:A1": src_ra})
        rms = _rms(
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:A1",
                    "target_requirement_urn": "urn:req:B1",
                    "relationship": "equal",
                }
            ]
        )

        result = self.engine.map_audit_results(
            source, rms, hop_index=1, path=["urn:fw:A", "urn:fw:B"]
        )

        target_ra = result["requirement_assessments"]["urn:req:B1"]
        mi = target_ra["mapping_inference"]
        assert "source_requirement_assessments" in mi
        src_ras = mi["source_requirement_assessments"]
        assert "urn:req:A1" in src_ras
        assert src_ras["urn:req:A1"]["coverage"] == "full"
        assert src_ras["urn:req:A1"]["id"] == "ra-src-id"
        assert mi["result"] == "compliant"

    # T7: not_related relationship → skipped
    def test_not_related_skipped(self):
        src_ra = {
            "result": "compliant",
            "status": "done",
            "score": 0,
            "is_scored": False,
            "observation": "",
            "documentation_score": 0,
            "applied_controls": [],
            "security_exceptions": [],
            "evidences": [],
            "name": "RA-src",
            "id": "ra-src-id",
            "source_framework": {"id": "fw-a-id", "name": "Framework A"},
        }
        source = _source_audit({"urn:req:A1": src_ra})
        rms = _rms(
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:A1",
                    "target_requirement_urn": "urn:req:B1",
                    "relationship": "not_related",
                }
            ]
        )

        result = self.engine.map_audit_results(
            source, rms, hop_index=1, path=["urn:fw:A", "urn:fw:B"]
        )

        ra_dict = result.get("requirement_assessments", {})
        # Should be empty or have no meaningful data
        assert "urn:req:B1" not in ra_dict or ra_dict.get("urn:req:B1") == {}


# ---------------------------------------------------------------------------
# T8 / T9 — best_mapping_inferences
# ---------------------------------------------------------------------------


class TestBestMappingInferences:
    def _build_engine_with_rms(self, rms_list):
        """Build engine with pre-loaded RMS entries."""
        engine = _make_engine()
        for r in rms_list:
            src_fw = r["source_framework_urn"]
            tgt_fw = r["target_framework_urn"]
            engine.all_rms[(src_fw, tgt_fw)] = engine._compress_rms(r)
            engine.framework_mappings[src_fw].append(tgt_fw)
            engine.direct_mappings.add((src_fw, tgt_fw))
        return engine

    # T8: multi-hop A→B→C
    def test_multi_hop_mapping(self):
        rms_ab = _rms(
            source_framework_urn="urn:fw:A",
            target_framework_urn="urn:fw:B",
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:A1",
                    "target_requirement_urn": "urn:req:B1",
                    "relationship": "equal",
                }
            ],
            urn="urn:rms:AB",
            name="A to B",
        )
        rms_bc = _rms(
            source_framework_urn="urn:fw:B",
            target_framework_urn="urn:fw:C",
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:B1",
                    "target_requirement_urn": "urn:req:C1",
                    "relationship": "equal",
                }
            ],
            urn="urn:rms:BC",
            name="B to C",
        )

        engine = self._build_engine_with_rms([rms_ab, rms_bc])
        engine.frameworks = {
            "urn:fw:A": {"min_score": 0, "max_score": 100},
            "urn:fw:B": {"min_score": 0, "max_score": 100},
            "urn:fw:C": {"min_score": 0, "max_score": 100},
        }

        source = _source_audit(
            {
                "urn:req:A1": {
                    "result": "compliant",
                    "status": "done",
                    "score": 90,
                    "is_scored": True,
                    "observation": "OK",
                    "documentation_score": 0,
                    "applied_controls": ["ctrl-1"],
                    "security_exceptions": [],
                    "evidences": [],
                    "name": "RA from A",
                    "id": "ra-a1-id",
                    "source_framework": {"id": "fw-a-id", "name": "Framework A"},
                }
            }
        )

        inferences, best_path = engine.best_mapping_inferences(
            source, "urn:fw:A", "urn:fw:C"
        )

        assert best_path == ["urn:fw:A", "urn:fw:B", "urn:fw:C"]
        target_ra = inferences["requirement_assessments"]["urn:req:C1"]
        assert target_ra["result"] == "compliant"
        # The inference at C1 should have A1's info propagated through
        mi = target_ra["mapping_inference"]
        src_ras = mi["source_requirement_assessments"]
        assert "urn:req:A1" in src_ras
        # The intermediate B1 requirement should also appear with its
        # own mapping set (the B→C hop).
        assert "urn:req:B1" in src_ras
        assert src_ras["urn:req:B1"]["used_mapping_set"]["urn"] == "urn:rms:BC"

    # T9: indirect path found when no direct path exists
    def test_indirect_path_when_no_direct(self):
        # No direct A→D, only A→C→D
        rms_ac = _rms(
            source_framework_urn="urn:fw:A",
            target_framework_urn="urn:fw:C",
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:A1",
                    "target_requirement_urn": "urn:req:C1",
                    "relationship": "equal",
                }
            ],
            urn="urn:rms:AC",
            name="A to C",
        )
        rms_cd = _rms(
            source_framework_urn="urn:fw:C",
            target_framework_urn="urn:fw:D",
            requirement_mappings=[
                {
                    "source_requirement_urn": "urn:req:C1",
                    "target_requirement_urn": "urn:req:D1",
                    "relationship": "equal",
                },
                {
                    "source_requirement_urn": "urn:req:C1",
                    "target_requirement_urn": "urn:req:D2",
                    "relationship": "equal",
                },
            ],
            urn="urn:rms:CD",
            name="C to D",
        )

        engine = self._build_engine_with_rms([rms_ac, rms_cd])
        engine.frameworks = {
            "urn:fw:A": {"min_score": 0, "max_score": 100},
            "urn:fw:C": {"min_score": 0, "max_score": 100},
            "urn:fw:D": {"min_score": 0, "max_score": 100},
        }

        source = _source_audit(
            {
                "urn:req:A1": {
                    "result": "compliant",
                    "status": "done",
                    "score": 80,
                    "is_scored": True,
                    "observation": "",
                    "documentation_score": 0,
                    "applied_controls": [],
                    "security_exceptions": [],
                    "evidences": [],
                    "name": "RA from A",
                    "id": "ra-a1-id",
                    "source_framework": {"id": "fw-a-id", "name": "Framework A"},
                }
            }
        )

        inferences, best_path = engine.best_mapping_inferences(
            source, "urn:fw:A", "urn:fw:D", max_depth=3
        )

        assert best_path == ["urn:fw:A", "urn:fw:C", "urn:fw:D"]
        assert "urn:req:D1" in inferences["requirement_assessments"]
        assert "urn:req:D2" in inferences["requirement_assessments"]
