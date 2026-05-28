"""Unit tests for per-requirement score scale override.

Covers:
- RequirementNode field storage (min_score, max_score, scores_definition_ref)
- RequirementNode.clean() validation (bounds, ref resolution)
- RequirementAssessment.get_resolved_scoring() cascade resolver
- Serializer effective_* exposure and visibility
"""

import pytest
from django.core.exceptions import ValidationError

from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    RequirementAssessment,
    RequirementNode,
)
from iam.models import Folder


@pytest.fixture
def framework_05():
    """Framework with min=0, max=5 (default scale for most tests below)."""
    root = Folder.get_root_folder()
    return Framework.objects.create(
        name="0-5 Framework",
        urn="urn:test:fw-05",
        min_score=0,
        max_score=5,
        folder=root,
    )


@pytest.fixture
def ca_05(framework_05):
    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="ca folder")
    perimeter = Perimeter.objects.create(name="ca perimeter", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="0-5 CA",
        framework=framework_05,
        folder=folder,
        perimeter=perimeter,
        min_score=0,
        max_score=5,
    )
    # DEFAULT_VISIBILITY hides score; explicitly enable for serializer tests.
    ca.scoring_enabled = True
    ca.save()
    return ca


def _scale_def_for(min_v: int, max_v: int) -> list:
    """Build a bare-list scale that exactly covers [min_v, max_v]."""
    return [{"score": s, "name": f"L{s}"} for s in range(min_v, max_v + 1)]


@pytest.mark.django_db
class TestRequirementNodeFields:
    def test_defaults_are_none(self, framework_05):
        node = RequirementNode.objects.create(
            urn="urn:test:n1",
            framework=framework_05,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        assert node.min_score is None
        assert node.max_score is None
        assert node.scores_definition_ref is None


@pytest.mark.django_db
class TestRequirementNodeClean:
    def _node(self, framework, **overrides):
        return RequirementNode(
            urn="urn:test:nclean",
            framework=framework,
            assessable=True,
            folder=Folder.get_root_folder(),
            **overrides,
        )

    def test_no_override_is_valid(self, framework_05):
        self._node(framework_05).clean()

    def test_bounds_only_override_is_valid(self, framework_05):
        """min/max alone are a valid scale override."""
        self._node(framework_05, min_score=0, max_score=1).clean()

    def test_min_only_override_validated_against_framework_max(self, framework_05):
        """Node sets min only; the resolved max (Framework) is used to check coherence."""
        self._node(framework_05, min_score=2).clean()

        node = self._node(framework_05, min_score=5)  # equal to framework_max
        with pytest.raises(ValidationError) as exc:
            node.clean()
        assert "max_score" in exc.value.message_dict

    def test_max_only_override_validated_against_framework_min(self, framework_05):
        """Node sets max only; resolved min (Framework=0) is the lower bound."""
        self._node(framework_05, max_score=3).clean()

    def test_min_not_strictly_below_max_rejected(self, framework_05):
        node = self._node(framework_05, min_score=3, max_score=3)
        with pytest.raises(ValidationError) as exc:
            node.clean()
        assert "max_score" in exc.value.message_dict

    def test_dangling_ref_rejected(self, framework_05):
        """A ref that does not exist in framework alternatives is rejected."""
        node = self._node(
            framework_05, min_score=0, max_score=1, scores_definition_ref="binary"
        )
        with pytest.raises(ValidationError) as exc:
            node.clean()
        assert "scores_definition_ref" in exc.value.message_dict


@pytest.mark.django_db
class TestGetResolvedScoring:
    def _make_ra(self, ca, node) -> RequirementAssessment:
        return RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=node,
            folder=ca.folder,
        )

    def test_falls_back_to_ca_when_node_has_no_override(self, ca_05, framework_05):
        node = RequirementNode.objects.create(
            urn="urn:test:r-fallback",
            framework=framework_05,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        ra = self._make_ra(ca_05, node)

        resolved = ra.get_resolved_scoring()
        assert resolved["min_score"] == 0
        assert resolved["max_score"] == 5

    def test_partial_bounds_override_combines_with_ca(self, ca_05, framework_05):
        """Each field cascades independently: Node.min only, max from CA."""
        node = RequirementNode.objects.create(
            urn="urn:test:r-partial",
            framework=framework_05,
            assessable=True,
            folder=Folder.get_root_folder(),
            min_score=2,
        )
        ra = self._make_ra(ca_05, node)

        resolved = ra.get_resolved_scoring()
        assert resolved["min_score"] == 2  # Node
        assert resolved["max_score"] == 5  # CA


@pytest.fixture
def framework_with_alternatives():
    """Framework whose scores_definition declares a 'binary' alternative."""
    root = Folder.get_root_folder()
    return Framework.objects.create(
        name="0-5 Framework with alternatives",
        urn="urn:test:fw-alt",
        min_score=0,
        max_score=5,
        folder=root,
        scores_definition={
            "scale": _scale_def_for(0, 5),
            "alternatives": {
                "binary": [
                    {"score": 0, "name": "No"},
                    {"score": 1, "name": "Yes"},
                ]
            },
        },
    )


@pytest.fixture
def ca_with_alternatives(framework_with_alternatives):
    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="ca alt folder")
    perimeter = Perimeter.objects.create(name="ca alt perimeter", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="0-5 alt CA",
        framework=framework_with_alternatives,
        folder=folder,
        perimeter=perimeter,
    )
    ca.scoring_enabled = True
    ca.save()
    return ca


