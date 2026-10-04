import pytest

from core.models import ComplianceAssessment, Framework, RequirementNode
from core.serializers import ComplianceAssessmentWriteSerializer
from iam.models import Folder

AVG = ComplianceAssessment.CalculationMethod.AVG
AVG_OF_AVG = ComplianceAssessment.CalculationMethod.AVG_OF_AVG

# Levels whose own targets override the framework's (3.5); E has none.
GROUPS = [
    {"ref_id": "B", "name": "basic", "target_score": 2.5},
    {"ref_id": "BK", "name": "basic - key measures", "target_score": 2.5},
    {"ref_id": "I", "name": "important", "target_score": 3},
    {"ref_id": "E", "name": "essential"},
]


def _anchored(target):
    return {
        "score_calculation_method": AVG_OF_AVG,
        "anchor_na_to_target": True,
        "target_score": target,
    }


@pytest.mark.parametrize(
    "groups, expected",
    [
        ([], _anchored(3.5)),
        (["B"], _anchored(2.5)),
        (["B", "BK"], _anchored(2.5)),
        # The highest target of the selected groups applies.
        (["B", "I"], _anchored(3)),
        # A group without its own target counts as the framework's.
        (["E"], _anchored(3.5)),
        (["B", "E"], _anchored(3.5)),
    ],
)
@pytest.mark.django_db
def test_default_scoring_for(groups, expected):
    framework = Framework(
        score_calculation_method=AVG_OF_AVG,
        anchor_na_to_target=True,
        target_score=3.5,
        implementation_groups_definition=GROUPS,
    )
    assert framework.default_scoring_for(groups) == expected


@pytest.mark.django_db
def test_framework_without_declared_scoring_proposes_average():
    assert Framework().default_scoring == {"score_calculation_method": AVG}


@pytest.mark.django_db
def test_group_targets_need_a_framework_target():
    """The framework's target is the fallback of groups without one."""
    framework = Framework(implementation_groups_definition=GROUPS)
    assert framework.default_scoring_for(["B"]) == {"score_calculation_method": AVG}


@pytest.fixture
def cyfun():
    folder = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="Levels",
        urn="urn:test:framework:levels",
        min_score=1,
        max_score=5,
        folder=folder,
        implementation_groups_definition=GROUPS,
        score_scale_locked=True,
        score_calculation_method=AVG_OF_AVG,
        anchor_na_to_target=True,
        target_score=3,
    )
    RequirementNode.objects.create(
        urn="urn:test:levels-default-scoring:1",
        framework=framework,
        assessable=True,
        folder=folder,
    )
    return {"folder": folder, "framework": framework}


def _serializer(cyfun, valid=True, **data):
    serializer = ComplianceAssessmentWriteSerializer(
        data={
            "name": "Levels audit",
            "folder": str(cyfun["folder"].id),
            "framework": str(cyfun["framework"].id),
            **data,
        }
    )
    assert serializer.is_valid() is valid, serializer.errors
    return serializer


@pytest.mark.django_db
class TestDefaultScoringOnCreate:
    """Audits created without scoring settings (API, presets, imports) get the
    framework's, like the form proposes."""

    @pytest.mark.parametrize("groups, target", [([], 3), (["E"], 3), (["B"], 2.5)])
    def test_new_audit_gets_level_settings(self, cyfun, groups, target):
        ca = _serializer(cyfun, selected_implementation_groups=groups).save()
        assert ca.score_calculation_method == AVG_OF_AVG
        assert ca.anchor_na_to_target is True
        assert ca.target_score == target

    def test_explicit_settings_win(self, cyfun):
        ca = _serializer(
            cyfun,
            score_calculation_method=AVG,
            anchor_na_to_target=False,
            target_score=4,
        ).save()
        assert (ca.score_calculation_method, ca.anchor_na_to_target) == (AVG, False)
        assert ca.target_score == 4

    def test_locked_scale_rejects_another_scale(self, cyfun):
        """A scale the standard defines: audits keep 1-5."""
        serializer = _serializer(cyfun, valid=False, score_scale_preset="0-100")
        assert serializer.errors["score_scale_preset"] == ["scoreScaleBoundToFramework"]

    def test_copy_of_an_audit_keeps_the_callers_settings(self, cyfun):
        baseline = ComplianceAssessment.objects.create(
            name="Baseline",
            framework=cyfun["framework"],
            folder=cyfun["folder"],
        )
        data = _serializer(cyfun, baseline=str(baseline.id)).validated_data
        assert "anchor_na_to_target" not in data
        assert "target_score" not in data

    def test_audit_from_another_framework_gets_the_framework_defaults(self, cyfun):
        """E.g. a CyFun 2025 audit created from a CyFun 2023 baseline."""
        other = Framework.objects.create(
            name="Other", urn="urn:test:framework:other", folder=cyfun["folder"]
        )
        baseline = ComplianceAssessment.objects.create(
            name="Baseline", framework=other, folder=cyfun["folder"]
        )
        data = _serializer(cyfun, baseline=str(baseline.id)).validated_data
        assert data["anchor_na_to_target"] is True
        assert data["target_score"] == 3
