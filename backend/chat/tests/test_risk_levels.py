"""Tests for risk_levels.py — matrix-driven level vocabulary."""

import pytest

from chat.risk_levels import (
    describe_levels,
    known_level_names,
    level_label,
    resolve_levels_by_matrix,
)


class FakeMatrix:
    """Stands in for a RiskMatrix — only id and json_definition are read."""

    def __init__(self, id, risk_defs):
        self.id = id
        self.json_definition = {"risk": risk_defs}


THREE_LEVEL = FakeMatrix(
    "m3",
    [
        {
            "abbreviation": "L",
            "name": "Low",
            "translations": {"fr": {"name": "Faible"}},
        },
        {
            "abbreviation": "M",
            "name": "Medium",
            "translations": {"fr": {"name": "Moyen"}},
        },
        {
            "abbreviation": "H",
            "name": "High",
            "translations": {"fr": {"name": "Élevé"}},
        },
    ],
)

# Real libraries decorate labels with their rank, e.g. the 5x5 ISO-27005 matrix
DECORATED_FIVE_LEVEL = FakeMatrix(
    "m5",
    [
        {"abbreviation": "VL", "name": "1 - very low"},
        {"abbreviation": "L", "name": "2 - low"},
        {"abbreviation": "M", "name": "3 - medium"},
        {"abbreviation": "H", "name": "4 - high"},
        {"abbreviation": "VH", "name": "5 - very high"},
    ],
)


class TestLevelLabel:
    def test_uses_matrix_wording(self):
        assert level_label(THREE_LEVEL, 2, locale="en") == "High"

    def test_uses_translation_when_available(self):
        assert level_label(THREE_LEVEL, 2, locale="fr") == "Élevé"

    def test_falls_back_to_source_name_for_missing_translation(self):
        assert level_label(THREE_LEVEL, 2, locale="de") == "High"

    def test_negative_level_is_not_rated(self):
        assert level_label(THREE_LEVEL, -1, locale="en") == "--"
        assert level_label(THREE_LEVEL, None, locale="en") == "--"

    def test_out_of_range_level_degrades_to_the_index(self):
        assert level_label(THREE_LEVEL, 9, locale="en") == "9"

    def test_missing_matrix_is_not_rated(self):
        assert level_label(None, 2, locale="en") == "--"


class TestResolveLevelsByMatrix:
    def test_matches_name_case_insensitively(self):
        assert resolve_levels_by_matrix("high", [THREE_LEVEL]) == {"m3": {2}}
        assert resolve_levels_by_matrix("HIGH", [THREE_LEVEL]) == {"m3": {2}}

    def test_matches_translated_name(self):
        assert resolve_levels_by_matrix("élevé", [THREE_LEVEL]) == {"m3": {2}}

    def test_matches_abbreviation(self):
        assert resolve_levels_by_matrix("VH", [DECORATED_FIVE_LEVEL]) == {"m5": {4}}

    def test_matches_through_rank_decoration(self):
        assert resolve_levels_by_matrix("high", [DECORATED_FIVE_LEVEL]) == {"m5": {3}}
        assert resolve_levels_by_matrix("very high", [DECORATED_FIVE_LEVEL]) == {
            "m5": {4}
        }

    def test_high_does_not_bleed_into_very_high(self):
        assert resolve_levels_by_matrix("high", [DECORATED_FIVE_LEVEL])["m5"] == {3}

    def test_same_term_maps_to_different_index_per_matrix(self):
        # The whole reason resolution is per-matrix: "high" is 2 in a 3-level
        # scale and 3 in a 5-level one; a shared index set would miscount.
        assert resolve_levels_by_matrix(
            "high", [THREE_LEVEL, DECORATED_FIVE_LEVEL]
        ) == {
            "m3": {2},
            "m5": {3},
        }

    def test_numeric_index_is_accepted(self):
        assert resolve_levels_by_matrix("2", [THREE_LEVEL]) == {"m3": {2}}

    def test_unknown_term_resolves_to_nothing(self):
        assert resolve_levels_by_matrix("catastrophic", [THREE_LEVEL]) == {}

    def test_empty_term_resolves_to_nothing(self):
        assert resolve_levels_by_matrix("", [THREE_LEVEL]) == {}


class TestDescribeLevels:
    def test_orders_lowest_to_highest(self):
        assert describe_levels(THREE_LEVEL, locale="en") == "Low < Medium < High"

    def test_translated(self):
        assert describe_levels(THREE_LEVEL, locale="fr") == "Faible < Moyen < Élevé"

    def test_empty_matrix(self):
        assert describe_levels(FakeMatrix("empty", []), locale="en") == ""


class TestKnownLevelNames:
    def test_deduplicates_across_matrices(self):
        names = known_level_names([THREE_LEVEL, THREE_LEVEL], locale="en")
        assert names == ["Low", "Medium", "High"]


@pytest.mark.django_db
class TestMatricesForScenarios:
    def test_empty_queryset_yields_no_matrices(self):
        from core.models import RiskScenario

        from chat.risk_levels import matrices_for_scenarios

        assert matrices_for_scenarios(RiskScenario.objects.none()) == []
