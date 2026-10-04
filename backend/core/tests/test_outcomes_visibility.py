"""Outcomes have their own field visibility, independent of the result's."""

from core.utils import AUDITOR_ONLY, THIRD_PARTY_VISIBILITY


def test_third_party_audits_hide_outcomes_from_respondents():
    assert THIRD_PARTY_VISIBILITY["outcomes"] == AUDITOR_ONLY
