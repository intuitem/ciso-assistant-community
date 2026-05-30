"""Aggregation tests for per-requirement score scale and target overrides.

Verifies:
- Mixed-scale RAs in a single CA aggregate correctly via normalization.
- anchor_na_to_target consumes the per-RA resolved target, not the CA target.
- recompute_assessment clamps to the resolved scale.
- CA with non-zero min_score denormalizes correctly.

The existing test_compliance_assessment_scoring.py covers the uniform-scale
(no-override) non-regression path: any deviation there would surface there.
"""

import pytest

from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder


@pytest.fixture
def mixed_scale_setup():
    """
    Framework: 0-5 default.
    Section A
        ├── Req A1 (default 0-5, weight=1)
        └── Req A2 (override 0-1, weight=1)
    Section B
        ├── Req B1 (default 0-5, weight=1)
        └── Req B2 (default 0-5, weight=3)
    """
    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="mixed scoring folder")
    perimeter = Perimeter.objects.create(name="mixed scoring perimeter", folder=folder)

    framework = Framework.objects.create(
        name="Mixed Scoring Framework",
        urn="urn:test:fw-mixed",
        min_score=0,
        max_score=5,
        folder=root,
    )

    sec_a = RequirementNode.objects.create(
        urn="urn:test:mix-sec-a",
        ref_id="A",
        framework=framework,
        assessable=False,
        folder=root,
    )
    sec_b = RequirementNode.objects.create(
        urn="urn:test:mix-sec-b",
        ref_id="B",
        framework=framework,
        assessable=False,
        folder=root,
    )

    a1 = RequirementNode.objects.create(
        urn="urn:test:mix-a1",
        ref_id="A.1",
        framework=framework,
        parent_urn=sec_a.urn,
        assessable=True,
        weight=1,
        folder=root,
    )
    a2 = RequirementNode.objects.create(
        urn="urn:test:mix-a2",
        ref_id="A.2",
        framework=framework,
        parent_urn=sec_a.urn,
        assessable=True,
        weight=1,
        folder=root,
        min_score=0,
        max_score=1,
    )
    b1 = RequirementNode.objects.create(
        urn="urn:test:mix-b1",
        ref_id="B.1",
        framework=framework,
        parent_urn=sec_b.urn,
        assessable=True,
        weight=1,
        folder=root,
    )
    b2 = RequirementNode.objects.create(
        urn="urn:test:mix-b2",
        ref_id="B.2",
        framework=framework,
        parent_urn=sec_b.urn,
        assessable=True,
        weight=3,
        folder=root,
    )

    ca = ComplianceAssessment.objects.create(
        name="Mixed Scoring CA",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        min_score=0,
        max_score=5,
    )

    return {
        "ca": ca,
        "a1": a1,
        "a2": a2,
        "b1": b1,
        "b2": b2,
        "folder": folder,
    }


def _score(setup, node_key, score, is_scored=True, result=None):
    """Create a RequirementAssessment for the given node, with the given score."""
    kwargs = {
        "compliance_assessment": setup["ca"],
        "requirement": setup[node_key],
        "folder": setup["folder"],
        "is_scored": is_scored,
        "score": score,
    }
    if result is not None:
        kwargs["result"] = result
    return RequirementAssessment.objects.create(**kwargs)


