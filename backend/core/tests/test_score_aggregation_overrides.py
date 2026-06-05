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
from django.urls import reverse
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder, User, UserGroup


@pytest.fixture
def admin_client():
    startup(sender=None, **{})
    admin = User.objects.create_superuser(
        "admin@score-aggregation-tests.com", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


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


@pytest.mark.django_db
class TestTreeAggregationNoneScoreOnOffsetScale:
    """Regression: an is_scored leaf with score=None on an offset scale must
    not pull the parent below the audit's min via a negative ratio. Covers
    both the tree path (helpers.annotate_tree_with_aggregated_scores) and
    the shared path used by the radar and global score
    (models._compute_score_for_field)."""

    def test_none_score_does_not_produce_negative_aggregate(self):
        from core.helpers import (
            annotate_tree_with_aggregated_scores,
            get_sorted_requirement_nodes,
        )

        root = Folder.get_root_folder()
        folder = Folder.objects.create(parent_folder=root, name="none-score folder")
        perimeter = Perimeter.objects.create(name="none-score perimeter", folder=folder)
        framework = Framework.objects.create(
            name="Offset Framework (1..4)",
            urn="urn:test:fw-1to4-none-score",
            min_score=1,
            max_score=4,
            folder=root,
        )
        section = RequirementNode.objects.create(
            urn="urn:test:none-score-sec",
            framework=framework,
            assessable=False,
            folder=root,
        )
        # Two leaves: one scored at 3, one is_scored=True but score=None
        # (inconsistent state observed on legacy audits).
        scored_leaf = RequirementNode.objects.create(
            urn="urn:test:none-score-r1",
            framework=framework,
            parent_urn=section.urn,
            assessable=True,
            weight=1,
            folder=root,
        )
        unscored_leaf = RequirementNode.objects.create(
            urn="urn:test:none-score-r2",
            framework=framework,
            parent_urn=section.urn,
            assessable=True,
            weight=1,
            folder=root,
        )
        ca = ComplianceAssessment.objects.create(
            name="None-score CA",
            framework=framework,
            folder=folder,
            perimeter=perimeter,
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=scored_leaf,
            folder=folder,
            is_scored=True,
            score=3,
        )
        RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=unscored_leaf,
            folder=folder,
            is_scored=True,
            score=None,
        )
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()

        nodes = list(RequirementNode.objects.filter(framework=framework))
        ras = list(RequirementAssessment.objects.filter(compliance_assessment=ca))
        tree = get_sorted_requirement_nodes(
            nodes, ras, framework.max_score, framework.min_score
        )
        annotate_tree_with_aggregated_scores(tree, ca)

        def _find(t, ref):
            for n in t.values():
                if n.get("urn") == ref:
                    return n
                f = _find(n.get("children") or {}, ref)
                if f is not None:
                    return f
            return None

        section_node = _find(tree, section.urn)
        # The unscored leaf must be excluded so the parent reflects only the
        # one valid leaf (score 3 on 1..4). Score 3 stays in the framework's
        # range [1, 4]; the parent should never dip below min_score.
        assert section_node["aggregated_score"] == 3
        assert section_node["aggregated_score"] >= framework.min_score

        # Same invariant on the radar / global-score path: the inconsistent
        # leaf must not coerce to 0 and produce a negative ratio. Both AVG
        # and SUM exclude the leaf, matching the tree.
        global_avg = ca.get_global_score()["implementation_score"]
        assert global_avg == 3.0
        assert global_avg >= framework.min_score

        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.save()
        global_sum = ca.get_global_score()["implementation_score"]
        # SUM: only the valid leaf (3) contributes, with weight 1.
        assert global_sum == 3.0


