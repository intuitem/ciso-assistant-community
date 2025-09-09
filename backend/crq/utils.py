import numpy as np
from typing import Dict, Tuple, List, Optional


def mu_sigma_from_lognorm_90pct(lower_bound: float, upper_bound: float):
    """
    Convert 90% confidence bounds to lognormal parameters.
    Assumes lower_bound = 5th percentile, upper_bound = 95th percentile.

    Args:
        lower_bound: 5th percentile of loss distribution
        upper_bound: 95th percentile of loss distribution

    Returns:
        (mu, sigma): Parameters for lognormal distribution
    """
    z05, z95 = -1.64485362695147, 1.64485362695147
    ln_lb, ln_ub = np.log(lower_bound), np.log(upper_bound)
    sigma = (ln_ub - ln_lb) / (z95 - z05)
    mu = ln_lb - sigma * z05
    return mu, sigma


def simulate_scenario_annual_loss(
    probability: float,
    lower_bound: float,
    upper_bound: float,
    n_simulations: int = 100_000,
    random_seed: int = 42,
) -> np.ndarray:
    """
    Simulate annual losses for a single risk scenario using two-stage process.

    Args:
        probability: Annual probability of event occurrence (0-1)
        lower_bound: 5th percentile of loss when event occurs
        upper_bound: 95th percentile of loss when event occurs
        n_simulations: Number of Monte Carlo iterations
        random_seed: Random seed for reproducibility

    Returns:
        Array of annual losses (0 if no event, >0 if event occurs)
    """
    rng = np.random.default_rng(random_seed)

    # Stage 1: Frequency - does event occur this year?
    events_occur = rng.random(n_simulations) < probability

    # Stage 2: Severity - what's the loss magnitude?
    losses = np.zeros(n_simulations)
    n_events = np.sum(events_occur)

    if n_events > 0:
        mu, sigma = mu_sigma_from_lognorm_90pct(lower_bound, upper_bound)
        losses[events_occur] = rng.lognormal(mu, sigma, n_events)

    return losses


