from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel, NameDescriptionMixin
from core.models import (
    FilteringLabelMixin,
    I18nObjectMixin,
    LoadedLibrary,
    ReferentialObjectMixin,
    Terminology,
)
from iam.models import FolderMixin, PublishInRootFolderMixin, User

import json


class MetricDefinition(ReferentialObjectMixin, I18nObjectMixin, FilteringLabelMixin):
    class Category(models.TextChoices):
        QUALITATIVE = "qualitative", _("Qualitative (Level)")
        QUANTITATIVE = "quantitative", _("Quantitative (Number)")

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
        default=Category.QUANTITATIVE,
        verbose_name=_("Category"),
    )
    unit = models.ForeignKey(
        Terminology,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name=_("Unit"),
        help_text=_(
            "Unit of measurement (e.g., count, users, bytes, percentage, score, event_per_second)"
        ),
        related_name="metric_definition_units",
        limit_choices_to={
            "field_path": Terminology.FieldPath.METRIC_UNIT,
            "is_visible": True,
        },
    )
    choices_definition = models.JSONField(
        blank=True,
        null=True,
        help_text=_(
            "For qualitative metrics: ordered list of options with translations. "
            "Format: [{'name': 'Low', 'description': '', 'translations': {'fr': {'name': 'Faible', 'description': ''}}}]"
        ),
    )
    is_published = models.BooleanField(default=True, verbose_name=_("Published"))
    higher_is_better = models.BooleanField(
        default=True,
        verbose_name=_("Higher is better"),
        help_text=_(
            "If true, an increase in value is considered positive (e.g., compliance score). "
            "If false, a decrease is considered positive (e.g., number of vulnerabilities)."
        ),
    )

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

    def current_value(self):
        """
        Returns the current value as a human-readable string.
        This is the display_value of the most recent sample.
        """
        latest_sample = self.get_latest_sample()
        if latest_sample:
            return latest_sample.display_value()
        return "N/A"

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

    def display_value(self):
        """
        Returns a human-readable display value based on the metric definition type
        """
        if not self.value:
            return "N/A"

        # Parse value if it's a string
        if isinstance(self.value, str):
            try:
                value_dict = json.loads(self.value)
            except (json.JSONDecodeError, TypeError):
                return "N/A"
        else:
            value_dict = self.value

        metric_definition = self.metric_instance.metric_definition

        # For qualitative metrics, show the choice name
        if metric_definition.category == MetricDefinition.Category.QUALITATIVE:
            choice_index = value_dict.get("choice_index")
            if (
                choice_index is not None
                and metric_definition.choices_definition
                and isinstance(metric_definition.choices_definition, list)
            ):
                # Convert 1-based index to 0-based for array access
                array_index = choice_index - 1
                if 0 <= array_index < len(metric_definition.choices_definition):
                    choice = metric_definition.choices_definition[array_index]
                    choice_name = choice.get("name", "")
                    return f"[{choice_index}] {choice_name}"
            return str(choice_index) if choice_index is not None else "N/A"

        # For quantitative metrics, show the result with unit
        elif metric_definition.category == MetricDefinition.Category.QUANTITATIVE:
            result = value_dict.get("result")
            if result is not None:
                if metric_definition.unit:
                    unit = metric_definition.unit.name
                    if metric_definition.unit.name == "percentage":
                        unit = "%"
                    if metric_definition.unit.name == "request_per_second":
                        unit = "RPS"
                    return f"{result} {unit}"
                return str(result)
            return "N/A"

        return "N/A"

    def save(self, *args, **kwargs):
        """Override save to update the parent metric instance's updated_at timestamp"""
        super().save(*args, **kwargs)
        # Touch the parent metric instance to update its updated_at field
        self.metric_instance.save(update_fields=["updated_at"])

    def delete(self, *args, **kwargs):
        """Override delete to update the parent metric instance's updated_at timestamp"""
        metric_instance = self.metric_instance
        result = super().delete(*args, **kwargs)
        # Touch the parent metric instance to update its updated_at field
        metric_instance.save(update_fields=["updated_at"])
        return result


class Dashboard(NameDescriptionMixin, FolderMixin, FilteringLabelMixin):
    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("reference id")
    )
    # Global dashboard settings (time range, refresh interval, layout type)
    dashboard_definition = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Global dashboard configuration. "
            "Format: {'layout': {'columns': 12, 'row_height': 100}, "
            "'global_filters': {'time_range': 'last_30_days', 'refresh_interval': 300}}"
        ),
    )

    class Meta:
        verbose_name = _("Dashboard")
        verbose_name_plural = _("Dashboards")
        ordering = ["name"]

    @property
    def widget_count(self):
        """Returns the number of widgets in this dashboard"""
        return self.widgets.count()


