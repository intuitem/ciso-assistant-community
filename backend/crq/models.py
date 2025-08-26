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
from iam.models import FolderMixin, User
from .utils import get_lognormal_params, parse_probability

import pymc as pm
import numpy as np


class QuantitativeRiskStudy(NameDescriptionMixin, ETADueDateMixin, FolderMixin):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        IN_PROGRESS = "in_progress", _("In progress")
        IN_REVIEW = "in_review", _("In review")
        DONE = "done", _("Done")
        DEPRECATED = "deprecated", _("Deprecated")

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

    class Meta:
        verbose_name = _("Quantitative Risk Study")
        verbose_name_plural = _("Quantitative Risk Studies")
        ordering = ["created_at"]


class QuantitativeRiskAggregation(NameDescriptionMixin, FolderMixin):
    quantitative_risk_study = models.ForeignKey(
        QuantitativeRiskStudy, on_delete=models.CASCADE, related_name="aggregations"
    )

    ref_id = models.CharField(max_length=100, blank=True)
    simulation_data = models.JSONField(blank=True, null=True, default=dict)

    class Meta:
        verbose_name = _("Quantitative Risk Aggregation")
        verbose_name_plural = _("Quantitative Risk Aggregations")
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


class QuantitativeRiskHypothesis(
    NameDescriptionMixin, FilteringLabelMixin, FolderMixin
):
    class ReferencePeriod(models.TextChoices):
        YEAR = "year", _("Year")
        MONTH = "month", _("Month")
        WEEK = "week", _("Week")
        DAY = "day", _("Day")
        HOUR = "hour", _("Hour")

    REFERENCE_PERIOD_SECONDS = {
        ReferencePeriod.YEAR: 31536000,
        ReferencePeriod.MONTH: 2628000,
        ReferencePeriod.WEEK: 604800,
        ReferencePeriod.DAY: 86400,
        ReferencePeriod.HOUR: 3600,
    }

    quantitative_risk_study = models.ForeignKey(
        QuantitativeRiskStudy, on_delete=models.CASCADE, related_name="hypotheses"
    )
    quantitative_risk_scenario = models.ForeignKey(
        QuantitativeRiskScenario, on_delete=models.CASCADE, related_name="hypotheses"
    )
    quantitative_risk_aggregations = models.ManyToManyField(
        QuantitativeRiskAggregation,
        verbose_name=_("Quantitative Risk Aggregations"),
        blank=True,
        related_name="hypotheses",
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

    ref_id = models.CharField(max_length=100, blank=True)
    estimated_parameters = models.JSONField(blank=True, null=True, default=dict)
    simulation_data = models.JSONField(blank=True, null=True, default=dict)
    justification = models.TextField(
        null=True, blank=True, verbose_name=_("Observation")
    )

    class Meta:
        verbose_name = _("Quantitative Risk Hypothesis")
        verbose_name_plural = _("Quantitative Risk Hypotheses")
        ordering = ["created_at"]

    def run_simulation(self, sim_size: int = 20000, write: bool = False) -> dict:
        """
        Runs a Monte Carlo simulation based on the data stored in the
        `estimated_parameters` field.

        Arguments:
            sim_size (int): Number of simulation iterations. Default is 20,000.
            write (bool): If True, saves the simulation results to the hypothesis instance.
        """
        ref_period = self.estimated_parameters.get("reference_period", "year")
        prob_data = self.estimated_parameters.get("probability")
        impact_data = self.estimated_parameters.get("impact")

        if not all([prob_data, impact_data]):
            raise ValueError(
                "Incomplete estimated parameters. Probability and impact are required."
            )

        time_units_in_seconds = {
            "year": 31536000,
            "month": 2628000,
            "day": 86400,
            "week": 604800,
            "hour": 3600,
        }
        ref_period_seconds = time_units_in_seconds.get(ref_period, 31536000)

        # Calculate probability, capping at 1.0 for a Bernoulli (single event) model
        probability = min(1.0, parse_probability(prob_data, ref_period_seconds))

        # Calculate log-normal parameters
        mu, sigma = get_lognormal_params(
            lb=impact_data.get("lb"), ub=impact_data.get("ub")
        )

        with pm.Model() as risk_model:
            event_occurs = pm.Bernoulli("event_occurs", p=probability)
            impact = pm.LogNormal("impact", mu=mu, sigma=sigma)
            total_loss = pm.Deterministic("total_loss", event_occurs * impact)

            idata = pm.sample_prior_predictive(samples=sim_size, random_seed=42)

        loss_samples = idata.prior.total_loss.values.flatten()
        non_zero_losses = loss_samples[loss_samples > 0]

        # compute loss exceedance
        # sort loss samples in descending order
        sorted_losses = np.sort(loss_samples)[::1]
        exceedance_probabilities = np.arange(1, len(sorted_losses) + 1) / len(
            sorted_losses
        )

        results = {
            "simulation_size": sim_size,
            "reference_period": ref_period,
            "probability_of_loss": len(non_zero_losses) / len(loss_samples)
            if len(loss_samples) > 0
            else 0,
            "expected_loss": np.mean(loss_samples),
            "statistics_if_loss_occurs": {
                "average": np.mean(non_zero_losses) if len(non_zero_losses) > 0 else 0,
                "median": np.median(non_zero_losses) if len(non_zero_losses) > 0 else 0,
                "min": np.min(non_zero_losses) if len(non_zero_losses) > 0 else 0,
                "max": np.max(non_zero_losses) if len(non_zero_losses) > 0 else 0,
            },
            "value_at_risk": {
                "var_90": np.percentile(loss_samples, 90),
                "var_95": np.percentile(loss_samples, 95),
                "var_99": np.percentile(loss_samples, 99),
            },
            "loss_exceedance": {
                "loss_amounts": sorted_losses.tolist(),
                "exceedance_probabilities": exceedance_probabilities.tolist(),
            },
        }

        if write:
            self.simulation_data = results
            self.save(update_fields=["simulation_data"])

        return results
