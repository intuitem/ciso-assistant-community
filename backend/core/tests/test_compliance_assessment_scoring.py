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
    root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
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
        folder=Folder.get_root_folder(),
    )

    # Parent sections (non-assessable)
    section_a = RequirementNode.objects.create(
        name="Section A",
        urn="urn:test:section-a",
        ref_id="A",
        framework=framework,
        assessable=False,
        folder=Folder.get_root_folder(),
    )
    section_b = RequirementNode.objects.create(
        name="Section B",
        urn="urn:test:section-b",
        ref_id="B",
        framework=framework,
        assessable=False,
        folder=Folder.get_root_folder(),
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
        folder=Folder.get_root_folder(),
    )
    req_a2 = RequirementNode.objects.create(
        name="Requirement A2",
        urn="urn:test:req-a2",
        ref_id="A.2",
        framework=framework,
        parent_urn=section_a.urn,
        assessable=True,
        weight=1,
        folder=Folder.get_root_folder(),
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
        folder=Folder.get_root_folder(),
    )
    req_b2 = RequirementNode.objects.create(
        name="Requirement B2",
        urn="urn:test:req-b2",
        ref_id="B.2",
        framework=framework,
        parent_urn=section_b.urn,
        assessable=True,
        weight=3,
        folder=Folder.get_root_folder(),
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
        = (80×1 + 60×1 + 40×1 + 100×3) / (1+1+1+3)
        = (80 + 60 + 40 + 300) / 6
        = 480 / 6 = 80.0
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()

        assert ca.get_global_score() == 80.0

    def test_sum_returns_weighted_sum(self, scoring_setup):
        """
        SUM: weighted sum = Σ(score × weight)

        Scores: A1=80 (w=1), A2=60 (w=1), B1=40 (w=1), B2=100 (w=3)
        = 80 + 60 + 40 + 300 = 480.0
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.save()

        assert ca.get_global_score() == 480.0

    def test_avg_of_avg_returns_average_of_group_averages(self, scoring_setup):
        """
        AVG_OF_AVG: average of per-parent weighted averages.

        Section A: (80×1 + 60×1) / (1+1) = 70.0
        Section B: (40×1 + 100×3) / (1+3) = 340/4 = 85.0
        Average of averages: (70 + 85) / 2 = 77.5
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()

        assert ca.get_global_score() == 77.5

    def test_avg_of_avg_gives_equal_weight_to_sections(self, scoring_setup):
        """
        AVG_OF_AVG should give equal weight to each section, regardless of
        how many requirements it has. Contrast with AVG which is dominated
        by the heavily-weighted B2 requirement.
        """
        ca = scoring_setup["ca"]

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        avg_score = ca.get_global_score()

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()
        avg_of_avg_score = ca.get_global_score()

        # These should differ because B2 has weight=3 and score=100,
        # which pulls AVG up more than AVG_OF_AVG
        assert avg_score != avg_of_avg_score
        assert avg_score == 80.0
        assert avg_of_avg_score == 77.5

    def test_not_applicable_excluded_from_all_methods(self, scoring_setup):
        """Requirements with NOT_APPLICABLE result should be excluded from all methods."""
        ca = scoring_setup["ca"]
        ra_b2 = scoring_setup["ra_b2"]

        # Mark B2 (score=100, weight=3) as not applicable
        ra_b2.result = RequirementAssessment.Result.NOT_APPLICABLE
        ra_b2.save()

        # AVG: (80 + 60 + 40) / 3 = 60.0
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        assert ca.get_global_score() == 60.0

        # SUM: 80 + 60 + 40 = 180.0
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.save()
        assert ca.get_global_score() == 180.0

        # AVG_OF_AVG: Section A = (80+60)/2 = 70, Section B = 40/1 = 40
        # Average = (70 + 40) / 2 = 55.0
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()
        assert ca.get_global_score() == 55.0

    def test_unscored_excluded_from_all_methods(self, scoring_setup):
        """Requirements with is_scored=False should be excluded from all methods."""
        ca = scoring_setup["ca"]
        ra_a2 = scoring_setup["ra_a2"]

        # Mark A2 (score=60, weight=1) as unscored
        RequirementAssessment.objects.filter(pk=ra_a2.pk).update(is_scored=False)

        # AVG without A2: (80×1 + 40×1 + 100×3) / (1+1+3) = 420/5 = 84.0
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        assert ca.get_global_score() == 84.0

        # AVG_OF_AVG without A2: Section A = 80/1 = 80, Section B = (40+300)/4 = 85
        # Average = (80 + 85) / 2 = 82.5
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()
        assert ca.get_global_score() == 82.5

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
            assert ca.get_global_score() == -1, f"Expected -1 for method {method}"


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
        """
        SUM max: max_score × Σ(weight) = 100 × (1+1+1+3) = 600
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.save()
        assert ca.get_total_max_score() == 600


@pytest.mark.django_db
class TestDocumentationScore:
    """Tests that documentation_score is included when show_documentation_score is on."""

    def test_avg_with_documentation_score(self, scoring_setup):
        """
        With documentation scores, each RA contributes both score and
        documentation_score with the same weight.
        """
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.show_documentation_score = True
        ca.save()

        # Set documentation scores
        scoring_setup["ra_a1"].documentation_score = 90
        scoring_setup["ra_a1"].save()
        scoring_setup["ra_a2"].documentation_score = 70
        scoring_setup["ra_a2"].save()
        scoring_setup["ra_b1"].documentation_score = 50
        scoring_setup["ra_b1"].save()
        scoring_setup["ra_b2"].documentation_score = 80
        scoring_setup["ra_b2"].save()

        # Weighted scores: (80+90)×1 + (60+70)×1 + (40+50)×1 + (100+80)×3
        # Weights: 1+1 + 1+1 + 1+1 + 3+3 = 12
        # Total: 170 + 130 + 90 + 540 = 930
        # Average: 930 / 12 = 77.5
        assert ca.get_global_score() == 77.5

    def test_avg_of_avg_with_documentation_score(self, scoring_setup):
        ca = scoring_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.show_documentation_score = True
        ca.save()

        scoring_setup["ra_a1"].documentation_score = 90
        scoring_setup["ra_a1"].save()
        scoring_setup["ra_a2"].documentation_score = 70
        scoring_setup["ra_a2"].save()
        scoring_setup["ra_b1"].documentation_score = 50
        scoring_setup["ra_b1"].save()
        scoring_setup["ra_b2"].documentation_score = 80
        scoring_setup["ra_b2"].save()

        # Section A: (80+90)×1 + (60+70)×1 = 300, weights = 4, avg = 75.0
        # Section B: (40+50)×1 + (100+80)×3 = 630, weights = 8, avg = 78.75
        # Average of averages: (75.0 + 78.75) / 2 = 76.875 → truncated to 76.8
        assert ca.get_global_score() == 76.8