class DashboardWidget(AbstractBaseModel, FolderMixin):
    """
    Individual widget configuration for dashboards.
    Each widget displays a single metric instance with customizable visualization.
    """

    class ChartType(models.TextChoices):
        LINE = "line", _("Line Chart")
        BAR = "bar", _("Bar Chart")
        AREA = "area", _("Area Chart")
        GAUGE = "gauge", _("Gauge")
        KPI_CARD = "kpi_card", _("KPI Card")
        SPARKLINE = "sparkline", _("Sparkline")
        TABLE = "table", _("Table")

    class TimeRange(models.TextChoices):
        LAST_HOUR = "last_hour", _("Last Hour")
        LAST_24_HOURS = "last_24_hours", _("Last 24 Hours")
        LAST_7_DAYS = "last_7_days", _("Last 7 Days")
        LAST_30_DAYS = "last_30_days", _("Last 30 Days")
        LAST_90_DAYS = "last_90_days", _("Last 90 Days")
        LAST_YEAR = "last_year", _("Last Year")
        ALL_TIME = "all_time", _("All Time")
        CUSTOM = "custom", _("Custom Range")

    class Aggregation(models.TextChoices):
        NONE = "none", _("None (Raw Data)")
        AVG = "avg", _("Average")
        SUM = "sum", _("Sum")
        MIN = "min", _("Minimum")
        MAX = "max", _("Maximum")
        COUNT = "count", _("Count")
        LAST = "last", _("Last Value")

    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name="widgets",
        verbose_name=_("Dashboard"),
    )
    metric_instance = models.ForeignKey(
        MetricInstance,
        on_delete=models.CASCADE,
        related_name="dashboard_widgets",
        verbose_name=_("Metric instance"),
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Title"),
        help_text=_(
            "Custom title for the widget. If empty, uses metric instance name."
        ),
    )

    # Grid position (12-column grid layout)
    position_x = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Position X"),
        help_text=_("Horizontal position in grid (0-11)"),
    )
    position_y = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Position Y"),
        help_text=_("Vertical position in grid (row number)"),
    )
    width = models.PositiveIntegerField(
        default=6,
        verbose_name=_("Width"),
        help_text=_("Width in grid columns (1-12)"),
    )
    height = models.PositiveIntegerField(
        default=2,
        verbose_name=_("Height"),
        help_text=_("Height in grid rows"),
    )

    # Visualization settings
    chart_type = models.CharField(
        max_length=20,
        choices=ChartType.choices,
        default=ChartType.LINE,
        verbose_name=_("Chart type"),
    )
    time_range = models.CharField(
        max_length=20,
        choices=TimeRange.choices,
        default=TimeRange.LAST_30_DAYS,
        verbose_name=_("Time range"),
    )
    aggregation = models.CharField(
        max_length=20,
        choices=Aggregation.choices,
        default=Aggregation.NONE,
        verbose_name=_("Aggregation"),
    )

    # Display options
    show_target = models.BooleanField(
        default=True,
        verbose_name=_("Show target"),
        help_text=_("Display target value line if defined on metric instance"),
    )
    show_legend = models.BooleanField(
        default=True,
        verbose_name=_("Show legend"),
    )

    # Additional configuration stored as JSON for flexibility
    widget_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Additional widget configuration. "
            "Format: {'color_scheme': 'default', 'threshold_colors': {...}, 'custom_options': {...}}"
        ),
    )

    class Meta:
        verbose_name = _("Dashboard widget")
        verbose_name_plural = _("Dashboard widgets")
        ordering = ["position_y", "position_x"]

    def __str__(self):
        display_title = self.title or self.metric_instance.name
        return f"{display_title} ({self.get_chart_type_display()})"

    @property
    def display_title(self):
        """Returns the widget title or falls back to metric instance name"""
        return self.title or self.metric_instance.name

    def clean(self):
        """Validate widget configuration"""
        from django.core.exceptions import ValidationError

        # Validate grid position
        if self.position_x < 0 or self.position_x > 11:
            raise ValidationError(
                {"position_x": _("Position X must be between 0 and 11")}
            )
        if self.width < 1 or self.width > 12:
            raise ValidationError({"width": _("Width must be between 1 and 12")})
        if self.position_x + self.width > 12:
            raise ValidationError(
                {"width": _("Widget exceeds grid boundary (position_x + width > 12)")}
            )
        if self.height < 1:
            raise ValidationError({"height": _("Height must be at least 1")})
