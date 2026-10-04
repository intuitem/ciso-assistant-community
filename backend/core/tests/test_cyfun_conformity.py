"""CCB conformity criteria (CAS) as outcomes of the CyFun 2025 library: the
verdict comes from library rules evaluated on the audit's scores. Each
criterion is an outcome that fires when met, so a conformant audit shows them
all, with the summary."""

import pytest

from core.cel_service import evaluate_outcomes
from core.cyfun import CYFUN_2025_URN
from core.models import (
    ComplianceAssessment,
    Framework,
    RequirementAssessment,
    StoredLibrary,
)
from core.serializers import ComplianceAssessmentWriteSerializer
from iam.models import Folder

MET = "cyfun-conformity-criteria-met"
TOTAL = "cyfun-total-maturity-target-met"
KEY_MEASURES = "cyfun-key-measure-targets-met"
CATEGORIES = "cyfun-category-targets-met"
EXCLUSIONS = "cyfun-exclusions-within-rules"
CRITERIA = {TOTAL, KEY_MEASURES, CATEGORIES, EXCLUSIONS}


@pytest.fixture
def framework():
    """The shipped library, stored with the others when the test database is
    set up."""
    stored = StoredLibrary.objects.get(urn="urn:intuitem:risk:library:ccb-cyfun2025")
    assert stored.load() is None
    return Framework.objects.get(urn=CYFUN_2025_URN)


def _audit(framework, groups):
    serializer = ComplianceAssessmentWriteSerializer(
        data={
            "name": "CyFun audit",
            "folder": str(Folder.get_root_folder().id),
            "framework": str(framework.id),
            "selected_implementation_groups": groups,
        }
    )
    assert serializer.is_valid(), serializer.errors
    audit = serializer.save()
    audit.create_requirement_assessments()
    return audit


def _in_scope(audit, group=None):
    """The audit's requirement assessments, or those of one group."""
    groups = {group} if group else set(audit.selected_implementation_groups or ["E"])
    return [
        ra
        for ra in RequirementAssessment.objects.filter(
            compliance_assessment=audit, requirement__assessable=True
        ).select_related("requirement")
        if groups & set(ra.requirement.implementation_groups or [])
    ]


def _score(requirement_assessments, score, documentation_score=None):
    for ra in requirement_assessments:
        ra.is_scored = True
        ra.score = score
        ra.documentation_score = (
            score if documentation_score is None else documentation_score
        )
        ra.result = RequirementAssessment.Result.COMPLIANT
        ra.save()


def _not_applicable(requirement_assessments):
    for ra in requirement_assessments:
        ra.result = RequirementAssessment.Result.NOT_APPLICABLE
        ra.save()


def _unmet(computed_outcome):
    """The criteria an audit misses: the summary fires only without any."""
    fired = set(computed_outcome or {})
    unmet = CRITERIA - fired
    assert (MET in fired) == (not unmet)
    return unmet


def _verdict(audit):
    evaluate_outcomes(audit)
    audit.refresh_from_db()
    return _unmet(audit.computed_outcome)


