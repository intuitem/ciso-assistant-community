import json
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Avg, Count, OuterRef, Q, Subquery, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel, NameDescriptionMixin
from core.models import (
    Actor,
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    Finding,
    FilteringLabelMixin,
    Framework,
    I18nObjectMixin,
    Incident,
    LoadedLibrary,
    ReferentialObjectMixin,
    RequirementAssessment,
    RiskAcceptance,
    RiskScenario,
    SecurityException,
    Severity,
    TaskNode,
    TaskTemplate,
    Terminology,
    Vulnerability,
)
from global_settings.models import GlobalSettings
from iam.models import Folder, FolderMixin, PublishInRootFolderMixin, User


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
        Actor,
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

    evidences = models.ForeignKey(
        Evidence,
        on_delete=models.SET_NULL,
        related_name="metric_instances",
        blank=True,
        null=True,
    )
    fields_to_check = ["ref_id", "name"]

    class Meta:
        verbose_name = _("Metric instance")
        verbose_name_plural = _("Metric instances")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if self.target_value is None and self.metric_definition_id:
            if self.metric_definition.default_target is not None:
                self.target_value = self.metric_definition.default_target
        super().save(*args, **kwargs)

    def get_latest_sample(self):
        return self.samples.first()  # ordering is important

    def last_refresh(self):
        latest_sample = self.get_latest_sample()
        if latest_sample:
            return latest_sample.timestamp
        return None

    def current_value(self):
        latest_sample = self.get_latest_sample()
        if latest_sample:
            return latest_sample.display_value()
        return "N/A"

    def raw_value(self):
        latest_sample = self.get_latest_sample()
        if latest_sample:
            return latest_sample.raw_value()
        return None

    @property
    def unit(self):
        if self.metric_definition and self.metric_definition.unit:
            return self.metric_definition.unit
        return None

    def is_stale(self):
        # Strict thresholds suitable for alerting: collection_frequency + grace period.
        if not self.collection_frequency:
            return False

        latest_sample = self.get_latest_sample()
        if not latest_sample:
            return self.status == self.Status.ACTIVE

        now = timezone.now()
        time_since_last_sample = now - latest_sample.timestamp

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

    observation = models.TextField(null=True, blank=True, verbose_name=_("Observation"))
    evidence_revision = models.ForeignKey(
        EvidenceRevision,
        on_delete=models.SET_NULL,
        related_name="samples",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Custom metric sample")
        verbose_name_plural = _("Custom metric samples")
        ordering = ["-timestamp"]  # Most recent first

    def __str__(self):
        return f"{self.metric_instance} - {self.timestamp}"

    def raw_value(self):
        if not self.value:
            return None

        if isinstance(self.value, str):
            try:
                value_dict = json.loads(self.value)
            except json.JSONDecodeError, TypeError:
                return None
        else:
            value_dict = self.value

        metric_definition = self.metric_instance.metric_definition

        if metric_definition.category == MetricDefinition.Category.QUALITATIVE:
            return value_dict.get("choice_index")

        elif metric_definition.category == MetricDefinition.Category.QUANTITATIVE:
            return value_dict.get("result")

        return None

    def display_value(self):
        if not self.value:
            return "N/A"

        if isinstance(self.value, str):
            try:
                value_dict = json.loads(self.value)
            except json.JSONDecodeError, TypeError:
                return "N/A"
        else:
            value_dict = self.value

        metric_definition = self.metric_instance.metric_definition

        if metric_definition.category == MetricDefinition.Category.QUALITATIVE:
            choice_index = value_dict.get("choice_index")
            if (
                choice_index is not None
                and metric_definition.choices_definition
                and isinstance(metric_definition.choices_definition, list)
            ):
                # choices_definition is 1-indexed.
                array_index = choice_index - 1
                if 0 <= array_index < len(metric_definition.choices_definition):
                    choice = metric_definition.choices_definition[array_index]
                    choice_name = choice.get("name", "")
                    return f"[{choice_index}] {choice_name}"
            return str(choice_index) if choice_index is not None else "N/A"

        elif metric_definition.category == MetricDefinition.Category.QUANTITATIVE:
            result = value_dict.get("result")
            if result is not None:
                if metric_definition.unit:
                    unit = (
                        metric_definition.unit.get_name_translated
                        or metric_definition.unit.name
                    )
                    if metric_definition.unit.name == "percentage":
                        unit = "%"
                    elif metric_definition.unit.name in ["score", "count"]:
                        unit = ""
                    elif metric_definition.unit.name == "request_per_second":
                        unit = "RPS"
                    else:
                        # Naive singular: drop trailing "s" when result is ±1.
                        if abs(result) == 1 and unit.endswith("s") and len(unit) > 1:
                            unit = unit[:-1]
                    if unit:
                        return f"{result} {unit}"
                return str(result)
            return "N/A"

        return "N/A"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.metric_instance.save(update_fields=["updated_at"])

    def delete(self, *args, **kwargs):
        metric_instance = self.metric_instance
        result = super().delete(*args, **kwargs)
        metric_instance.save(update_fields=["updated_at"])
        return result


class BuiltinMetricSample(AbstractBaseModel):
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
    def update_or_create_snapshot(cls, obj, date=None, precomputed_metrics=None):
        # Returns (sample, created). Pass precomputed_metrics to skip compute_metrics().
        if date is None:
            date = timezone.now().date()

        content_type = ContentType.objects.get_for_model(obj)
        metrics = (
            precomputed_metrics
            if precomputed_metrics is not None
            else cls.compute_metrics(obj)
        )

        return cls.objects.update_or_create(
            content_type=content_type,
            object_id=obj.id,
            date=date,
            defaults={"metrics": metrics},
        )

    @classmethod
    def compute_metrics(cls, obj):
        model_name = obj.__class__.__name__

        if model_name == "ComplianceAssessment":
            return cls._compute_compliance_assessment_metrics(obj)
        elif model_name == "RiskAssessment":
            return cls._compute_risk_assessment_metrics(obj)
        elif model_name == "FindingsAssessment":
            return cls._compute_findings_assessment_metrics(obj)
        elif model_name == "Folder":
            return cls._compute_folder_metrics(obj)
        elif model_name == "Project":
            return cls._compute_project_metrics(obj)
        else:
            return {}

    @classmethod
    def _compute_project_metrics(cls, project):
        return {
            "status": project.status.name if project.status_id else None,
            "health": project.health.name if project.health_id else None,
            "priority": project.priority,
            "progress": project.progress,
            "start_date": project.start_date.isoformat()
            if project.start_date
            else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "eta": project.eta.isoformat() if project.eta else None,
            "budget": float(project.budget) if project.budget is not None else None,
            "actual_cost": float(project.actual_cost)
            if project.actual_cost is not None
            else None,
            "currency": project.currency or "",
        }

    @classmethod
    def _compute_compliance_assessment_metrics(cls, assessment):
        status_breakdown = {}
        for item in assessment.get_requirements_status_count():
            status_breakdown[item[1]] = item[0]

        result_breakdown = {}
        for item in assessment.get_requirements_result_count():
            result_breakdown[item[1]] = item[0]

        total = RequirementAssessment.objects.filter(
            compliance_assessment=assessment
        ).count()

        return {
            "progress": assessment.progress,
            "score": assessment.get_global_score()["maturity_score"],
            "total_requirements": total,
            "status_breakdown": status_breakdown,
            "result_breakdown": result_breakdown,
        }

    @classmethod
    def _compute_risk_assessment_metrics(cls, assessment):
        scenarios = RiskScenario.objects.filter(risk_assessment=assessment)
        total = scenarios.count()

        qualifications_breakdown = dict(
            scenarios.values("qualifications__name")
            .annotate(count=Count("id", distinct=True))
            .filter(qualifications__name__isnull=False)
            .values_list("qualifications__name", "count")
        )

        treatment_breakdown = {}
        for treatment in RiskScenario.TREATMENT_OPTIONS:
            treatment_breakdown[treatment[0]] = scenarios.filter(
                treatment=treatment[0]
            ).count()

        risk_level_labels = {}
        if assessment.risk_matrix:
            try:
                risk_levels = assessment.risk_matrix.risk or []
                for idx, level in enumerate(risk_levels):
                    risk_level_labels[idx] = level.get("name", str(idx))
            except KeyError, TypeError, AttributeError:
                pass

        current_level_counts = dict(
            scenarios.exclude(current_level=-1)
            .values("current_level")
            .annotate(count=Count("id"))
            .values_list("current_level", "count")
        )
        current_level_breakdown = {
            risk_level_labels.get(k, str(k)): v for k, v in current_level_counts.items()
        }

        residual_level_counts = dict(
            scenarios.exclude(residual_level=-1)
            .values("residual_level")
            .annotate(count=Count("id"))
            .values_list("residual_level", "count")
        )
        residual_level_breakdown = {
            risk_level_labels.get(k, str(k)): v
            for k, v in residual_level_counts.items()
        }

        return {
            "total_scenarios": total,
            "treatment_breakdown": treatment_breakdown,
            "current_level_breakdown": current_level_breakdown,
            "residual_level_breakdown": residual_level_breakdown,
            "qualifications_breakdown": qualifications_breakdown,
        }

    @classmethod
    def _compute_findings_assessment_metrics(cls, assessment):
        findings = Finding.objects.filter(findings_assessment=assessment)
        total = findings.count()

        severity_breakdown = dict(
            findings.values("severity")
            .annotate(count=Count("id"))
            .values_list("severity", "count")
        )
        severity_labels = {choice[0]: choice[1] for choice in Severity.choices}
        severity_breakdown = {
            severity_labels.get(k, str(k)): v for k, v in severity_breakdown.items()
        }

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
        # Root folder = unfiltered org-wide scope; others = direct membership only
        # (no descendant traversal, matching the existing breakdown metrics).
        is_global = folder.content_type == Folder.ContentType.ROOT
        today = timezone.localdate()

        def scope(qs):
            return qs if is_global else qs.filter(folder=folder)

        controls = scope(AppliedControl.objects.all())
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

        incidents = scope(Incident.objects.all())
        total_incidents = incidents.count()

        incidents_severity_raw = dict(
            incidents.values("severity")
            .annotate(count=Count("id"))
            .values_list("severity", "count")
        )
        incident_severity_labels = {
            choice[0]: choice[1] for choice in Incident.Severity.choices
        }
        incidents_severity_breakdown = {
            incident_severity_labels.get(k, str(k)): v
            for k, v in incidents_severity_raw.items()
        }

        incidents_status_breakdown = dict(
            incidents.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        incidents_detection_raw = dict(
            incidents.exclude(detection__in=[None, ""])
            .values("detection")
            .annotate(count=Count("id"))
            .values_list("detection", "count")
        )
        detection_labels = {
            choice[0]: choice[1] for choice in Incident.Detection.choices
        }
        incidents_detection_breakdown = {
            detection_labels.get(k, str(k)): v
            for k, v in incidents_detection_raw.items()
        }

        incidents_qualifications_breakdown = dict(
            incidents.values("qualifications__name")
            .annotate(count=Count("id", distinct=True))
            .filter(qualifications__name__isnull=False)
            .values_list("qualifications__name", "count")
        )

        # Task templates: status comes from TaskNode (current node for non-recurrent,
        # latest past occurrence for recurrent). Mirrors helpers.task_template_per_status.
        task_templates = scope(TaskTemplate.objects.all())
        task_templates_status_breakdown = {
            label: 0 for _key, label in TaskNode.TASK_STATUS_CHOICES
        }
        status_label_by_key = dict(TaskNode.TASK_STATUS_CHOICES)

        last_occurrence_subq = (
            TaskNode.objects.filter(task_template=OuterRef("pk"), due_date__lt=today)
            .order_by("-due_date")
            .values("status")[:1]
        )
        single_node_subq = (
            TaskNode.objects.filter(task_template=OuterRef("pk"))
            .order_by("-due_date")
            .values("status")[:1]
        )

        for status in (
            task_templates.filter(is_recurrent=True)
            .annotate(node_status=Subquery(last_occurrence_subq))
            .values_list("node_status", flat=True)
        ):
            label = status_label_by_key.get(status or "pending", "pending")
            task_templates_status_breakdown[label] = (
                task_templates_status_breakdown.get(label, 0) + 1
            )
        for status in (
            task_templates.filter(is_recurrent=False)
            .annotate(node_status=Subquery(single_node_subq))
            .values_list("node_status", flat=True)
        ):
            label = status_label_by_key.get(status or "pending", "pending")
            task_templates_status_breakdown[label] = (
                task_templates_status_breakdown.get(label, 0) + 1
            )

        security_exceptions = scope(SecurityException.objects.all())
        total_security_exceptions = security_exceptions.count()

        security_exceptions_status_breakdown = dict(
            security_exceptions.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        sec_exc_severity_raw = dict(
            security_exceptions.values("severity")
            .annotate(count=Count("id"))
            .values_list("severity", "count")
        )
        severity_labels = {choice[0]: choice[1] for choice in Severity.choices}
        security_exceptions_severity_breakdown = {
            severity_labels.get(k, str(k)): v for k, v in sec_exc_severity_raw.items()
        }

        total_risk_acceptances = scope(RiskAcceptance.objects.all()).count()

        # Risk scenarios qualifications (scoped via the parent risk assessment's folder)
        risk_scenarios_qs = (
            RiskScenario.objects.all()
            if is_global
            else RiskScenario.objects.filter(risk_assessment__folder=folder)
        )
        risk_scenarios_qualifications_breakdown = dict(
            risk_scenarios_qs.values("qualifications__name")
            .annotate(count=Count("id", distinct=True))
            .filter(qualifications__name__isnull=False)
            .values_list("qualifications__name", "count")
        )

        # Frameworks "in use" = distinct frameworks referenced by accessible audits
        audits_qs = (
            ComplianceAssessment.objects.all()
            if is_global
            else ComplianceAssessment.objects.filter(folder=folder)
        )
        total_frameworks_in_use = Framework.objects.filter(
            id__in=audits_qs.values_list("framework_id", flat=True).distinct()
        ).count()

        assets = scope(Asset.objects.all())
        total_assets = assets.count()
        # gettext_lazy proxies serialize as dict keys only after str() — satisfy dict.get/__eq__ but break json.dumps.
        assets_type_labels = {
            choice[0]: str(choice[1]) for choice in Asset.Type.choices
        }
        assets_type_breakdown = {
            assets_type_labels.get(k, str(k)): v
            for k, v in assets.values("type")
            .annotate(count=Count("id"))
            .values_list("type", "count")
        }

        evidence = scope(Evidence.objects.all())
        total_evidence = evidence.count()
        evidence_status_labels = {
            choice[0]: str(choice[1]) for choice in Evidence.Status.choices
        }
        evidence_status_breakdown = {
            evidence_status_labels.get(k, str(k)): v
            for k, v in evidence.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        }
        evidence_expiring_30d = evidence.filter(
            expiry_date__isnull=False,
            expiry_date__gte=today,
            expiry_date__lte=today + timedelta(days=30),
        ).count()

        vulnerabilities = scope(Vulnerability.objects.all())
        total_vulnerabilities = vulnerabilities.count()
        vuln_severity_raw = dict(
            vulnerabilities.values("severity")
            .annotate(count=Count("id"))
            .values_list("severity", "count")
        )
        # Vulnerability.severity uses the shared core Severity choices.
        vuln_severity_breakdown = {
            severity_labels.get(k, str(k)): v for k, v in vuln_severity_raw.items()
        }
        vuln_status_labels = {
            choice[0]: str(choice[1]) for choice in Vulnerability.Status.choices
        }
        vulnerabilities_status_breakdown = {
            vuln_status_labels.get(k, str(k)): v
            for k, v in vulnerabilities.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        }

        # Task occurrences: overdue + due in next 7 days (excluding completed / cancelled).
        # TaskNode.folder is propagated from its TaskTemplate.folder, so direct filter is correct.
        open_tasks = scope(TaskNode.objects.all()).exclude(
            status__in=["completed", "cancelled"]
        )
        tasks_overdue = open_tasks.filter(due_date__lt=today).count()
        tasks_due_7d = open_tasks.filter(
            due_date__gte=today, due_date__lte=today + timedelta(days=7)
        ).count()

        eta_on_track = controls.filter(Q(eta__isnull=False) & Q(eta__gte=today)).count()
        eta_late = controls.filter(
            Q(eta__isnull=False)
            & Q(eta__lt=today)
            & ~Q(status__in=["active", "deprecated"])
        ).count()
        eta_no_eta = controls.filter(eta__isnull=True).count()
        controls_eta_breakdown = {
            str(_("On track")): eta_on_track,
            str(_("Late")): eta_late,
            str(_("No ETA")): eta_no_eta,
        }
        controls_priority_breakdown = {
            str(k if k is not None else _("Unset")): v
            for k, v in controls.values("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        }

        total_audits = audits_qs.count()
        audit_status_labels = {
            choice[0]: str(choice[1]) for choice in ComplianceAssessment.Status.choices
        }
        audits_status_breakdown = {
            audit_status_labels.get(k, str(k) if k else str(_("Unset"))): v
            for k, v in audits_qs.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        }
        # N+1: progress is a @property doing 1+ queries per audit. Bounded by snapshot cadence.
        if total_audits:
            progresses = [a.progress for a in audits_qs]
            audits_avg_progress = (
                round(sum(progresses) / len(progresses)) if progresses else 0
            )
        else:
            audits_avg_progress = 0

        # Lazy import: pmbok.models imports metrology.models in Project.save() — leave inline.
        from pmbok.models import Project as _Project

        projects = scope(_Project.objects.all())
        projects_total = projects.count()
        projects_status_breakdown = dict(
            projects.exclude(status__isnull=True)
            .values("status__name")
            .annotate(count=Count("id"))
            .values_list("status__name", "count")
        )
        projects_health_breakdown = dict(
            projects.exclude(health__isnull=True)
            .values("health__name")
            .annotate(count=Count("id"))
            .values_list("health__name", "count")
        )
        projects_priority_breakdown = dict(
            projects.exclude(priority__isnull=True)
            .values("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        )
        projects_priority_labels = {k: str(v) for k, v in _Project.PRIORITY}
        projects_priority_breakdown = {
            projects_priority_labels.get(k, str(k)): v
            for k, v in projects_priority_breakdown.items()
        }
        projects_aggs = projects.aggregate(
            avg_progress=Avg("progress"),
            total_budget=Sum("budget"),
            total_actual_cost=Sum("actual_cost"),
        )
        projects_avg_progress = (
            round(projects_aggs["avg_progress"])
            if projects_aggs["avg_progress"] is not None
            else 0
        )
        projects_total_budget = (
            float(projects_aggs["total_budget"])
            if projects_aggs["total_budget"] is not None
            else 0
        )
        projects_total_actual_cost = (
            float(projects_aggs["total_actual_cost"])
            if projects_aggs["total_actual_cost"] is not None
            else 0
        )

        return {
            "total_controls": total_controls,
            "controls_status_breakdown": controls_status_breakdown,
            "controls_category_breakdown": controls_category_breakdown,
            "controls_eta_breakdown": controls_eta_breakdown,
            "controls_priority_breakdown": controls_priority_breakdown,
            "total_incidents": total_incidents,
            "incidents_severity_breakdown": incidents_severity_breakdown,
            "incidents_status_breakdown": incidents_status_breakdown,
            "incidents_detection_breakdown": incidents_detection_breakdown,
            "incidents_qualifications_breakdown": incidents_qualifications_breakdown,
            "task_templates_status_breakdown": task_templates_status_breakdown,
            "security_exceptions_status_breakdown": security_exceptions_status_breakdown,
            "security_exceptions_severity_breakdown": security_exceptions_severity_breakdown,
            "total_security_exceptions": total_security_exceptions,
            "total_risk_acceptances": total_risk_acceptances,
            "total_frameworks_in_use": total_frameworks_in_use,
            "risk_scenarios_qualifications_breakdown": risk_scenarios_qualifications_breakdown,
            "total_assets": total_assets,
            "assets_type_breakdown": assets_type_breakdown,
            "total_evidence": total_evidence,
            "evidence_status_breakdown": evidence_status_breakdown,
            "evidence_expiring_30d": evidence_expiring_30d,
            "total_vulnerabilities": total_vulnerabilities,
            "vulnerabilities_severity_breakdown": vuln_severity_breakdown,
            "vulnerabilities_status_breakdown": vulnerabilities_status_breakdown,
            "tasks_overdue": tasks_overdue,
            "tasks_due_7d": tasks_due_7d,
            "total_audits": total_audits,
            "audits_status_breakdown": audits_status_breakdown,
            "audits_avg_progress": audits_avg_progress,
            "projects_total": projects_total,
            "projects_status_breakdown": projects_status_breakdown,
            "projects_health_breakdown": projects_health_breakdown,
            "projects_priority_breakdown": projects_priority_breakdown,
            "projects_avg_progress": projects_avg_progress,
            "projects_total_budget": projects_total_budget,
            "projects_total_actual_cost": projects_total_actual_cost,
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
        return self.widgets.count()


class DashboardWidget(AbstractBaseModel, FolderMixin):
    # Each widget displays exactly one of: custom metric (metric_instance),
    # builtin metric (target_content_type + target_object_id + metric_key),
    # or text content (chart_type=TEXT + text_content). Enforced in clean().
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
        if self.title:
            return self.title
        if self.chart_type == self.ChartType.TEXT:
            return None
        if self.metric_instance:
            return self.metric_instance.name
        if self.metric_key:
            return self.metric_key.replace("_", " ").title()
        return _("Untitled Widget")

    @property
    def is_builtin_metric(self):
        return self.target_content_type is not None and self.metric_key is not None

    @property
    def is_custom_metric(self):
        return self.metric_instance is not None

    @property
    def is_text_widget(self):
        return self.chart_type == self.ChartType.TEXT

    def clean(self):
        if self.is_text_widget:
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
            return

        # custom metric and builtin metric are mutually exclusive; builtin
        # detection keys off target_content_type (id+key alone don't qualify).
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
    # Defaults to 730 days (2 years), minimum 1 day.
    try:
        settings = GlobalSettings.objects.get(name="general")
        retention = settings.value.get("builtin_metrics_retention_days", 730)
        return max(1, int(retention))
    except GlobalSettings.DoesNotExist, TypeError, ValueError:
        return 730