@pytest.mark.django_db
class TestScoresDefinitionRef:
    """Node.scores_definition_ref is a string key into the framework's
    scores_definition.alternatives registry."""

    def _ra(self, ca, node):
        return RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=node,
            folder=ca.folder,
        )

    def test_node_ref_resolves_into_ca_alternatives(
        self, ca_with_alternatives, framework_with_alternatives
    ):
        node = RequirementNode.objects.create(
            urn="urn:test:r-ref-ok",
            framework=framework_with_alternatives,
            assessable=True,
            folder=Folder.get_root_folder(),
            min_score=0,
            max_score=1,
            scores_definition_ref="binary",
        )
        ra = self._ra(ca_with_alternatives, node)
        resolved = ra.get_resolved_scoring()
        assert isinstance(resolved["scores_definition"], list)
        assert {entry["score"] for entry in resolved["scores_definition"]} == {0, 1}

    def test_ca_dissociation_preserves_alternatives(
        self, ca_with_alternatives, framework_with_alternatives
    ):
        """Once the CA is customized after creation, its copy of the
        alternatives stays accessible to per-RA ref resolution."""
        assert ca_with_alternatives.scores_definition["alternatives"]["binary"]

        node = RequirementNode.objects.create(
            urn="urn:test:r-ref-after-diss",
            framework=framework_with_alternatives,
            assessable=True,
            folder=Folder.get_root_folder(),
            min_score=0,
            max_score=1,
            scores_definition_ref="binary",
        )
        ra = self._ra(ca_with_alternatives, node)
        # Simulate the framework dropping the alternative later. The CA's
        # copy is the source of truth, so the RA keeps resolving.
        framework_with_alternatives.scores_definition = {"scale": _scale_def_for(0, 5)}
        framework_with_alternatives.save()

        resolved = ra.get_resolved_scoring()
        assert isinstance(resolved["scores_definition"], list)
        assert {entry["score"] for entry in resolved["scores_definition"]} == {0, 1}


@pytest.mark.django_db
class TestSerializer:
    """Serializer-level behavior: effective_* exposure, visibility, clamping."""

    def _ra(self, ca, node):
        return RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=node,
            folder=ca.folder,
        )

    def test_effective_fields_use_resolved_scoring(
        self, ca_with_alternatives, framework_with_alternatives
    ):
        from core.serializers import RequirementAssessmentReadSerializer

        node = RequirementNode.objects.create(
            urn="urn:test:r-eff",
            framework=framework_with_alternatives,
            assessable=True,
            folder=Folder.get_root_folder(),
            min_score=0,
            max_score=1,
            scores_definition_ref="binary",
        )
        ra = self._ra(ca_with_alternatives, node)
        data = RequirementAssessmentReadSerializer(
            ra, context={"viewer_role": "auditor"}
        ).data

        assert data["effective_min_score"] == 0
        assert data["effective_max_score"] == 1
        assert isinstance(data["effective_scores_definition"], list)

    def test_effective_fields_are_none_when_scoring_disabled(self, ca_05, framework_05):
        from core.serializers import RequirementAssessmentReadSerializer

        node = RequirementNode.objects.create(
            urn="urn:test:r-eff-off",
            framework=framework_05,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
        ra = self._ra(ca_05, node)
        ca_05.scoring_enabled = False
        ca_05.save()
        ra.refresh_from_db()

        data = RequirementAssessmentReadSerializer(
            ra, context={"viewer_role": "auditor"}
        ).data
        assert data["effective_min_score"] is None
        assert data["effective_max_score"] is None
        assert data["effective_scores_definition"] is None

    def test_nested_requirement_exposes_raw_override_fields(self, ca_05, framework_05):
        from core.serializers import RequirementAssessmentReadSerializer

        node = RequirementNode.objects.create(
            urn="urn:test:r-raw",
            framework=framework_05,
            assessable=True,
            folder=Folder.get_root_folder(),
            min_score=0,
            max_score=1,
        )
        ra = self._ra(ca_05, node)
        data = RequirementAssessmentReadSerializer(
            ra, context={"viewer_role": "auditor"}
        ).data

        req = data["requirement"]
        assert req["min_score"] == 0
        assert req["max_score"] == 1

    def test_validate_score_clamps_to_node_override(self, ca_05, framework_05):
        from core.serializers import RequirementAssessmentWriteSerializer

        node = RequirementNode.objects.create(
            urn="urn:test:r-clamp",
            framework=framework_05,
            assessable=True,
            folder=Folder.get_root_folder(),
            min_score=0,
            max_score=1,
        )
        ra = self._ra(ca_05, node)
        serializer = RequirementAssessmentWriteSerializer(instance=ra, data={})
        serializer.is_valid()
        # Score 5 (on CA scale) must be clamped down to 1 (node max)
        assert serializer.validate_score(5) == 1
        # documentation_score uses the same scale
        assert serializer.validate_documentation_score(5) == 1