@pytest.mark.django_db
class TestBasic:
    def test_criteria_met_at_the_level_target(self, framework):
        audit = _audit(framework, ["B"])
        _score(_in_scope(audit), 3, documentation_score=2)  # key measures at 2.5
        assert _verdict(audit) == set()

    def test_key_measure_below_target(self, framework):
        audit = _audit(framework, ["B"])
        _score(_in_scope(audit), 4)
        _score(_in_scope(audit, "BK")[:1], 2)
        assert _verdict(audit) == {KEY_MEASURES}

    def test_total_maturity_below_target(self, framework):
        audit = _audit(framework, ["B"])
        others = [
            ra
            for ra in _in_scope(audit)
            if "BK" not in ra.requirement.implementation_groups
        ]
        _score(_in_scope(audit, "BK"), 3)
        _score(others, 1)
        assert _verdict(audit) == {TOTAL}

    def test_one_exclusion_counts_as_the_target(self, framework):
        """An N/A requirement counts as 2.5, the BASIC key measure target."""
        audit = _audit(framework, ["B"])
        others = [
            ra
            for ra in _in_scope(audit)
            if "BK" not in ra.requirement.implementation_groups
        ]
        _score(_in_scope(audit), 3)
        _not_applicable(others[:1])
        assert _verdict(audit) == set()

    def test_second_exclusion_is_too_many(self, framework):
        audit = _audit(framework, ["B"])
        others = [
            ra
            for ra in _in_scope(audit)
            if "BK" not in ra.requirement.implementation_groups
        ]
        _score(_in_scope(audit), 3)
        _not_applicable(others[:2])
        assert _verdict(audit) == {EXCLUSIONS}

    def test_key_measures_cannot_be_excluded(self, framework):
        audit = _audit(framework, ["B"])
        _score(_in_scope(audit), 3)
        _not_applicable(_in_scope(audit, "BK")[:1])
        assert EXCLUSIONS in _verdict(audit)


@pytest.mark.django_db
class TestScope:
    def test_partial_scope_is_not_a_full_level(self, framework):
        """Key measures alone pass each check, but are not a BASIC audit."""
        audit = _audit(framework, ["BK"])
        _score(_in_scope(audit), 4)
        evaluate_outcomes(audit)
        audit.refresh_from_db()
        fired = set(audit.computed_outcome)
        assert fired >= CRITERIA
        assert MET not in fired


@pytest.mark.django_db
class TestImportantAndEssential:
    def test_important_key_measures_need_3(self, framework):
        audit = _audit(framework, ["I"])
        _score(_in_scope(audit), 4)
        _score(_in_scope(audit, "IK")[:1], 3, documentation_score=2)
        assert _verdict(audit) == {KEY_MEASURES}

    def test_essential_needs_3_5_in_total(self, framework):
        audit = _audit(framework, [])
        _score(_in_scope(audit), 3)
        assert _verdict(audit) == {TOTAL}

    def test_essential_category_below_3(self, framework):
        audit = _audit(framework, ["E"])
        _score(_in_scope(audit), 4)
        assert _verdict(audit) == set()

        # A category without key measures, scored 1 throughout: the total
        # stays above 3.5.
        by_category = {}
        for ra in _in_scope(audit):
            category = ra.requirement.ref_id.split("-")[0]
            by_category.setdefault(category, []).append(ra)
        category = next(
            ras
            for ras in by_category.values()
            if not any("EK" in ra.requirement.implementation_groups for ra in ras)
        )
        _score(category, 1)
        assert _verdict(audit) == {CATEGORIES}

    def test_essential_management_aspects_cannot_be_excluded(self, framework):
        audit = _audit(framework, ["E"])
        _score(_in_scope(audit), 4)
        _not_applicable(
            [
                ra
                for ra in _in_scope(audit, "EG")
                if "EK" not in ra.requirement.implementation_groups
            ][:1]
        )
        assert _verdict(audit) == {EXCLUSIONS}


@pytest.mark.django_db(transaction=True)
class TestReevaluation:
    """The verdict follows the scores without an explicit evaluation."""

    def test_documentation_score_change(self, framework):
        audit = _audit(framework, ["B"])
        _score(_in_scope(audit), 3)
        ra = _in_scope(audit, "BK")[0]
        ra.documentation_score = 1
        ra.save()
        audit.refresh_from_db()
        assert _unmet(audit.computed_outcome) == {KEY_MEASURES}

    def test_audit_settings_change(self, framework):
        audit = _audit(framework, ["B"])
        _score(_in_scope(audit), 3)
        audit.refresh_from_db()
        assert _unmet(audit.computed_outcome) == set()

        # IMPORTANT: its requirements are unscored, so its target is missed.
        audit = ComplianceAssessment.objects.get(pk=audit.pk)
        audit.selected_implementation_groups = ["I"]
        audit.save()
        audit.refresh_from_db()
        assert MET not in audit.computed_outcome
