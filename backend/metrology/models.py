from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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
    default_target = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Default target"),
        help_text=_(
            "Default target value for metric instances. Can be overridden at instance level."
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
        return self.display_short


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

    def save(self, *args, **kwargs):
        # Inherit default_target from metric_definition if target_value is not set
        if self.target_value is None and self.metric_definition_id:
            if self.metric_definition.default_target is not None:
                self.target_value = self.metric_definition.default_target
        super().save(*args, **kwargs)

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


class CustomMetricSample(AbstractBaseModel, FolderMixin):
    """
    User-entered metric samples for custom metrics.
    Stores individual measurements recorded manually or via API.
    """

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
        verbose_name = _("Custom metric sample")
        verbose_name_plural = _("Custom metric samples")
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
                    if metric_definition.unit.name in ["score", "count"]:
                        unit = ""
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


class BuiltinMetricSample(AbstractBaseModel):
    """
    System-computed metric samples for builtin metrics.
    Stores daily snapshots of computed metrics for various objects
    (ComplianceAssessment, RiskAssessment, FindingsAssessment, Folder).
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content type"),
        help_text=_("The type of object this metric is computed for"),
    )
    object_id = models.UUIDField(
        verbose_name=_("Object ID"),
        help_text=_("The ID of the object this metric is computed for"),
        db_index=True,
    )
    object = GenericForeignKey("content_type", "object_id")

    date = models.DateField(
        verbose_name=_("Date"),
        help_text=_("The date this snapshot was recorded"),
        db_index=True,
    )
    metrics = models.JSONField(
        default=dict,
        verbose_name=_("Metrics"),
        help_text=_(
            "All computed metrics for this object. "
            "Format depends on object type (e.g., progress, result_breakdown, etc.)"
        ),
    )

    class Meta:
        verbose_name = _("Builtin metric sample")
        verbose_name_plural = _("Builtin metric samples")
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "date"],
                name="unique_builtin_metric_sample_per_object_per_day",
            )
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id", "date"]),
        ]

    def __str__(self):
        return f"{self.content_type.model} {self.object_id} - {self.date}"

    @classmethod
    def update_or_create_snapshot(cls, obj, date=None):
        """
        Update or create a daily metric snapshot for the given object.

        Args:
            obj: The model instance (ComplianceAssessment, RiskAssessment, etc.)
            date: Optional date for the snapshot. Defaults to today.

        Returns:
            Tuple of (BuiltinMetricSample, created)
        """
        from django.utils.timezone import now

        if date is None:
            date = now().date()

        content_type = ContentType.objects.get_for_model(obj)
        metrics = cls.compute_metrics(obj)

        return cls.objects.update_or_create(
            content_type=content_type,
            object_id=obj.id,
            date=date,
            defaults={"metrics": metrics},
        )

    @classmethod
    def compute_metrics(cls, obj):
        """
        Compute metrics for the given object based on its type.

        Args:
            obj: The model instance

        Returns:
            Dictionary of computed metrics
        """
        model_name = obj.__class__.__name__

        if model_name == "ComplianceAssessment":
            return cls._compute_compliance_assessment_metrics(obj)
        elif model_name == "RiskAssessment":
            return cls._compute_risk_assessment_metrics(obj)
        elif model_name == "FindingsAssessment":
            return cls._compute_findings_assessment_metrics(obj)
        elif model_name == "Folder":
            return cls._compute_folder_metrics(obj)
        else:
            return {}

    @classmethod
    def _compute_compliance_assessment_metrics(cls, assessment):
        """Compute metrics for a ComplianceAssessment."""
        from core.models import RequirementAssessment

        # Get requirement counts by status
        status_breakdown = {}
        for item in assessment.get_requirements_status_count():
            status_breakdown[item[1]] = item[0]

        # Get requirement counts by result
        result_breakdown = {}
        for item in assessment.get_requirements_result_count():
            result_breakdown[item[1]] = item[0]

        total = RequirementAssessment.objects.filter(
            compliance_assessment=assessment
        ).count()

        return {
            "progress": assessment.get_progress(),
            "score": assessment.get_global_score(),
            "total_requirements": total,
            "status_breakdown": status_breakdown,
            "result_breakdown": result_breakdown,
        }

    @classmethod
    def _compute_risk_assessment_metrics(cls, assessment):
        """Compute metrics for a RiskAssessment."""
        from core.models import RiskScenario
        from django.db.models import Count

        scenarios = RiskScenario.objects.filter(risk_assessment=assessment)
        total = scenarios.count()

        # Treatment breakdown
        treatment_breakdown = {}
        for treatment in RiskScenario.TREATMENT_OPTIONS:
            treatment_breakdown[treatment[0]] = scenarios.filter(
                treatment=treatment[0]
            ).count()

        # Get risk level labels from the risk matrix
        risk_level_labels = {}
        if assessment.risk_matrix:
            try:
                risk_levels = assessment.risk_matrix.risk or []
                for idx, level in enumerate(risk_levels):
                    # Each level is a dict with 'name', 'abbreviation', 'hexcolor', etc.
                    risk_level_labels[idx] = level.get("name", str(idx))
            except (KeyError, TypeError, AttributeError):
                # Handle cases where json_definition is missing or malformed
                pass

        # Current level breakdown
        current_level_counts = dict(
            scenarios.exclude(current_level=-1)
            .values("current_level")
            .annotate(count=Count("id"))
            .values_list("current_level", "count")
        )
        # Convert integer keys to labels
        current_level_breakdown = {
            risk_level_labels.get(k, str(k)): v for k, v in current_level_counts.items()
        }

        # Residual level breakdown
        residual_level_counts = dict(
            scenarios.exclude(residual_level=-1)
            .values("residual_level")
            .annotate(count=Count("id"))
            .values_list("residual_level", "count")
        )
        # Convert integer keys to labels
        residual_level_breakdown = {
            risk_level_labels.get(k, str(k)): v
            for k, v in residual_level_counts.items()
        }

        return {
            "total_scenarios": total,
            "treatment_breakdown": treatment_breakdown,
            "current_level_breakdown": current_level_breakdown,
            "residual_level_breakdown": residual_level_breakdown,
        }

    @classmethod
    def _compute_findings_assessment_metrics(cls, assessment):
        """Compute metrics for a FindingsAssessment."""
        from core.models import Finding, Severity
        from django.db.models import Count

        findings = Finding.objects.filter(findings_assessment=assessment)
        total = findings.count()

        # Severity breakdown
        severity_breakdown = dict(
            findings.values("severity")
            .annotate(count=Count("id"))
            .values_list("severity", "count")
        )
        # Convert severity integers to labels
        severity_labels = {choice[0]: choice[1] for choice in Severity.choices}
        severity_breakdown = {
            severity_labels.get(k, str(k)): v for k, v in severity_breakdown.items()
        }

        # Status breakdown
        status_breakdown = dict(
            findings.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        return {
            "total_findings": total,
            "severity_breakdown": severity_breakdown,
            "status_breakdown": status_breakdown,
        }

    @classmethod
    def _compute_folder_metrics(cls, folder):
        """Compute metrics for a Folder (domain-level aggregations)."""
        from core.models import AppliedControl, Incident, Severity
        from django.db.models import Count

        # Applied controls in this folder
        controls = AppliedControl.objects.filter(folder=folder)
        total_controls = controls.count()

        controls_status_breakdown = dict(
            controls.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        controls_category_breakdown = dict(
            controls.values("category")
            .annotate(count=Count("id"))
            .values_list("category", "count")
        )

        # Incidents in this folder
        incidents = Incident.objects.filter(folder=folder)
        total_incidents = incidents.count()

        incidents_severity_breakdown = dict(
            incidents.values("severity")
            .annotate(count=Count("id"))
            .values_list("severity", "count")
        )
        # Convert severity integers to labels
        severity_labels = {choice[0]: choice[1] for choice in Severity.choices}
        incidents_severity_breakdown = {
            severity_labels.get(k, str(k)): v
            for k, v in incidents_severity_breakdown.items()
        }

        incidents_status_breakdown = dict(
            incidents.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        return {
            "total_controls": total_controls,
            "controls_status_breakdown": controls_status_breakdown,
            "controls_category_breakdown": controls_category_breakdown,
            "total_incidents": total_incidents,
            "incidents_severity_breakdown": incidents_severity_breakdown,
            "incidents_status_breakdown": incidents_status_breakdown,
        }


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

    fields_to_check = ["ref_id", "name"]

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
    Each widget displays one of:
    - A custom metric (via metric_instance), or
    - A builtin metric (via target_content_type + target_object_id + metric_key), or
    - Text content with markdown support (via chart_type=TEXT + text_content)
    """

    class ChartType(models.TextChoices):
        KPI_CARD = "kpi_card", _("KPI Card")
        DONUT = "donut", _("Donut Chart")
        PIE = "pie", _("Pie Chart")
        BAR = "bar", _("Bar Chart")
        LINE = "line", _("Line Chart")
        AREA = "area", _("Area Chart")
        GAUGE = "gauge", _("Gauge")
        SPARKLINE = "sparkline", _("Sparkline")
        TABLE = "table", _("Table")
        TEXT = "text", _("Text")

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

    # Option 1: Custom metric (user-defined via MetricInstance)
    metric_instance = models.ForeignKey(
        MetricInstance,
        on_delete=models.CASCADE,
        related_name="dashboard_widgets",
        verbose_name=_("Metric instance"),
        null=True,
        blank=True,
        help_text=_("For custom metrics: the metric instance to display"),
    )

    # Option 2: Builtin metric (system-computed for an object)
    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Target content type"),
        help_text=_(
            "For builtin metrics: the type of object (e.g., ComplianceAssessment)"
        ),
    )
    target_object_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("Target object ID"),
        help_text=_("For builtin metrics: the ID of the specific object"),
    )
    metric_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Metric key"),
        help_text=_(
            "For builtin metrics: which metric to display (e.g., 'progress', 'result_breakdown')"
        ),
    )

    title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Title"),
        help_text=_(
            "Custom title for the widget. If empty, uses metric instance name or metric key."
        ),
    )

    # Option 3: Text widget (static content with markdown support)
    text_content = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Text content"),
        help_text=_("Markdown content for text widgets"),
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
        default=ChartType.KPI_CARD,
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
        verbose_name=_("Show title and legend"),
        help_text=_("Display widget title bar and legend (for charts)"),
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
        return f"{self.display_title} ({self.get_chart_type_display()})"

    @property
    def display_title(self):
        """Returns the widget title or falls back to metric instance name or metric key.
        Returns None for text widgets without a title (they don't need one).
        """
        if self.title:
            return self.title
        # Text widgets don't need a fallback title
        if self.chart_type == self.ChartType.TEXT:
            return None
        if self.metric_instance:
            return self.metric_instance.name
        if self.metric_key:
            # Format metric_key for display (e.g., "result_breakdown" -> "Result Breakdown")
            return self.metric_key.replace("_", " ").title()
        return _("Untitled Widget")

    @property
    def is_builtin_metric(self):
        """Returns True if this widget displays a builtin metric"""
        return self.target_content_type is not None and self.metric_key is not None

    @property
    def is_custom_metric(self):
        """Returns True if this widget displays a custom metric"""
        return self.metric_instance is not None

    @property
    def is_text_widget(self):
        """Returns True if this widget displays text content"""
        return self.chart_type == self.ChartType.TEXT

    def clean(self):
        """Validate widget configuration"""
        from django.core.exceptions import ValidationError

        # Text widgets only need title and text_content, not metrics
        if self.is_text_widget:
            # Text widgets should not have metric fields set
            if self.metric_instance is not None:
                raise ValidationError(
                    {
                        "metric_instance": _(
                            "Text widgets should not have a metric instance."
                        )
                    }
                )
            if self.target_content_type is not None:
                raise ValidationError(
                    {
                        "target_content_type": _(
                            "Text widgets should not have builtin metric fields."
                        )
                    }
                )
            return  # Text widgets are valid without metrics

        # For non-text widgets: validate mutual exclusivity of custom metric OR builtin metric
        # For builtin detection, require target_content_type to be set
        # (target_object_id and metric_key alone don't constitute a builtin metric)
        has_custom = self.metric_instance is not None
        has_builtin = self.target_content_type is not None

        if has_custom and has_builtin:
            raise ValidationError(
                _(
                    "A widget cannot have both a custom metric instance and builtin metric fields. "
                    "Use either metric_instance OR (target_content_type + target_object_id + metric_key)."
                )
            )

        if not has_custom and not has_builtin:
            raise ValidationError(
                {
                    "metric_instance": _(
                        "A metric instance is required for custom metric widgets."
                    )
                }
            )

        # If builtin metric, ensure all required fields are present
        if has_builtin:
            if not self.target_content_type:
                raise ValidationError(
                    {
                        "target_content_type": _(
                            "Target content type is required for builtin metrics"
                        )
                    }
                )
            if not self.target_object_id:
                raise ValidationError(
                    {
                        "target_object_id": _(
                            "Target object ID is required for builtin metrics"
                        )
                    }
                )
            if not self.metric_key:
                raise ValidationError(
                    {"metric_key": _("Metric key is required for builtin metrics")}
                )

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


def get_builtin_metrics_retention_days():
    """
    Returns the retention days for builtin metric samples from global settings.
    Default is 730 days (2 years), minimum is 1 day.
    """
    from global_settings.models import GlobalSettings

    try:
        settings = GlobalSettings.objects.get(name="general")
        retention = settings.value.get("builtin_metrics_retention_days", 730)
        return max(1, int(retention))
    except (GlobalSettings.DoesNotExist, TypeError, ValueError):
        return 730