def create_loss_exceedance_curve(losses: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create Loss Exceedance Curve from loss data.

    Args:
        losses: Array of loss values

    Returns:
        (loss_values, exceedance_probabilities)
    """
    sorted_losses = np.sort(losses)
    n = len(sorted_losses)
    exceedance_probs = 1 - (np.arange(n) / n)
    return sorted_losses, exceedance_probs


def calculate_risk_insights(
    losses: np.ndarray, probability: float = None
) -> Dict[str, float]:
    """
    Calculate standard risk metrics from loss distribution.

    Args:
        losses: Array of annual loss values
        probability: Original probability of the risk event (optional)

    Returns:
        Dictionary of risk metrics
    """
    if len(losses) == 0 or np.max(losses) == 0:
        return {}

    metrics = {
        "mean_annual_loss": np.mean(losses),
        "var_95": np.percentile(losses, 95),  # 1-in-20 year loss
        "var_99": np.percentile(losses, 99),  # 1-in-100 year loss
        "var_999": np.percentile(losses, 99.9),  # 1-in-1000 year loss
        "expected_shortfall_99": np.mean(losses[losses >= np.percentile(losses, 99)]),
        "maximum_credible_loss": np.max(losses),
        "prob_zero_loss": np.mean(losses == 0),
        "prob_above_10k": np.mean(losses > 10_000),
        "prob_above_100k": np.mean(losses > 100_000),
        "prob_above_1M": np.mean(losses > 1_000_000),
    }

    # Add probability-based loss metrics if probability is provided
    if probability is not None and probability > 0:
        # Create loss exceedance curve
        sorted_losses, exceedance_probs = create_loss_exceedance_curve(losses)

        # Find losses at P/2, P/4, P/8, P/16 probability levels
        target_probs = [
            probability / 2,
            probability / 4,
            probability / 8,
            probability / 16,
        ]

        for target_prob in target_probs:
            # Find the loss value where exceedance probability is closest to target
            if len(sorted_losses) > 0 and np.max(exceedance_probs) >= target_prob:
                # Interpolate to find loss at exact probability level
                loss_at_prob = np.interp(
                    target_prob, exceedance_probs[::-1], sorted_losses[::-1]
                )
                # Create key with actual percentage (e.g., "loss_with_5_percent", "loss_with_2_5_percent")
                percentage = target_prob * 100
                if percentage == int(percentage):
                    key = f"loss_with_{int(percentage)}_percent"
                else:
                    key = f"loss_with_{percentage:.1f}_percent".replace(".", "_")
                metrics[key] = loss_at_prob
            else:
                percentage = target_prob * 100
                if percentage == int(percentage):
                    key = f"loss_with_{int(percentage)}_percent"
                else:
                    key = f"loss_with_{percentage:.1f}_percent".replace(".", "_")
                metrics[key] = 0

    return metrics


def run_agg_simulation(
    scenarios: Dict[str, Dict],
    n_simulations: int = 100_000,
    random_seed: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """
    Run Monte Carlo simulation for agg of risk scenarios.

    Args:
        scenarios: Dictionary of scenarios with keys 'P', 'LB', 'UB'
        n_simulations: Number of Monte Carlo iterations
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with scenario losses and portfolio total

    """
    rng = np.random.default_rng(random_seed)
    results = {}

    # Simulate each scenario
    for name, params in scenarios.items():
        losses = simulate_scenario_annual_loss(
            params["P"],
            params["LB"],
            params["UB"],
            n_simulations,
            rng.integers(0, 2**31),
        )
        results[name] = losses

    # Calculate portfolio total
    total_losses = np.zeros(n_simulations)
    for losses in results.values():
        total_losses += losses
    results["Portfolio_Total"] = total_losses

    return results


def get_lognormal_params_from_points(point1: Dict, point2: Dict) -> Tuple[float, float]:
    """
    Calculate lognormal distribution parameters (mu, sigma) from two risk tolerance points.

    Args:
        point1: Dict with 'probability' and 'acceptable_loss' keys
        point2: Dict with 'probability' and 'acceptable_loss' keys

    Returns:
        (mu, sigma): Parameters for lognormal distribution

    Raises:
        ValueError: If points are invalid or cannot fit lognormal distribution
    """
    # Extract values
    p1, loss1 = point1["probability"], point1["acceptable_loss"]
    p2, loss2 = point2["probability"], point2["acceptable_loss"]

    # Validate inputs
    if not (0 < p1 < 1 and 0 < p2 < 1):
        raise ValueError("Probabilities must be between 0 and 1")
    if not (loss1 > 0 and loss2 > 0):
        raise ValueError("Losses must be positive")
    if p1 == p2:
        raise ValueError("Points must have different probabilities")
    if loss1 == loss2:
        raise ValueError("Points must have different losses")

    # Convert probabilities to z-scores (normal quantiles)
    # We use 1-p because we want exceedance probabilities
    try:
        from scipy.stats import norm

        z1 = norm.ppf(1 - p1)  # Exceedance probability
        z2 = norm.ppf(1 - p2)
    except ImportError:
        raise ValueError(
            "scipy is required for risk tolerance curve generation. Please install scipy."
        )

    # Take logarithm of losses
    ln_loss1 = np.log(loss1)
    ln_loss2 = np.log(loss2)

    # Solve for sigma and mu
    # ln_loss = mu + sigma * z
    # ln_loss1 = mu + sigma * z1
    # ln_loss2 = mu + sigma * z2

    sigma = (ln_loss2 - ln_loss1) / (z2 - z1)
    mu = ln_loss1 - sigma * z1

    return mu, sigma


def generate_risk_tolerance_lec(
    point1: Dict, point2: Dict, n_points: int = 1000
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate Loss Exceedance Curve from two risk tolerance points using fitted lognormal distribution.

    Args:
        point1: Dict with 'probability' and 'acceptable_loss' keys
        point2: Dict with 'probability' and 'acceptable_loss' keys
        n_points: Number of points for the curve

    Returns:
        (loss_values, exceedance_probabilities): Arrays for plotting LEC
    """
    # Get lognormal parameters
    mu, sigma = get_lognormal_params_from_points(point1, point2)

    # Generate probability range (from high probability to low probability)
    min_prob = min(point1["probability"], point2["probability"])
    max_prob = max(point1["probability"], point2["probability"])

    # Extend range slightly beyond the points for better visualization
    prob_range = max_prob - min_prob
    min_display_prob = max(1e-6, min_prob - 0.1 * prob_range)
    max_display_prob = min(0.99, max_prob + 0.1 * prob_range)

    # Create exceedance probabilities (decreasing)
    exceedance_probs = np.logspace(
        np.log10(min_display_prob), np.log10(max_display_prob), n_points
    )[::-1]  # Reverse for decreasing order

    # Convert to normal quantiles and then to lognormal losses
    try:
        from scipy.stats import norm

        z_scores = norm.ppf(1 - exceedance_probs)
        loss_values = np.exp(mu + sigma * z_scores)
    except ImportError:
        raise ValueError(
            "scipy is required for risk tolerance curve generation. Please install scipy."
        )

    return loss_values, exceedance_probs


def risk_tolerance_curve(risk_tolerance_data: Dict) -> Dict:
    """
    Generate risk tolerance curve data from risk tolerance points.

    Args:
        risk_tolerance_data: Dict containing risk tolerance points

    Returns:
        Dict with curve data and fitted parameters
    """
    if not risk_tolerance_data or "points" not in risk_tolerance_data:
        return {}

    points = risk_tolerance_data["points"]

    # Check if we have both points
    if "point1" not in points or "point2" not in points:
        return {}

    point1 = points["point1"]
    point2 = points["point2"]

    # Validate point structure
    required_keys = ["probability", "acceptable_loss"]
    if not all(key in point1 and key in point2 for key in required_keys):
        return {}

    try:
        # Generate the LEC
        loss_values, exceedance_probs = generate_risk_tolerance_lec(point1, point2)

        # Get fitted parameters
        mu, sigma = get_lognormal_params_from_points(point1, point2)

        # Calculate distribution statistics
        try:
            from scipy.stats import lognorm

            dist = lognorm(s=sigma, scale=np.exp(mu))
        except ImportError:
            raise ValueError(
                "scipy is required for risk tolerance curve generation. Please install scipy."
            )

        return {
            "loss_values": loss_values.tolist(),
            "probability_values": exceedance_probs.tolist(),
            "fitted_parameters": {
                "mu": float(mu),
                "sigma": float(sigma),
                "distribution": "lognormal",
            },
            "statistics": {
                "mean": float(dist.mean()),
                "median": float(dist.median()),
                "std": float(dist.std()),
                "var_95": float(dist.ppf(0.95)),
                "var_99": float(dist.ppf(0.99)),
            },
        }

    except Exception as e:
        return {"error": str(e)}