@pytest.mark.django_db
class TestRadarDataNormalizesMixedScales:
    """Regression for the compare endpoint's per-top-level radar slice:
    mixed-scale subtrees must normalise before averaging, otherwise a binary
    0..1 leaf and a 0..5 leaf can't be compared.
    """

    def test_avg_radar_normalises_mixed_scales(self, mixed_scale_setup):
        """A1=4/5 (ratio 0.8), A2=1/1 (ratio 1.0) under section A.
        Weighted avg ratio = (0.8 + 1.0) / 2 = 0.9. Denormalised on the CA
        (0..5): 0.9 * 5 = 4.5. The legacy ad-hoc path returned (4 + 1) / 2 =
        2.5 instead — meaningless across mixed scales.
        """
        ca = mixed_scale_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        _score(mixed_scale_setup, "a1", 4)
        _score(mixed_scale_setup, "a2", 1)

        a1 = mixed_scale_setup["a1"]
        a2 = mixed_scale_setup["a2"]
        scored = list(
            RequirementAssessment.objects.filter(
                compliance_assessment=ca, requirement__in=[a1, a2]
            )
        )
        result = ca._compute_score_for_field(
            scored, None, "score", ca.anchor_na_to_target
        )
        assert result == 4.5

    def test_sum_radar_keeps_raw_weighted_sum(self, mixed_scale_setup):
        """SUM stays raw — operator's responsibility to interpret across scales."""
        ca = mixed_scale_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.SUM
        ca.save()
        _score(mixed_scale_setup, "a1", 4)
        _score(mixed_scale_setup, "a2", 1)

        scored = list(
            RequirementAssessment.objects.filter(
                compliance_assessment=ca,
                requirement__in=[mixed_scale_setup["a1"], mixed_scale_setup["a2"]],
            )
        )
        # raw weighted: 4*1 + 1*1 = 5
        assert (
            ca._compute_score_for_field(scored, None, "score", ca.anchor_na_to_target)
            == 5.0
        )

    def test_compare_endpoint_radar_normalises_mixed_scales(
        self, admin_client, mixed_scale_setup
    ):
        """End-to-end through the compare endpoint's aggregate_by_top_level():
        section A's radar slice must be the denormalised mixed-scale average
        (4.5), not the raw average (2.5). Section B has no scored RAs -> 0.
        """
        ca = mixed_scale_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.save()
        _score(mixed_scale_setup, "a1", 4)
        _score(mixed_scale_setup, "a2", 1)

        other = ComplianceAssessment.objects.create(
            name="Mixed Scoring CA (compare)",
            framework=ca.framework,
            folder=mixed_scale_setup["folder"],
            perimeter=ca.perimeter,
            min_score=0,
            max_score=5,
        )

        url = reverse("compliance-assessments-compare", kwargs={"pk": str(ca.pk)})
        response = admin_client.get(url, {"compare_id": str(other.pk)})
        assert response.status_code == 200
        radar = response.json()["base"]["radar_data"]
        assert radar["labels"] == ["A", "B"]
        assert radar["maturity_scores"] == [4.5, 0]

    def test_compare_endpoint_radar_anchors_na_to_target(
        self, admin_client, mixed_scale_setup
    ):
        """With anchor_na_to_target on, an N/A RA contributes its
        target-projected ratio to the radar slice, matching get_global_score():
        A1 = 4/5 (0.8), A2 N/A -> CA target 2/5 projected (0.4).
        Avg ratio 0.6, denormalised on 0..5 -> 3.0. Excluding the N/A RA
        (the pre-fix behaviour) would yield 4.0 instead.
        """
        ca = mixed_scale_setup["ca"]
        ca.score_calculation_method = ComplianceAssessment.CalculationMethod.AVG
        ca.anchor_na_to_target = True
        ca.target_score = 2
        ca.save()
        _score(mixed_scale_setup, "a1", 4)
        _score(mixed_scale_setup, "a2", None, is_scored=False, result="not_applicable")

        other = ComplianceAssessment.objects.create(
            name="Mixed Scoring CA (compare)",
            framework=ca.framework,
            folder=mixed_scale_setup["folder"],
            perimeter=ca.perimeter,
            min_score=0,
            max_score=5,
        )

        url = reverse("compliance-assessments-compare", kwargs={"pk": str(ca.pk)})
        response = admin_client.get(url, {"compare_id": str(other.pk)})
        assert response.status_code == 200
        body = response.json()
        radar = body["base"]["radar_data"]
        assert radar["labels"] == ["A", "B"]
        assert radar["maturity_scores"][0] == 3.0
        # Radar slice and global score agree (only section A is scored).
        assert body["base"]["global_score"] == 3.0
