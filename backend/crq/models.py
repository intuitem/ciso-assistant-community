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
        ReferencePeriod.MONTH: 2592000,
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
