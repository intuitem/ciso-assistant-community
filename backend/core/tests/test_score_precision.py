import pytest

from core.models import round_score


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
