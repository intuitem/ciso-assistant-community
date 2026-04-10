import pytest

from core.models import (
    ComplianceAssessment,
    Framework,
    RequirementNode,
    RequirementAssessment,
    Perimeter,
)
from iam.models import Folder


@pytest.fixture
def scoring_setup():
    """
    Creates a lightweight framework with two parent sections, each containing
    assessable requirement nodes, plus a compliance assessment and its
    requirement assessments.

    Structure:
        Section A (parent, non-assessable)
            ├── Req A1 (assessable, weight=1)
            └── Req A2 (assessable, weight=1)
        Section B (parent, non-assessable)
            ├── Req B1 (assessable, weight=1)
            └── Req B2 (assessable, weight=3)
    """
    root_folder = Folder.get_root_folder()
    folder = Folder.objects.create(
        parent_folder=root_folder,
        name="scoring test folder",
    )
    perimeter = Perimeter.objects.create(name="scoring test perimeter", folder=folder)

    framework = Framework.objects.create(
        name="Scoring Test Framework",
        urn="urn:test:scoring-framework",
        min_score=0,
        max_score=100,
        folder=root_folder,
    )

    # Parent sections (non-assessable)
    section_a = RequirementNode.objects.create(
        name="Section A",
        urn="urn:test:section-a",
        ref_id="A",
        framework=framework,
        assessable=False,
        folder=root_folder,
    )
    section_b = RequirementNode.objects.create(
        name="Section B",
        urn="urn:test:section-b",
        ref_id="B",
        framework=framework,
        assessable=False,
        folder=root_folder,
    )

    # Assessable requirements under Section A
    req_a1 = RequirementNode.objects.create(
        name="Requirement A1",
        urn="urn:test:req-a1",
        ref_id="A.1",
        framework=framework,
        parent_urn=section_a.urn,
        assessable=True,
        weight=1,
        folder=root_folder,
    )
    req_a2 = RequirementNode.objects.create(
        name="Requirement A2",
        urn="urn:test:req-a2",
        ref_id="A.2",
        framework=framework,
        parent_urn=section_a.urn,
        assessable=True,
        weight=1,
        folder=root_folder,
    )

    # Assessable requirements under Section B
    req_b1 = RequirementNode.objects.create(
        name="Requirement B1",
        urn="urn:test:req-b1",
        ref_id="B.1",
        framework=framework,
        parent_urn=section_b.urn,
        assessable=True,
        weight=1,
        folder=root_folder,
    )
    req_b2 = RequirementNode.objects.create(
        name="Requirement B2",
        urn="urn:test:req-b2",
        ref_id="B.2",
        framework=framework,
        parent_urn=section_b.urn,
        assessable=True,
        weight=3,
        folder=root_folder,
    )

    ca = ComplianceAssessment.objects.create(
        name="Scoring Test Assessment",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        min_score=0,
        max_score=100,
    )

    # Create requirement assessments manually
    ra_a1 = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req_a1,
        folder=folder,
        is_scored=True,
        score=80,
    )
    ra_a2 = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req_a2,
        folder=folder,
        is_scored=True,
        score=60,
    )
    ra_b1 = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req_b1,
        folder=folder,
        is_scored=True,
        score=40,
    )
    ra_b2 = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req_b2,
        folder=folder,
        is_scored=True,
        score=100,
    )

    return {
        "ca": ca,
        "ra_a1": ra_a1,
        "ra_a2": ra_a2,
        "ra_b1": ra_b1,
        "ra_b2": ra_b2,
    }


