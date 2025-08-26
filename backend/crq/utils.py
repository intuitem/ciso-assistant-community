import numpy as np
from crq.models import QuantitativeRiskHypothesis
from scipy.stats import norm


def get_lognormal_params(lb: float, ub: float, ci: float = 0.90) -> tuple[float, float]:
    """
    Calculates mu and sigma for a log-normal distribution from a confidence interval.
    """
    if lb <= 0 or ub <= 0:
        raise ValueError(
            "Confidence interval bounds must be positive for a log-normal distribution."
        )
    if ub <= lb:
        raise ValueError("The upper bound must be greater than the lower bound.")

    # Calculate the Z-score for the lower percentile
    lower_percentile = (1 - ci) / 2
    z_score = norm.ppf(1 - lower_percentile)

    # Calculate mu and sigma
    log_lb = np.log(lb)
    log_ub = np.log(ub)

    mu = (log_ub + log_lb) / 2
    sigma = (log_ub - log_lb) / (2 * z_score)

    return mu, sigma


def parse_probability(prob_input: dict, ref_period_in_seconds: int) -> float:
    """
    Parses various probability formats into a single decimal probability for the
    given reference period.
    """

    time_units_in_seconds = QuantitativeRiskHypothesis.REFERENCE_PERIOD_SECONDS

    prob_type = prob_input.get("type")

    if prob_type == "decimal":
        return prob_input.get("value", 0.0)

    elif prob_type == "frequency":
        x = prob_input.get("x", 0)
        y_unit = prob_input.get("y_unit")

        if not y_unit or y_unit not in time_units_in_seconds:
            raise ValueError(f"Invalid time unit '{y_unit}' in frequency.")

        freq_per_second = x / time_units_in_seconds[y_unit]
        return freq_per_second * ref_period_in_seconds

    elif prob_type == "proportion":
        x = prob_input.get("x", 0)
        y = prob_input.get("y", 1)
        if y == 0:
            return 0.0
        return x / y

    else:
        raise ValueError(f"Invalid probability type specified: {prob_type}")
