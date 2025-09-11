import numpy as np
from typing import Dict, Tuple, List, Optional, Union


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
            try:
                from scipy.stats import norm

                uniform_draws = norm.cdf(correlated_normals)
            except ImportError:
                raise ValueError(
                    "scipy is required for correlation support. Please install scipy."
                )

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


def run_agg_simulation(
    scenarios: Dict[str, Dict],
    n_simulations: int = 100_000,
    random_seed: Optional[int] = None,
) -> Dict[str, np.ndarray]:
    """
    Legacy function for backward compatibility.
    Now uses the new mathematically consistent approach.

    Args:
        scenarios: Dictionary of scenarios with keys 'P', 'LB', 'UB'
        n_simulations: Number of Monte Carlo iterations
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with scenario losses and portfolio total
    """
    # Convert old format to new format
    scenarios_params = {}
    for name, params in scenarios.items():
        scenarios_params[name] = {
            "probability": params["P"],
            "lower_bound": params["LB"],
            "upper_bound": params["UB"],
        }

    # Use new combined simulation approach
    simulation_results = run_combined_simulation(
        scenarios_params, n_simulations, random_seed=random_seed
    )

    # Convert back to old format (just raw losses)
    results = {}
    for name, result_data in simulation_results.items():
        results[name] = result_data["raw_losses"]

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


def sum_lec_curves(
    curves_data: List[Tuple[np.ndarray, np.ndarray]], n_points: int = 1000
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Sum multiple Loss Exceedance Curves by aggregating their underlying loss distributions.

    This approach works by:
    1. Finding the common loss value range across all curves
    2. Interpolating each curve to get probabilities at common loss points
    3. Converting exceedance probabilities to survival probabilities for independence
    4. Computing combined survival probabilities assuming independence
    5. Converting back to exceedance probabilities

    Args:
        curves_data: List of (loss_values, exceedance_probabilities) tuples
        n_points: Number of points for the output curve

    Returns:
        (combined_loss_values, combined_exceedance_probabilities)
    """
    if not curves_data or len(curves_data) == 0:
        return np.array([]), np.array([])

    if len(curves_data) == 1:
        return curves_data[0]

    # Find the overall loss range
    min_loss = min(
        np.min(losses[losses > 0]) for losses, _ in curves_data if len(losses) > 0
    )
    max_loss = max(np.max(losses) for losses, _ in curves_data if len(losses) > 0)

    # Create common loss points (logarithmic spacing for better resolution at lower losses)
    common_losses = np.logspace(np.log10(min_loss), np.log10(max_loss), n_points)

    # Interpolate each curve to common loss points
    combined_survival_prob = np.ones(n_points)

    for loss_values, exceedance_probs in curves_data:
        if len(loss_values) == 0 or len(exceedance_probs) == 0:
            continue

        # Ensure arrays are properly sorted
        sorted_indices = np.argsort(loss_values)
        sorted_losses = loss_values[sorted_indices]
        sorted_probs = exceedance_probs[sorted_indices]

        # Interpolate to common loss points
        # Use bounds_error=False, fill_value=0 to handle extrapolation
        interpolated_probs = np.interp(
            common_losses,
            sorted_losses,
            sorted_probs,
            left=1.0,  # For losses below minimum, probability = 1
            right=0.0,  # For losses above maximum, probability = 0
        )

        # Convert exceedance probability to survival probability for this scenario
        # P(total loss <= x) = 1 - P(this scenario exceeds x)
        survival_probs = 1 - interpolated_probs

        # Combine assuming independence: P(A and B both <= x) = P(A <= x) * P(B <= x)
        combined_survival_prob *= survival_probs

    # Convert back to exceedance probabilities
    combined_exceedance_probs = 1 - combined_survival_prob

    # Clean up numerical issues (ensure probabilities are between 0 and 1)
    combined_exceedance_probs = np.clip(combined_exceedance_probs, 0, 1)

    # Filter out points where probability is 1.0 (or very close to 1.0)
    # These represent zero-loss scenarios which aren't meaningful for visualization
    valid_indices = combined_exceedance_probs < 0.999
    filtered_losses = common_losses[valid_indices]
    filtered_probs = combined_exceedance_probs[valid_indices]

    # Sort by loss value to ensure proper curve ordering
    sort_indices = np.argsort(filtered_losses)

    return filtered_losses[sort_indices], filtered_probs[sort_indices]


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