@pytest.mark.django_db
class TestScoringCalculationMethods:
    """Tests for the three score calculation methods: AVG, SUM, AVG_OF_AVG."""

    def test_avg_returns_weighted_average(self, scoring_setup):
        """
        AVG: weighted average = Σ(score × weight) / Σ(weight)

        Scores: A1=80 (w=1), A2=60 (w=1), B1=40 (w=1), B2=100 (w=3)
        = (80 + 60 + 40 + 300) / 6 = 80.0
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()

        scores = ca.get_global_score()
        assert scores["implementation_score"] == 80.0
        assert scores["documentation_score"] is None  # doc scoring not enabled
        assert scores["maturity_score"] == 80.0  # same as impl when doc off

    def test_sum_returns_weighted_sum(self, scoring_setup):
        """
        SUM: weighted sum = Σ(score × weight)
        = 80 + 60 + 40 + 300 = 480.0
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.save()

        scores = ca.get_global_score()
        assert scores["implementation_score"] == 480.0

    def test_avg_of_avg_returns_average_of_group_averages(self, scoring_setup):
        """
        AVG_OF_AVG: average of per-parent weighted averages.

        Section A: (80×1 + 60×1) / (1+1) = 70.0
        Section B: (40×1 + 100×3) / (1+3) = 85.0
        Average of averages: (70 + 85) / 2 = 77.5
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()

        scores = ca.get_global_score()
        assert scores["implementation_score"] == 77.5

    def test_avg_of_avg_gives_equal_weight_to_sections(self, scoring_setup):
        """
        AVG_OF_AVG should give equal weight to each section, regardless of
        how many requirements it has.
        """
        ca = scoring_setup["ca"]

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        avg_score = ca.get_global_score()["implementation_score"]

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()
        avg_of_avg_score = ca.get_global_score()["implementation_score"]

        assert avg_score != avg_of_avg_score
        assert avg_score == 80.0
        assert avg_of_avg_score == 77.5

    def test_not_applicable_excluded_from_all_methods(self, scoring_setup):
        """Requirements with NOT_APPLICABLE result should be excluded."""
        ca = scoring_setup["ca"]
        ra_b2 = scoring_setup["ra_b2"]

        ra_b2.result = RequirementAssessment.Result.NOT_APPLICABLE
        ra_b2.save()

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        assert ca.get_global_score()["implementation_score"] == 60.0

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.save()
        assert ca.get_global_score()["implementation_score"] == 180.0

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()
        assert ca.get_global_score()["implementation_score"] == 55.0

    def test_unscored_excluded_from_all_methods(self, scoring_setup):
        """Requirements with is_scored=False should be excluded."""
        ca = scoring_setup["ca"]
        ra_a2 = scoring_setup["ra_a2"]

        RequirementAssessment.objects.filter(pk=ra_a2.pk).update(is_scored=False)

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        assert ca.get_global_score()["implementation_score"] == 84.0

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()
        assert ca.get_global_score()["implementation_score"] == 82.5

    def test_no_scored_requirements_returns_minus_one(self, scoring_setup):
        """All methods should return -1 when there are no scored requirements."""
        ca = scoring_setup["ca"]

        RequirementAssessment.objects.filter(compliance_assessment=ca).update(
            is_scored=False
        )

        for method in [
            ComplianceAssessment.CalculationMethod.AVG,
            ComplianceAssessment.CalculationMethod.SUM,
            ComplianceAssessment.CalculationMethod.AVG_OF_AVG,
        ]:
            ca.score_calculation_method = method
            ca.save()
            scores = ca.get_global_score()
            assert scores["implementation_score"] == -1, f"Expected -1 for {method}"
            assert scores["maturity_score"] == -1


@pytest.fixture
def deep_tree_setup():
    """
    Creates a 4-level framework tree mimicking CyFun structure:

        Function F1 (root, non-assessable)
            ├── Category C1 (non-assessable)
            │     ├── Subcategory S1 (non-assessable)
            │     │     ├── Req R1 (assessable, score=80)
            │     │     └── Req R2 (assessable, score=60)
            │     └── Subcategory S2 (non-assessable)
            │           └── Req R3 (assessable, score=40)
            └── Category C2 (non-assessable)
                  └── Subcategory S3 (non-assessable)
                        └── Req R4 (assessable, score=100)
        Function F2 (root, non-assessable)
            └── Category C3 (non-assessable)
                  └── Subcategory S4 (non-assessable)
                        └── Req R5 (assessable, score=50)

    Expected AVG_OF_AVG (recursive):
        S1 = avg(80, 60) = 70
        S2 = 40
        C1 = avg(70, 40) = 55
        S3 = 100
        C2 = 100
        F1 = avg(55, 100) = 77.5
        S4 = 50
        C3 = 50
        F2 = 50
        Global = avg(77.5, 50) = 63.7 (truncated from 63.75)
    """
    root_folder = Folder.get_root_folder()
    folder = Folder.objects.create(
        parent_folder=root_folder,
        name="deep tree test folder",
    )
    perimeter = Perimeter.objects.create(name="deep tree test perimeter", folder=folder)

    framework = Framework.objects.create(
        name="Deep Tree Test Framework",
        urn="urn:test:deep-tree-framework",
        min_score=0,
        max_score=100,
        folder=root_folder,
    )

    # Functions (roots)
    RequirementNode.objects.create(
        name="Function F1",
        urn="urn:test:f1",
        ref_id="F1",
        framework=framework,
        assessable=False,
        folder=root_folder,
    )
    RequirementNode.objects.create(
        name="Function F2",
        urn="urn:test:f2",
        ref_id="F2",
        framework=framework,
        assessable=False,
        folder=root_folder,
    )

    # Categories
    RequirementNode.objects.create(
        name="Category C1",
        urn="urn:test:c1",
        ref_id="C1",
        framework=framework,
        parent_urn="urn:test:f1",
        assessable=False,
        folder=root_folder,
    )
    RequirementNode.objects.create(
        name="Category C2",
        urn="urn:test:c2",
        ref_id="C2",
        framework=framework,
        parent_urn="urn:test:f1",
        assessable=False,
        folder=root_folder,
    )
    RequirementNode.objects.create(
        name="Category C3",
        urn="urn:test:c3",
        ref_id="C3",
        framework=framework,
        parent_urn="urn:test:f2",
        assessable=False,
        folder=root_folder,
    )

    # Subcategories
    RequirementNode.objects.create(
        name="Subcategory S1",
        urn="urn:test:s1",
        ref_id="S1",
        framework=framework,
        parent_urn="urn:test:c1",
        assessable=False,
        folder=root_folder,
    )
    RequirementNode.objects.create(
        name="Subcategory S2",
        urn="urn:test:s2",
        ref_id="S2",
        framework=framework,
        parent_urn="urn:test:c1",
        assessable=False,
        folder=root_folder,
    )
    RequirementNode.objects.create(
        name="Subcategory S3",
        urn="urn:test:s3",
        ref_id="S3",
        framework=framework,
        parent_urn="urn:test:c2",
        assessable=False,
        folder=root_folder,
    )
    RequirementNode.objects.create(
        name="Subcategory S4",
        urn="urn:test:s4",
        ref_id="S4",
        framework=framework,
        parent_urn="urn:test:c3",
        assessable=False,
        folder=root_folder,
    )

    # Assessable requirements
    req_r1 = RequirementNode.objects.create(
        name="Req R1",
        urn="urn:test:r1",
        ref_id="R1",
        framework=framework,
        parent_urn="urn:test:s1",
        assessable=True,
        folder=root_folder,
    )
    req_r2 = RequirementNode.objects.create(
        name="Req R2",
        urn="urn:test:r2",
        ref_id="R2",
        framework=framework,
        parent_urn="urn:test:s1",
        assessable=True,
        folder=root_folder,
    )
    req_r3 = RequirementNode.objects.create(
        name="Req R3",
        urn="urn:test:r3",
        ref_id="R3",
        framework=framework,
        parent_urn="urn:test:s2",
        assessable=True,
        folder=root_folder,
    )
    req_r4 = RequirementNode.objects.create(
        name="Req R4",
        urn="urn:test:r4",
        ref_id="R4",
        framework=framework,
        parent_urn="urn:test:s3",
        assessable=True,
        folder=root_folder,
    )
    req_r5 = RequirementNode.objects.create(
        name="Req R5",
        urn="urn:test:r5",
        ref_id="R5",
        framework=framework,
        parent_urn="urn:test:s4",
        assessable=True,
        folder=root_folder,
    )

    ca = ComplianceAssessment.objects.create(
        name="Deep Tree Test Assessment",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        min_score=0,
        max_score=100,
    )

    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req_r1,
        folder=folder,
        is_scored=True,
        score=80,
    )
    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req_r2,
        folder=folder,
        is_scored=True,
        score=60,
    )
    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req_r3,
        folder=folder,
        is_scored=True,
        score=40,
    )
    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req_r4,
        folder=folder,
        is_scored=True,
        score=100,
    )
    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req_r5,
        folder=folder,
        is_scored=True,
        score=50,
    )

    return {"ca": ca}


@pytest.mark.django_db
class TestDeepTreeAvgOfAvg:
    """Tests for recursive average-of-averages on deep (4-level) trees."""

    def test_recursive_avg_of_avg(self, deep_tree_setup):
        """
        AVG_OF_AVG recurses subcategory→category, then flat-averages categories.

        S1 = avg(80, 60) = 70
        S2 = 40
        C1 = avg(70, 40) = 55
        C2 = 100
        C3 = 50
        Global = avg(C1, C2, C3) = (55 + 100 + 50) / 3 = 68.3
        """
        ca = deep_tree_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()

        scores = ca.get_global_score()
        assert scores["implementation_score"] == 68.3

    def test_flat_avg_differs_from_recursive(self, deep_tree_setup):
        """
        Flat AVG should differ from recursive AVG_OF_AVG on a deep tree.

        Flat AVG = (80+60+40+100+50) / 5 = 66.0
        Recursive AVG_OF_AVG = 68.3
        """
        ca = deep_tree_setup["ca"]

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        avg_score = ca.get_global_score()["implementation_score"]

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()
        avg_of_avg_score = ca.get_global_score()["implementation_score"]

        assert avg_score == 66.0
        assert avg_of_avg_score == 68.3
        assert avg_score != avg_of_avg_score


@pytest.mark.django_db
class TestTotalMaxScore:
    """Tests for get_total_max_score across calculation methods."""

    def test_avg_max_score(self, scoring_setup):
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        assert ca.get_total_max_score() == 100

    def test_avg_of_avg_max_score(self, scoring_setup):
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()
        assert ca.get_total_max_score() == 100

    def test_sum_max_score(self, scoring_setup):
        """SUM max: max_score × Σ(weight) = 100 × (1+1+1+3) = 600"""
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.save()
        assert ca.get_total_max_score() == 600


@pytest.mark.django_db
class TestThreeLayerScoring:
    """Tests for the three-layer scoring: implementation, documentation, maturity."""

    def _set_doc_scores(self, scoring_setup):
        """Helper to set documentation scores on all RAs."""
        scoring_setup["ra_a1"].documentation_score = 90
        scoring_setup["ra_a1"].save()
        scoring_setup["ra_a2"].documentation_score = 70
        scoring_setup["ra_a2"].save()
        scoring_setup["ra_b1"].documentation_score = 50
        scoring_setup["ra_b1"].save()
        scoring_setup["ra_b2"].documentation_score = 80
        scoring_setup["ra_b2"].save()

    def test_without_doc_score_maturity_equals_implementation(self, scoring_setup):
        """When doc scoring is off, maturity_score == implementation_score."""
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()

        scores = ca.get_global_score()
        assert scores["documentation_score"] is None
        assert scores["maturity_score"] == scores["implementation_score"]

    def test_avg_three_layers(self, scoring_setup):
        """
        AVG with doc scoring: implementation and documentation computed independently.

        Implementation: (80+60+40+300)/6 = 80.0
        Documentation:  (90+70+50+80×3)/6 = (90+70+50+240)/6 = 450/6 = 75.0
        Maturity: (80.0 + 75.0) / 2 = 77.5
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.show_documentation_score = True
        ca.save()
        self._set_doc_scores(scoring_setup)

        scores = ca.get_global_score()
        assert scores["implementation_score"] == 80.0
        assert scores["documentation_score"] == 75.0
        assert scores["maturity_score"] == 77.5

    def test_sum_three_layers(self, scoring_setup):
        """
        SUM with doc scoring: each layer summed independently.

        Implementation: 80+60+40+300 = 480
        Documentation:  90+70+50+240 = 450
        Maturity: (480 + 450) / 2 = 465.0
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.show_documentation_score = True
        ca.save()
        self._set_doc_scores(scoring_setup)

        scores = ca.get_global_score()
        assert scores["implementation_score"] == 480.0
        assert scores["documentation_score"] == 450.0
        assert scores["maturity_score"] == 465.0

    def test_avg_of_avg_three_layers(self, scoring_setup):
        """
        AVG_OF_AVG with doc scoring: each layer grouped independently.

        Implementation:
          Section A: (80+60)/2 = 70, Section B: (40+300)/4 = 85
          Average: (70+85)/2 = 77.5

        Documentation:
          Section A: (90+70)/2 = 80, Section B: (50+240)/4 = 72.5
          Average: (80+72.5)/2 = 76.2  (truncated from 76.25)

        Maturity: (77.5 + 76.2) / 2 = 76.85 → truncated to 76.8
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.show_documentation_score = True
        ca.save()
        self._set_doc_scores(scoring_setup)

        scores = ca.get_global_score()
        assert scores["implementation_score"] == 77.5
        assert scores["documentation_score"] == 76.2
        assert scores["maturity_score"] == 76.8

    def test_doc_score_null_treated_as_zero(self, scoring_setup):
        """
        When doc scoring is enabled but documentation_score is null on some RAs,
        those null values should be treated as 0 in the computation.
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.show_documentation_score = True
        ca.save()

        # Only set doc score on A1, leave others null
        scoring_setup["ra_a1"].documentation_score = 60
        scoring_setup["ra_a1"].save()

        scores = ca.get_global_score()
        # Implementation: 80.0 (unchanged)
        assert scores["implementation_score"] == 80.0
        # Documentation: (60×1 + 0×1 + 0×1 + 0×3) / 6 = 10.0
        assert scores["documentation_score"] == 10.0
        # Maturity: (80 + 10) / 2 = 45.0
        assert scores["maturity_score"] == 45.0

    def test_implementation_score_unchanged_by_doc_toggle(self, scoring_setup):
        """
        Enabling documentation scoring should NOT change the implementation score.
        This is the key difference from the old blended approach.
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        self._set_doc_scores(scoring_setup)

        impl_without_doc = ca.get_global_score()["implementation_score"]

        ca.show_documentation_score = True
        ca.save()

        impl_with_doc = ca.get_global_score()["implementation_score"]
        assert impl_without_doc == impl_with_doc == 80.0
