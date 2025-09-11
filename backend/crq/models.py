from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import ETADueDateMixin, NameDescriptionMixin
from core.models import (
    AppliedControl,
    Asset,
    FilteringLabelMixin,
    Qualification,
    Threat,
    Vulnerability,
)
from global_settings.models import GlobalSettings
from iam.models import FolderMixin, User
from .utils import (
    simulate_scenario_annual_loss,
    create_loss_exceedance_curve,
    calculate_risk_insights,
    risk_tolerance_curve,
)

import numpy as np


class QuantitativeRiskStudy(NameDescriptionMixin, ETADueDateMixin, FolderMixin):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        IN_PROGRESS = "in_progress", _("In progress")
        IN_REVIEW = "in_review", _("In review")
        DONE = "done", _("Done")
        DEPRECATED = "deprecated", _("Deprecated")

    class Distribution_model(models.TextChoices):
        LOGNORMAL_CI90 = "lognormal_ci90", _("Lognormal - CI 90")

    ref_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=100,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name=_("Status"),
        blank=True,
        null=True,
    )
    authors = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Authors"),
        related_name="quantitative_risk_study_authors",
    )
    reviewers = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Reviewers"),
        related_name="quantitative_risk_study_reviewers",
    )
    observation = models.TextField(null=True, blank=True, verbose_name=_("Observation"))
    risk_tolerance = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text=_(
            "Risk tolerance points and curve data. Expected format: {'points': {'point1': {'probability': float, 'acceptable_loss': float}, 'point2': {'probability': float, 'acceptable_loss': float}}, 'curve_data': {'loss_values': [...], 'probability_values': [...]}}"
        ),
    )
    distribution_model = models.CharField(
        max_length=100,
        choices=Distribution_model.choices,
        default=Distribution_model.LOGNORMAL_CI90,
        verbose_name=_("Distribution model"),
    )

    def __str__(self):
        return f"{self.name}"

    def get_risk_tolerance_display(self):
        """Return human-readable format of risk tolerance points"""
        if not self.risk_tolerance or not self.risk_tolerance.get("points"):
            return "Not configured"

        # Get currency from global settings
        from global_settings.models import GlobalSettings

        general_settings = GlobalSettings.objects.filter(name="general").first()
        currency = (
            general_settings.value.get("currency", "€") if general_settings else "€"
        )

        points = self.risk_tolerance["points"]
        display_parts = []

        # Handle point1
        if "point1" in points and isinstance(points["point1"], dict):
            point1 = points["point1"]
            prob = point1.get("probability")
            loss = point1.get("acceptable_loss")
            if prob is not None:
                prob_display = f"{prob * 100:.1f}%"
                if loss is not None:
                    loss_display = f"{loss:,.0f} {currency}"
                else:
                    loss_display = "N/A"
                display_parts.append(
                    f"Point 1: {prob_display} probability, {loss_display} acceptable loss"
                )

        # Handle point2
        if "point2" in points and isinstance(points["point2"], dict):
            point2 = points["point2"]
            prob = point2.get("probability")
            loss = point2.get("acceptable_loss")
            if prob is not None:
                prob_display = f"{prob * 100:.1f}%"
                if loss is not None:
                    loss_display = f"{loss:,.0f} {currency}"
                else:
                    loss_display = "N/A"
                display_parts.append(
                    f"Point 2: {prob_display} probability, {loss_display} acceptable loss"
                )

        return " | ".join(display_parts) if display_parts else "Not configured"

    def generate_risk_tolerance_curve(self):
        """
        Generate the risk tolerance Loss Exceedance Curve from the configured points.

        Returns:
            Dict with curve data, fitted parameters, and statistics
        """
        return risk_tolerance_curve(self.risk_tolerance)

    def save(self, *args, **kwargs):
        """
        Override save to mark related hypotheses simulation as not fresh when risk_tolerance changes.
        """
        # Check if risk_tolerance has changed (only for existing instances)
        if self.pk:
            try:
                old_instance = QuantitativeRiskStudy.objects.get(pk=self.pk)
                if old_instance.risk_tolerance != self.risk_tolerance:
                    # Mark all related hypotheses as not fresh
                    QuantitativeRiskHypothesis.objects.filter(
                        quantitative_risk_scenario__quantitative_risk_study=self
                    ).update(is_simulation_fresh=False)
            except QuantitativeRiskStudy.DoesNotExist:
                # This is a new instance, no need to compare with previous state
                pass

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Quantitative Risk Study")
        verbose_name_plural = _("Quantitative Risk Studies")
        ordering = ["created_at"]


