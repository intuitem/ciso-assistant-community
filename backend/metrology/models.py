from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel, NameDescriptionMixin
from core.models import (
    FilteringLabelMixin,
    I18nObjectMixin,
    LoadedLibrary,
    ReferentialObjectMixin,
)
from iam.models import FolderMixin, PublishInRootFolderMixin, User


class MetricDefinition(ReferentialObjectMixin, I18nObjectMixin, FilteringLabelMixin):
    class Category(models.TextChoices):
        QUALITATIVE = "qualitative", _("Qualitative")
        QUANTITATIVE_INT = "quantitative_int", _("Quantitative (Integer)")
        QUANTITATIVE_FLOAT = "quantitative_float", _("Quantitative (Float)")

    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="metric_definitions",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.QUANTITATIVE_FLOAT,
        verbose_name=_("Category"),
    )
    unit = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Unit"),
        help_text=_("Unit of measurement (e.g., seconds, count, percentage)"),
    )
    min_value = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Minimum value"),
        help_text=_("Minimum acceptable value for this metric"),
    )
    max_value = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Maximum value"),
        help_text=_("Maximum acceptable value for this metric"),
    )
    options_definition = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Options definition"),
        help_text=_(
            "For qualitative metrics: ordered list of options with translations. "
            "Format: [{'value': 0, 'name': 'Low', 'description': '', 'translations': {'fr': {'name': 'Faible'}}}]"
        ),
    )
    is_published = models.BooleanField(default=True, verbose_name=_("Published"))

    fields_to_check = ["ref_id", "name"]

    class Meta:
        verbose_name = _("Metric definition")
        verbose_name_plural = _("Metric definitions")
        ordering = ["name"]

    def is_deletable(self):
        """
        Returns True if the metric definition can be deleted
        """
        return not self.metricinstance_set.exists()

    def __str__(self):
        if self.name:
            return self.ref_id + " - " + self.name if self.ref_id else self.name
        else:
            return (
                self.ref_id + " - " + self.description
                if self.ref_id
                else self.description
            )


class MetricInstance(
    NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin, FilteringLabelMixin
):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        STALE = "stale", _("Stale")
        DEPRECATED = "deprecated", _("Deprecated")

    class Frequency(models.TextChoices):
        REALTIME = "realtime", _("Real-time (continuous)")
        HOURLY = "hourly", _("Hourly")
        DAILY = "daily", _("Daily")
        WEEKLY = "weekly", _("Weekly")
        MONTHLY = "monthly", _("Monthly")
        QUARTERLY = "quarterly", _("Quarterly")
        YEARLY = "yearly", _("Yearly")

    metric_definition = models.ForeignKey(
        MetricDefinition,
        on_delete=models.PROTECT,
        verbose_name=_("Metric definition"),
    )
    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("reference id")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Status"),
        db_index=True,
    )
    owner = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Owner"),
        related_name="metric_instances",
    )
    target_value = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Target value"),
        help_text=_("Target or optimal value for this metric instance"),
    )
    collection_frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        blank=True,
        null=True,
        verbose_name=_("Collection frequency"),
        help_text=_("Expected frequency for collecting metric samples"),
    )

    fields_to_check = ["ref_id", "name"]

    class Meta:
        verbose_name = _("Metric instance")
        verbose_name_plural = _("Metric instances")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def get_latest_sample(self):
        """Returns the most recent sample for this metric instance"""
        return self.samples.first()  # ordering is important

    def is_stale(self):
        """
        Checks if the metric instance is stale based on collection_frequency.
        Returns True if the last sample is older than expected.
        Uses strict thresholds suitable for alerting.
        """
        if not self.collection_frequency:
            return False

        latest_sample = self.get_latest_sample()
        if not latest_sample:
            # No samples yet - consider stale if active
            return self.status == self.Status.ACTIVE

        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        time_since_last_sample = now - latest_sample.timestamp

        # Strict staleness thresholds for alerting (frequency + small grace period)
        thresholds = {
            self.Frequency.REALTIME: timedelta(minutes=15),
            self.Frequency.HOURLY: timedelta(hours=2),
            self.Frequency.DAILY: timedelta(hours=36),  # 1.5 days
            self.Frequency.WEEKLY: timedelta(days=8),
            self.Frequency.MONTHLY: timedelta(days=32),
            self.Frequency.QUARTERLY: timedelta(days=95),
            self.Frequency.YEARLY: timedelta(days=370),
        }

        threshold = thresholds.get(self.collection_frequency)
        if threshold:
            return time_since_last_sample > threshold

        return False


class MetricSample(AbstractBaseModel, FolderMixin):
    metric_instance = models.ForeignKey(
        MetricInstance,
        on_delete=models.CASCADE,
        verbose_name=_("Metric instance"),
        related_name="samples",
    )
    timestamp = models.DateTimeField(
        verbose_name=_("Timestamp"),
        help_text=_("When the metric sample was recorded"),
        db_index=True,
    )
    value = models.JSONField(
        default=dict,
        verbose_name=_("Value"),
        help_text=_("The metric value (format depends on metric definition category)"),
    )

    class Meta:
        verbose_name = _("Metric sample")
        verbose_name_plural = _("Metric samples")
        ordering = ["-timestamp"]  # Most recent first

    def __str__(self):
        return f"{self.metric_instance} - {self.timestamp}"
