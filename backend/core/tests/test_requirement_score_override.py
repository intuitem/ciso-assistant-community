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

    def test_validate_score_rejects_out_of_node_override(self, ca_05, framework_05):
        """Out-of-range scores are rejected. Clamping would hide client bugs."""
        from rest_framework import serializers as drf_serializers

        from core.serializers import RequirementAssessmentWriteSerializer

        node = RequirementNode.objects.create(
            urn="urn:test:r-reject",
            framework=framework_05,
            assessable=True,
            folder=Folder.get_root_folder(),
            min_score=0,
            max_score=1,
        )
        ra = self._ra(ca_05, node)
        serializer = RequirementAssessmentWriteSerializer(instance=ra, data={})
        serializer.is_valid()
        with pytest.raises(drf_serializers.ValidationError):
            serializer.validate_score(5)
        with pytest.raises(drf_serializers.ValidationError):
            serializer.validate_documentation_score(5)
        # In-range values pass through unchanged.
        assert serializer.validate_score(1) == 1
        assert serializer.validate_documentation_score(0) == 0

    def test_validate_score_rejects_on_create(self, ca_05, framework_05):
        """No instance means no resolvable scale; the score must be rejected."""
        from rest_framework import serializers as drf_serializers

        from core.serializers import RequirementAssessmentWriteSerializer

        serializer = RequirementAssessmentWriteSerializer(data={})
        with pytest.raises(drf_serializers.ValidationError):
            serializer.validate_score(99999)

    def test_validate_score_rejects_when_bounds_none(self, framework_05):
        """Null CA bounds (degenerate misconfiguration) reject any score.

        CA.save() auto-copies from the framework, so the only way to land
        here is via a direct DB write — we simulate that with a queryset
        update to test the defensive path in the validator.
        """
        from rest_framework import serializers as drf_serializers

        from core.serializers import RequirementAssessmentWriteSerializer

        root = Folder.get_root_folder()
        folder = Folder.objects.create(parent_folder=root, name="no-bounds folder")
        perimeter = Perimeter.objects.create(name="no-bounds perimeter", folder=folder)
        ca = ComplianceAssessment.objects.create(
            name="No-bounds CA",
            framework=framework_05,
            folder=folder,
            perimeter=perimeter,
        )
        ComplianceAssessment.objects.filter(id=ca.id).update(
            min_score=None, max_score=None
        )
        ca.refresh_from_db()
        assert ca.min_score is None and ca.max_score is None

        node = RequirementNode.objects.create(
            urn="urn:test:r-no-bounds",
            framework=framework_05,
            assessable=True,
            folder=root,
        )
        ra = RequirementAssessment.objects.create(
            compliance_assessment=ca,
            requirement=node,
            folder=folder,
        )
        serializer = RequirementAssessmentWriteSerializer(instance=ra, data={})
        with pytest.raises(drf_serializers.ValidationError):
            serializer.validate_score(3)


@pytest.fixture
def admin_client_with_audit(framework_with_alternatives):
    """Admin API client + an audit with a binary-override RA, for endpoint tests."""
    from knox.models import AuthToken
    from rest_framework.test import APIClient

    from core.apps import startup
    from iam.models import User, UserGroup

    startup(sender=None)

    admin = User.objects.create_superuser(
        "admin@update-requirement-tests.com", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")

    root = Folder.get_root_folder()
    folder = Folder.objects.create(parent_folder=root, name="update-req folder")
    perimeter = Perimeter.objects.create(name="update-req perimeter", folder=folder)
    ca = ComplianceAssessment.objects.create(
        name="Update-Req CA",
        framework=framework_with_alternatives,
        folder=folder,
        perimeter=perimeter,
    )
    binary_node = RequirementNode.objects.create(
        urn="urn:test:update-req-binary",
        framework=framework_with_alternatives,
        assessable=True,
        folder=root,
        min_score=0,
        max_score=1,
        scores_definition_ref="binary",
    )
    ra = RequirementAssessment.objects.create(
        compliance_assessment=ca,
        requirement=binary_node,
        folder=folder,
    )
    return {"client": client, "ca": ca, "ra": ra, "urn": binary_node.urn}


@pytest.mark.django_db
class TestUpdateRequirementEndpointScoreValidation:
    """Regression tests for the update_requirement action's score validation."""

    def _url(self, ca):
        from django.urls import reverse

        return reverse(
            "compliance-assessments-update-requirement", kwargs={"pk": str(ca.pk)}
        )

    def test_rejects_score_above_node_override(self, admin_client_with_audit):
        ctx = admin_client_with_audit
        response = ctx["client"].post(
            self._url(ctx["ca"]),
            {"urn": ctx["urn"], "result": "compliant", "score": 5},
            format="json",
        )
        assert response.status_code == 400
        assert "between 0 and 1" in response.json().get("error", "")

    def test_accepts_score_within_node_override(self, admin_client_with_audit):
        ctx = admin_client_with_audit
        response = ctx["client"].post(
            self._url(ctx["ca"]),
            {"urn": ctx["urn"], "result": "compliant", "score": 1},
            format="json",
        )
        assert response.status_code == 200
        ctx["ra"].refresh_from_db()
        assert ctx["ra"].score == 1
        assert ctx["ra"].is_scored is True

    def test_rejects_score_when_bounds_unresolvable(self, admin_client_with_audit):
        """If the CA has null bounds, scoring isn't configured and scores reject."""
        ctx = admin_client_with_audit
        # Drop the node-level override (incl. the ref into alternatives) so
        # resolution falls through to the CA bounds.
        ctx["ra"].requirement.min_score = None
        ctx["ra"].requirement.max_score = None
        ctx["ra"].requirement.scores_definition_ref = None
        ctx["ra"].requirement.save()
        # Bypass CA.save()'s framework-default copy with a direct queryset
        # update — the only realistic way bounds can be null in production.
        ComplianceAssessment.objects.filter(id=ctx["ca"].id).update(
            min_score=None, max_score=None
        )

        response = ctx["client"].post(
            self._url(ctx["ca"]),
            {"urn": ctx["urn"], "result": "compliant", "score": 3},
            format="json",
        )
        assert response.status_code == 400
        assert "not configured" in response.json().get("error", "")
