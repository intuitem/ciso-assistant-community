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
        "prob_above_1M": np.mean(losses > 1_000_000),
        "prob_above_10M": np.mean(losses > 10_000_000),
        "prob_above_100M": np.mean(losses > 100_000_000),
    }

    # Add probability-based loss metrics if probability is provided
    if probability is not None and probability > 0:
        # Create loss exceedance curve
        sorted_losses, exceedance_probs = create_loss_exceedance_curve(losses)

        # Find losses at P/2, P/4, P/8 probability levels
        target_probs = [probability / 2, probability / 4, probability / 8]

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


def get_lognormal_params():
    pass


def risk_tolerance_curve():
    pass