class QuantitativeRiskScenario(NameDescriptionMixin, FolderMixin):
    quantitative_risk_study = models.ForeignKey(
        QuantitativeRiskStudy, on_delete=models.CASCADE, related_name="risk_scenarios"
    )
    assets = models.ManyToManyField(
        Asset,
        verbose_name=_("Assets"),
        blank=True,
        help_text=_("Assets impacted by the risk scenario"),
        related_name="quantitative_risk_scenarios",
    )
    owner = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Owner"),
        related_name="quantitative_risk_scenarios",
    )
    STATUS_OPTIONS = [
        ("draft", _("Draft")),
        ("open", _("Open")),
        ("mitigate", _("Mitigate")),
        ("accept", _("Accept")),
        ("transfer", _("Transfer")),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_OPTIONS,
        default="draft",
        verbose_name=_("status"),
    )
    vulnerabilities = models.ManyToManyField(
        Vulnerability,
        verbose_name=_("Vulnerabilities"),
        blank=True,
        help_text=_("Vulnerabities exploited by the risk scenario"),
        related_name="quantitative_risk_scenarios",
    )
    threats = models.ManyToManyField(
        Threat,
        verbose_name=_("Threats"),
        blank=True,
        related_name="quantitative_risk_scenarios",
    )
    qualifications = models.ManyToManyField(
        Qualification,
        related_name="quantitative_risk_scenarios",
        verbose_name="Qualifications",
        blank=True,
    )

    ref_id = models.CharField(max_length=100, blank=True)
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=True)

    @classmethod
    def get_default_ref_id(cls, quantitative_risk_study):
        """Return a unique reference ID for a given quantitative risk study."""
        scenarios_ref_ids = [
            x.ref_id for x in quantitative_risk_study.risk_scenarios.all()
        ]
        nb_scenarios = len(scenarios_ref_ids) + 1
        candidates = [f"QRS.{i:02d}" for i in range(1, nb_scenarios + 1)]
        return next(x for x in candidates if x not in scenarios_ref_ids)

    @property
    def current_ale(self):
        """
        Get the current Annual Loss Expectancy (ALE) from the current stage hypothesis.
        Returns None if no current stage hypothesis exists or has no simulation data.
        """
        current_hypothesis = self.hypotheses.filter(risk_stage="current").first()
        if not current_hypothesis or not current_hypothesis.simulation_data:
            return None

        metrics = current_hypothesis.simulation_data.get("metrics", {})
        return metrics.get("mean_annual_loss")

    @property
    def current_ale_display(self):
        """
        Get the current Annual Loss Expectancy (ALE) with currency from global settings.
        Returns "No current ALE calculated" if no ALE is available.
        """
        ale_value = self.current_ale
        if ale_value is None:
            return "No current ALE calculated"

        # Get currency from global settings
        general_settings = GlobalSettings.objects.filter(name="general").first()
        currency = (
            general_settings.value.get("currency", "€") if general_settings else "€"
        )

        return f"{ale_value:,.0f} {currency}"

    class Meta:
        verbose_name = _("Quantitative Risk Scenario")
        verbose_name_plural = _("Quantitative Risk Scenarios")
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["quantitative_risk_study", "name"],
                name="unique_scenario_name_per_study",
            )
        ]


