import numpy as np
from typing import Dict, Tuple, List, Optional, Union


def mu_sigma_from_lognorm_90pct(lower_bound: float, upper_bound: float):
    """
    Convert 90% confidence bounds to lognormal parameters.
    Assumes lower_bound = 5th percentile, upper_bound = 95th percentile.
    """
    z05, z95 = -1.64485362695147, 1.64485362695147
    ln_lb, ln_ub = np.log(lower_bound), np.log(upper_bound)
    sigma = (ln_ub - ln_lb) / (z95 - z05)
    mu = ln_lb - sigma * z05
    return mu, sigma


def simulate_portfolio_annual_losses(
    scenario_params: List[Dict[str, float]],
    n_simulations: int = 100_000,
    random_seed: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """
    Run Monte Carlo simulation for multiple risk scenarios simultaneously.
    This ensures mathematical consistency by using the same random draw
    for all scenarios in each simulation iteration.

    Args:
        scenario_params: List of dicts, each with keys:
            - 'name': scenario identifier
            - 'probability': Annual probability of event occurrence (0-1)
            - 'lower_bound': 5th percentile of loss when event occurs
            - 'upper_bound': 95th percentile of loss when event occurs
        n_simulations: Number of Monte Carlo iterations
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with scenario names as keys and annual loss arrays as values.
        Also includes 'Portfolio_Total' with sum of all scenarios.
    """
    if not scenario_params:
        return {}

    rng = np.random.default_rng(random_seed)
    results = {}

    # Pre-compute lognormal parameters for all scenarios
    scenario_distributions = []
    for scenario in scenario_params:
        if scenario["upper_bound"] <= scenario["lower_bound"]:
            raise ValueError(
                f"Upper bound must be greater than lower bound for scenario {scenario.get('name', 'unnamed')}"
            )
        if scenario["lower_bound"] <= 0:
            raise ValueError(
                f"Lower bound must be positive for scenario {scenario.get('name', 'unnamed')}"
            )

        mu, sigma = mu_sigma_from_lognorm_90pct(
            scenario["lower_bound"], scenario["upper_bound"]
        )
        scenario_distributions.append(
            {
                "name": scenario["name"],
                "probability": scenario["probability"],
                "mu": mu,
                "sigma": sigma,
            }
        )

    # Initialize loss arrays
    for scenario_dist in scenario_distributions:
        results[scenario_dist["name"]] = np.zeros(n_simulations)

    # Run simulation with consistent random draws across scenarios
    for i in range(n_simulations):
        # Single random draw for frequency determination across all scenarios
        frequency_draw = rng.random()

        for scenario_dist in scenario_distributions:
            # Stage 1: Frequency - does event occur this year?
            if frequency_draw < scenario_dist["probability"]:
                # Stage 2: Severity - what's the loss magnitude?
                # Use consistent random seed per iteration for severity
                severity_rng = np.random.default_rng(rng.integers(0, 2**31))
                loss = severity_rng.lognormal(
                    scenario_dist["mu"], scenario_dist["sigma"]
                )
                results[scenario_dist["name"]][i] = loss
            # else: loss remains 0 (initialized above)

    # Calculate portfolio total
    portfolio_losses = np.zeros(n_simulations)
    for scenario_name in results:
        portfolio_losses += results[scenario_name]
    results["Portfolio_Total"] = portfolio_losses

    return results


def simulate_portfolio_with_correlation(
    scenario_params: List[Dict[str, float]],
    correlation_matrix: Optional[np.ndarray] = None,
    n_simulations: int = 100_000,
    random_seed: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """
    Run Monte Carlo simulation for multiple risk scenarios with optional correlation.

    Args:
        scenario_params: List of scenario parameter dictionaries
        correlation_matrix: Optional correlation matrix for frequency events.
                          If None, assumes independence.
        n_simulations: Number of Monte Carlo iterations
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with scenario names as keys and annual loss arrays as values.
    """
    if not scenario_params:
        return {}

    n_scenarios = len(scenario_params)
    rng = np.random.default_rng(random_seed)

    # Pre-compute lognormal parameters
    scenario_distributions = []
    for scenario in scenario_params:
        mu, sigma = mu_sigma_from_lognorm_90pct(
            scenario["lower_bound"], scenario["upper_bound"]
        )
        scenario_distributions.append(
            {
                "name": scenario["name"],
                "probability": scenario["probability"],
                "mu": mu,
                "sigma": sigma,
            }
        )

    # Initialize results
    results = {}
    for scenario_dist in scenario_distributions:
        results[scenario_dist["name"]] = np.zeros(n_simulations)

    if correlation_matrix is not None:
        # Validate correlation matrix
        if correlation_matrix.shape != (n_scenarios, n_scenarios):
            raise ValueError(f"Correlation matrix must be {n_scenarios}x{n_scenarios}")
        if not np.allclose(correlation_matrix, correlation_matrix.T):
            raise ValueError("Correlation matrix must be symmetric")
        if not np.all(np.linalg.eigvals(correlation_matrix) >= 0):
            raise ValueError("Correlation matrix must be positive semi-definite")

        # Use multivariate normal for correlated frequency events
        mean = np.zeros(n_scenarios)

        # Generate correlated normal variables and convert to uniform
        for i in range(n_simulations):
            correlated_normals = rng.multivariate_normal(mean, correlation_matrix)
            # Convert to uniform using normal CDF approximation
            from scipy.stats import norm

            uniform_draws = norm.cdf(correlated_normals)

            for j, scenario_dist in enumerate(scenario_distributions):
                if uniform_draws[j] < scenario_dist["probability"]:
                    # Event occurs, sample severity
                    severity_rng = np.random.default_rng(rng.integers(0, 2**31))
                    loss = severity_rng.lognormal(
                        scenario_dist["mu"], scenario_dist["sigma"]
                    )
                    results[scenario_dist["name"]][i] = loss
    else:
        # Independent case - use the simpler approach
        return simulate_portfolio_annual_losses(
            scenario_params, n_simulations, random_seed
        )

    # Calculate portfolio total
    portfolio_losses = np.zeros(n_simulations)
    for scenario_name in results:
        if scenario_name != "Portfolio_Total":
            portfolio_losses += results[scenario_name]
    results["Portfolio_Total"] = portfolio_losses

    return results


def create_loss_exceedance_curve(losses: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create Loss Exceedance Curve from loss data.
    """
    sorted_losses = np.sort(losses)
    n = len(sorted_losses)
    exceedance_probs = 1 - (np.arange(n) / n)
    return sorted_losses, exceedance_probs


def calculate_risk_insights(
    losses: np.ndarray, probability: Optional[float] = None
) -> Dict[str, float]:
    """
    Calculate standard risk metrics from loss distribution.
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

    return metrics


def run_combined_simulation(
    scenarios_params: Dict[str, Dict[str, float]],
    n_simulations: int = 100_000,
    correlation_matrix: Optional[np.ndarray] = None,
    random_seed: Optional[int] = None,
) -> Dict[str, Dict]:
    """
    Run combined Monte Carlo simulation for multiple scenarios with consistent aggregation.

    Args:
        scenarios_params: Dictionary with scenario names as keys and parameter dicts as values.
                         Each parameter dict should have 'probability', 'lower_bound', 'upper_bound'.
        n_simulations: Number of Monte Carlo iterations
        correlation_matrix: Optional correlation matrix for scenarios
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with scenario results and combined portfolio metrics.
    """
    if not scenarios_params:
        return {}

    # Convert to list format for simulation
    scenario_list = []
    scenario_names = list(scenarios_params.keys())

    for name, params in scenarios_params.items():
        scenario_list.append(
            {
                "name": name,
                "probability": params["probability"],
                "lower_bound": params["lower_bound"],
                "upper_bound": params["upper_bound"],
            }
        )

    # Run simulation
    if correlation_matrix is not None:
        loss_results = simulate_portfolio_with_correlation(
            scenario_list, correlation_matrix, n_simulations, random_seed
        )
    else:
        loss_results = simulate_portfolio_annual_losses(
            scenario_list, n_simulations, random_seed
        )

    # Process results for each scenario + portfolio
    results = {}

    for name, losses in loss_results.items():
        # Create LEC
        loss_values, exceedance_probs = create_loss_exceedance_curve(losses)

        # Calculate metrics
        if name == "Portfolio_Total":
            metrics = calculate_risk_insights(losses)
        else:
            original_probability = scenarios_params[name]["probability"]
            metrics = calculate_risk_insights(losses, original_probability)

        # Downsample for visualization
        downsample_factor = max(1, len(loss_values) // 1000)
        downsampled_losses = loss_values[::downsample_factor]
        downsampled_probs = exceedance_probs[::downsample_factor]

        results[name] = {
            "loss": downsampled_losses.tolist(),
            "probability": downsampled_probs.tolist(),
            "metrics": metrics,
            "raw_losses": losses,  # Keep for further analysis if needed
        }

    return results


# Backward compatibility functions
def sum_lec_curves(
    curves_data: List[Tuple[np.ndarray, np.ndarray]], n_points: int = 1000
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Legacy function for summing LEC curves.
    Consider using run_combined_simulation() for better mathematical consistency.
    """
    # Import the original function to maintain compatibility
    from .utils import sum_lec_curves as original_sum_lec_curves

    return original_sum_lec_curves(curves_data, n_points)
