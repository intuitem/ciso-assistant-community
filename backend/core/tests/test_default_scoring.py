import pytest

from core.cyfun import CYFUN_2025_URN as CYFUN
from core.models import ComplianceAssessment, Framework, RequirementNode
from core.serializers import ComplianceAssessmentWriteSerializer
from iam.models import Folder

AVG = ComplianceAssessment.CalculationMethod.AVG
AVG_OF_AVG = ComplianceAssessment.CalculationMethod.AVG_OF_AVG


def _cyfun(target):
    return {
        "score_calculation_method": AVG_OF_AVG,
        "anchor_na_to_target": True,
        "target_score": target,
    }


@pytest.mark.parametrize(
    "urn, groups, expected",
    [
        # CyFun 2025 tools count N/A as the level's key measure threshold.
        (CYFUN, [], _cyfun(3)),
        (CYFUN, ["E"], _cyfun(3)),
        (CYFUN, ["I", "IK"], _cyfun(3)),
        (CYFUN, ["B"], _cyfun(2.5)),
        (CYFUN, ["BK", "BG"], _cyfun(2.5)),
        # BASIC and IMPORTANT groups together make an IMPORTANT audit.
        (CYFUN, ["B", "I"], _cyfun(3)),
        # Other frameworks only propose their declared calculation method.
        (
            "urn:test:framework:avg-of-avg",
            ["B"],
            {"score_calculation_method": AVG_OF_AVG},
        ),
    ],
)
@pytest.mark.django_db
def test_default_scoring_for(urn, groups, expected):
    framework = Framework(urn=urn, score_calculation_method=AVG_OF_AVG)
    assert framework.default_scoring_for(groups) == expected


@pytest.mark.django_db
def test_framework_without_declared_method_proposes_average():
    assert Framework(urn="urn:test:framework:plain").default_scoring == {
        "score_calculation_method": AVG
    }


@pytest.fixture
def cyfun():
    folder = Folder.get_root_folder()
    framework = Framework.objects.create(
        name="CyFun 2025",
        urn=CYFUN,
        min_score=1,
        max_score=5,
        folder=folder,
        implementation_groups_definition=[
            {"ref_id": ref_id, "name": ref_id} for ref_id in ("B", "BK", "I", "E")
        ],
        score_scale_locked=True,
        score_calculation_method=AVG_OF_AVG,
    )
    RequirementNode.objects.create(
        urn="urn:test:cyfun-default-scoring:1",
        framework=framework,
        assessable=True,
        folder=folder,
    )
    return {"folder": folder, "framework": framework}


def _serializer(cyfun, valid=True, **data):
    serializer = ComplianceAssessmentWriteSerializer(
        data={
            "name": "CyFun audit",
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
    def test_new_cyfun_audit_gets_level_settings(self, cyfun, groups, target):
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
        """The CyFun scale is part of the standard: audits keep 1-5."""
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