class QuantitativeRiskHypothesis(
    NameDescriptionMixin, FilteringLabelMixin, FolderMixin
):
    RISK_STAGE_OPTIONS = [
        ("inherent", _("Inherent")),
        ("current", _("Current")),
        ("residual", _("Residual")),
    ]
    quantitative_risk_scenario = models.ForeignKey(
        QuantitativeRiskScenario, on_delete=models.CASCADE, related_name="hypotheses"
    )
    existing_applied_controls = models.ManyToManyField(
        AppliedControl,
        verbose_name=_("Existing Applied controls"),
        blank=True,
        related_name="quantitative_risk_hypotheses_existing",
    )
    added_applied_controls = models.ManyToManyField(
        AppliedControl,
        verbose_name=_("Added Applied controls"),
        blank=True,
        related_name="quantitative_risk_hypotheses_added",
    )
    removed_applied_controls = models.ManyToManyField(
        AppliedControl,
        verbose_name=_("Removed Applied controls"),
        blank=True,
        related_name="quantitative_risk_hypotheses_removed",
    )
    risk_stage = models.CharField(
        max_length=20,
        choices=RISK_STAGE_OPTIONS,
        default="current",
        verbose_name=_("risk stage"),
    )

    ref_id = models.CharField(max_length=100, blank=True)
    parameters = models.JSONField(blank=True, null=True, default=dict)
    simulation_data = models.JSONField(blank=True, null=True, default=dict)
    observation = models.TextField(null=True, blank=True, verbose_name=_("Observation"))

    is_simulation_fresh = models.BooleanField(
        verbose_name=_("Is simulation fresh"), default=False
    )

    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)

    @classmethod
    def get_default_ref_id(cls, quantitative_risk_scenario):
        """Return a unique reference ID for a given quantitative risk scenario."""
        hypotheses_ref_ids = [
            x.ref_id for x in quantitative_risk_scenario.hypotheses.all()
        ]
        nb_hypotheses = len(hypotheses_ref_ids) + 1
        candidates = [f"H.{i:02d}" for i in range(1, nb_hypotheses + 1)]
        return next(x for x in candidates if x not in hypotheses_ref_ids)

    class Meta:
        verbose_name = _("Quantitative Risk Hypothesis")
        verbose_name_plural = _("Quantitative Risk Hypotheses")
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["quantitative_risk_scenario", "name"],
                name="unique_hypothesis_name_per_scenario",
            ),
        ]

    def run_simulation(self, dry_run: bool = False):
        """
        Run Monte Carlo simulation for this risk hypothesis.
        Uses the actual probability and impact parameters stored in the hypothesis.
        - get lognormal params from UB and LB -> mu and sigma
        - bernouli trial based on P, to get a list of true, false
        - run simulation on how bad was it for events when it happened
        - generate downsampled dataset for LEC
        """
        # Get parameters from the hypothesis
        params = self.parameters or {}

        # Extract probability
        probability = params.get("probability")
        if probability is None:
            raise ValueError("Probability parameter is required for simulation")

        # Extract impact parameters
        impact = params.get("impact", {})
        if not impact:
            raise ValueError("Impact parameter is required for simulation")

        distribution = impact.get("distribution")
        lower_bound = impact.get("lb")
        upper_bound = impact.get("ub")

        # Validate required impact parameters
        if not all([distribution, lower_bound is not None, upper_bound is not None]):
            raise ValueError(
                "Impact must include distribution, lb (lower bound), and ub (upper bound)"
            )

        if distribution != "LOGNORMAL-CI90":
            raise ValueError("Only LOGNORMAL-CI90 distribution is currently supported")

        if lower_bound <= 0:
            raise ValueError("Lower bound must be positive")

        if upper_bound <= lower_bound:
            raise ValueError("Upper bound must be greater than lower bound")

        # Simulation configuration (can be made configurable later)
        n_simulations = 50_000
        random_seed = 42

        # 1. Run the simulation using actual parameters
        losses = simulate_scenario_annual_loss(
            probability=probability,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            n_simulations=n_simulations,
            random_seed=random_seed,
        )

        # 2. Generate Loss Exceedance Curve
        loss_values, exceedance_probs = create_loss_exceedance_curve(losses)

        # 3. Calculate risk metrics
        metrics = calculate_risk_insights(losses, probability)

        # 4. Downsample for visualization (take every nth point to reduce data size)
        downsample_factor = max(1, len(loss_values) // 1000)  # Max 1000 points
        downsampled_losses = loss_values[::downsample_factor].tolist()
        downsampled_probs = exceedance_probs[::downsample_factor].tolist()

        # 5. Store simulation results
        simulation_results = {
            "loss": downsampled_losses,
            "probability": downsampled_probs,
            "metrics": metrics,
            "parameters_used": {
                "probability": probability,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "distribution": distribution,
                "n_simulations": n_simulations,
            },
            "simulation_timestamp": str(self.updated_at),
        }

        if not dry_run:
            self.simulation_data = simulation_results
            self.is_simulation_fresh = True
            self.save(update_fields=["simulation_data", "is_simulation_fresh"])

            # Update the risk tolerance curve in the parent study
            study = self.quantitative_risk_scenario.quantitative_risk_study
            if study.risk_tolerance:
                curve_data = study.generate_risk_tolerance_curve()
                if curve_data and "error" not in curve_data:
                    # Update the risk_tolerance with the generated curve data
                    updated_risk_tolerance = study.risk_tolerance.copy()
                    updated_risk_tolerance["curve_data"] = curve_data
                    study.risk_tolerance = updated_risk_tolerance
                    study.save(update_fields=["risk_tolerance"])

        return simulation_results

    def get_simulation_parameters_display(self):
        """
        Returns a human-readable format of the simulation parameters.
        """
        params = self.parameters or {}
        if not params:
            return "No parameters configured"

        display_parts = []

        # Probability
        probability = params.get("probability")
        if probability is not None:
            display_parts.append(f"Probability: {probability * 100:.1f}%")

        # Impact parameters
        impact = params.get("impact", {})
        if impact:
            distribution = impact.get("distribution", "")
            lower_bound = impact.get("lb")
            upper_bound = impact.get("ub")

            if all([distribution, lower_bound is not None, upper_bound is not None]):
                # Format monetary values
                lb_formatted = self._format_currency(lower_bound)
                ub_formatted = self._format_currency(upper_bound)
                display_parts.append(
                    f"Impact: {lb_formatted} - {ub_formatted} ({distribution})"
                )

        if not display_parts:
            return "Parameters configured but not displayable"

        return "\n".join(display_parts)

    def _format_currency(self, value):
        """Helper method to format currency values."""
        # Get currency from global settings
        general_settings = GlobalSettings.objects.filter(name="general").first()
        currency = (
            general_settings.value.get("currency", "€") if general_settings else "€"
        )

        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M {currency}"
        elif value >= 1_000:
            return f"{value / 1_000:.0f}K {currency}"
        else:
            return f"{value:,.0f} {currency}"

    @property
    def treatment_cost(self):
        """Calculate the total treatment cost based on applied controls."""

        # I'm assuming that the current controls are part of the baseline so cost is not considered
        total_cost = 0

        # Add cost of added controls
        for control in self.added_applied_controls.all():
            total_cost += control.annual_cost

        # Subtract cost of removed controls (cost savings)
        for control in self.removed_applied_controls.all():
            total_cost -= control.annual_cost

        return total_cost

    @property
    def treatment_cost_display(self):
        """Returns a human-readable format of the treatment cost."""
        cost = self.treatment_cost
        if cost == 0:
            return "No cost"
        return self._format_currency(cost)

    @property
    def ale(self):
        """
        Get the Annual Loss Expectancy (ALE) from this hypothesis's simulation data.
        Returns None if no simulation data exists.
        """
        if not self.simulation_data:
            return None

        metrics = self.simulation_data.get("metrics", {})
        return metrics.get("mean_annual_loss")

    @property
    def roc(self):
        """
        Calculate Return on Controls (ROC) for residual hypotheses.

        reduction in expected loss is the diff between the current and the residual ALE

        ROC = (Current ALE - Residual ALE - Treatment Cost) / Treatment Cost

        Only applies to residual hypotheses. Returns None if:
        - This is not a residual hypothesis
        - No current hypothesis exists in the same scenario
        - Treatment cost is zero or negative
        - Missing ALE data
        """
        if self.risk_stage != "residual":
            return None

        # Find the current hypothesis in the same scenario
        current_hypothesis = self.quantitative_risk_scenario.hypotheses.filter(
            risk_stage="current"
        ).first()

        if not current_hypothesis:
            return None

        # Get ALEs
        current_ale = current_hypothesis.ale
        residual_ale = self.ale

        if current_ale is None or residual_ale is None:
            return None

        # Get treatment cost
        treatment_cost = self.treatment_cost

        if treatment_cost <= 0:
            return None

        # Calculate ROC
        risk_reduction = current_ale - residual_ale
        net_benefit = risk_reduction - treatment_cost
        roc = net_benefit / treatment_cost

        return roc

    @property
    def roc_display(self):
        """
        Returns a human-readable format of the ROC.
        """
        roc_value = self.roc
        if roc_value is None:
            if self.risk_stage != "residual":
                return "N/A (not residual hypothesis)"
            else:
                return "Cannot calculate ROC"

        # Format as percentage
        return f"{roc_value * 100:.0f}%"

    @property
    def roc_interpretation(self):
        """
        Returns an interpretation of the ROC value.
        """
        roc_value = self.roc
        if roc_value is None:
            return None

        if roc_value > 0:
            return "Positive ROC - Investment is profitable"
        elif roc_value == 0:
            return "Break-even - Investment covers its cost"
        else:
            return "Negative ROC - Investment costs more than benefits"

    def save(self, *args, **kwargs):
        """
        Override save to mark simulation as not fresh when parameters change.
        """
        # Check if parameters have changed (only for existing instances)
        if self.pk:
            try:
                old_instance = QuantitativeRiskHypothesis.objects.get(pk=self.pk)
                if old_instance.parameters != self.parameters:
                    self.is_simulation_fresh = False
            except QuantitativeRiskHypothesis.DoesNotExist:
                # This is a new instance, no need to compare with previous state
                pass

        super().save(*args, **kwargs)
