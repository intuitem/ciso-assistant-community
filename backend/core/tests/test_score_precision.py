import pytest

from core.models import ComplianceAssessment, Framework, round_score


@pytest.mark.parametrize(
    "value, expected",
    [
        (2.69433333, 2.69),
        (2.695, 2.7),
        (68.3333333, 68.33),
        (4.375, 4.38),
        # Float noise from ratio aggregation must not flip the rounding.
        (2.6949999999999, 2.7),
    ],
)
def test_round_score_two_decimals_half_up(value, expected):
    assert round_score(value) == expected


@pytest.mark.parametrize(
    "urn, expected",
    [
        (
            "urn:intuitem:risk:framework:ccb-cyfun2025",
            ComplianceAssessment.CalculationMethod.AVG_OF_AVG,
        ),
        (
            "urn:intuitem:risk:framework:ccb-cff-2023-03-01",
            ComplianceAssessment.CalculationMethod.AVG_OF_AVG,
        ),
        (
            "urn:intuitem:risk:framework:iso27001-2022",
            ComplianceAssessment.CalculationMethod.AVG,
        ),
    ],
)
@pytest.mark.django_db
def test_default_score_calculation_method(urn, expected):
    assert Framework(urn=urn).default_score_calculation_method == expected