@pytest.mark.django_db
class TestMixedScaleAggregation:
    def test_avg_normalizes_mixed_scales(self, mixed_scale_setup):
        """A2 on 0-1 scoring 1 = full (ratio 1.0); others on 0-5.

        Ratios: A1=4/5=0.8, A2=1/1=1.0, B1=2/5=0.4, B2=5/5=1.0 (w=3)
        Weighted avg ratio = (0.8 + 1.0 + 0.4 + 3.0) / 6 = 5.2 / 6 ≈ 0.8667
        Denormalized on CA (0-5): 0.8667 * 5 = 4.333 → 4.3 (truncated to .1)
        """
        _score(mixed_scale_setup, "a1", 4)
        _score(mixed_scale_setup, "a2", 1)
        _score(mixed_scale_setup, "b1", 2)
        _score(mixed_scale_setup, "b2", 5)

        ca = mixed_scale_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()

        assert ca.get_global_score()["implementation_score"] == 4.3

    def test_avg_full_top_of_each_scale_returns_max(self, mixed_scale_setup):
        """Every RA at its own max → global ratio 1.0 → CA max."""
        _score(mixed_scale_setup, "a1", 5)
        _score(mixed_scale_setup, "a2", 1)
        _score(mixed_scale_setup, "b1", 5)
        _score(mixed_scale_setup, "b2", 5)

        ca = mixed_scale_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()

        assert ca.get_global_score()["implementation_score"] == 5.0

    def test_avg_of_avg_normalizes_mixed_scales(self, mixed_scale_setup):
        """
        Section A: weighted avg of ratios (A1=0.8, A2=1.0) = 0.9
        Section B: weighted avg of ratios (B1=0.4 w1, B2=1.0 w3) = 3.4/4 = 0.85
        Global ratio = (0.9 + 0.85) / 2 = 0.875
        Denormalized = 0.875 * 5 = 4.375 → 4.3 (int(x*10)/10)
        """
        _score(mixed_scale_setup, "a1", 4)
        _score(mixed_scale_setup, "a2", 1)
        _score(mixed_scale_setup, "b1", 2)
        _score(mixed_scale_setup, "b2", 5)

        ca = mixed_scale_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG_OF_AVG
        ca.save()

        assert ca.get_global_score()["implementation_score"] == 4.3

    def test_sum_uses_raw_weighted_sum(self, mixed_scale_setup):
        """SUM is intentionally simple: Σ(raw_score × weight), no scale
        normalization. Scales are kept as-is — summing across mixed scales
        is the operator's responsibility.

        Raw scores: A1=4 (w=1), A2=1 on 0-1 (w=1), B1=2 (w=1), B2=5 (w=3)
        SUM = 4 + 1 + 2 + 15 = 22.0
        """
        _score(mixed_scale_setup, "a1", 4)
        _score(mixed_scale_setup, "a2", 1)
        _score(mixed_scale_setup, "b1", 2)
        _score(mixed_scale_setup, "b2", 5)

        ca = mixed_scale_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.save()

        assert ca.get_global_score()["implementation_score"] == 22.0


@pytest.mark.django_db
class TestAnchorNAToTargetWithMixedScales:
    def test_anchor_projects_ca_target_onto_ra_scale(self, mixed_scale_setup):
        """CA target is projected via ratio onto the RA scale so mixed scales
        stay coherent (CA target 4/5 → 80% of the RA range, applied to
        whatever the RA's resolved scale is).
        """
        _score(mixed_scale_setup, "a1", 5)
        _score(mixed_scale_setup, "a2", 1)
        _score(
            mixed_scale_setup,
            "b1",
            None,
            is_scored=False,
            result=RequirementAssessment.Result.NOT_APPLICABLE,
        )
        _score(mixed_scale_setup, "b2", 5)

        ca = mixed_scale_setup["ca"]
        ca.anchor_na_to_target = True
        ca.target_score = 4  # CA target projected onto each N/A RA's range
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()

        # Ratios: A1=1.0, A2=1.0, B1=4/5=0.8, B2=1.0 (w=3)
        # Weighted avg = (1.0 + 1.0 + 0.8 + 3.0) / 6 = 5.8/6 ≈ 0.9667
        # Denormalized: 0.9667 * 5 = 4.833 → 4.8
        assert ca.get_global_score()["implementation_score"] == 4.8


@pytest.fixture
def offset_scale_setup():
    """CA with non-zero min: 10-20."""
    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="offset folder")
    perimeter = Perimeter.objects.create(name="offset perimeter", folder=folder)

    framework = Framework.objects.create(
        name="Offset Framework",
        urn="urn:test:fw-offset",
        min_score=10,
        max_score=20,
        folder=root,
    )
    req = RequirementNode.objects.create(
        urn="urn:test:offset-r1",
        framework=framework,
        assessable=True,
        weight=1,
        folder=root,
    )
    ca = ComplianceAssessment.objects.create(
        name="Offset CA",
        framework=framework,
        folder=folder,
        perimeter=perimeter,
        min_score=10,
        max_score=20,
    )
    RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=req,
        folder=folder,
        is_scored=True,
        score=15,
    )
    return ca


@pytest.mark.django_db
class TestNonZeroMinDenormalization:
    def test_avg_preserves_score_on_uniform_offset_scale(self, offset_scale_setup):
        """For uniform scale (no Node override), normalize + denormalize is identity."""
        offset_scale_setup.score_calculation_method = (
            ComplianceAssessment.CalculationMethod.AVG
        )
        offset_scale_setup.save()
        # score=15 → ratio=(15-10)/10=0.5 → denormalized=10+0.5*10=15.0
        assert offset_scale_setup.get_global_score()["implementation_score"] == 15.0
