from collections import Counter

from auditlog.registry import auditlog
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel
from core.models import (
    Assessment,
    Asset,
    FindingsAssessment,
    Framework,
    RequirementNode,
)
from iam.models import User


class PostureAssessment(Assessment):
    framework = models.ForeignKey(
        Framework, on_delete=models.CASCADE, verbose_name=_("Framework")
    )
    selected_implementation_groups = models.JSONField(
        blank=True, null=True, verbose_name=_("Selected implementation groups")
    )
    assets = models.ManyToManyField(
        Asset,
        blank=True,
        verbose_name=_("Assets"),
        related_name="posture_assessments",
    )
    history_depth = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        verbose_name=_("History depth"),
    )
    follow_up_assessment = models.ForeignKey(
        FindingsAssessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posture_assessments",
        verbose_name=_("Follow-up assessment"),
    )
    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("reference id")
    )

    class Meta:
        verbose_name = _("Posture assessment")
        verbose_name_plural = _("Posture assessments")

    def requirement_matches_selected_groups(self, implementation_groups) -> bool:
        selected = self.selected_implementation_groups
        if not selected:
            return True
        if not implementation_groups:
            return False
        return bool(set(selected) & set(implementation_groups))

    def selected_requirement_ids(self) -> set | None:
        if not self.selected_implementation_groups:
            return None
        return {
            node["id"]
            for node in RequirementNode.objects.filter(
                framework=self.framework, assessable=True
            ).values("id", "implementation_groups")
            if self.requirement_matches_selected_groups(node["implementation_groups"])
        }

    @property
    def results(self):
        return PostureResult.objects.filter(run__posture_assessment=self)

    def current_posture(self, asset_id=None, asset_ids=None) -> list[dict]:
        qs = self.results
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        if asset_ids is not None:
            qs = qs.filter(asset_id__in=asset_ids)
        selected_ids = self.selected_requirement_ids()
        if selected_ids is not None:
            qs = qs.filter(requirement_id__in=selected_ids)
        return list(
            qs.annotate(
                rn=Window(
                    expression=RowNumber(),
                    partition_by=[F("asset_id"), F("requirement_id")],
                    order_by=[F("timestamp").desc(), F("created_at").desc()],
                )
            )
            .filter(rn=1)
            .values(
                "id",
                "requirement_id",
                "asset_id",
                "result",
                "timestamp",
                "run_id",
                "run__tool",
                "source",
                "actual",
                "expected",
                "message",
                "requirement__ref_id",
                "requirement__name",
                "asset__name",
                "asset__folder__name",
            )
        )

    def get_score(self) -> float | None:
        counts = Counter(row["result"] for row in self.current_posture())
        applicable = counts["pass"] + counts["fail"]
        if not applicable:
            return None
        return round(100 * counts["pass"] / applicable, 1)

    def prune_history(self, pairs):
        if not pairs:
            return
        stale = list(
            self.results.filter(
                asset_id__in={a for a, _ in pairs},
                requirement_id__in={r for _, r in pairs},
            )
            .annotate(
                rn=Window(
                    expression=RowNumber(),
                    partition_by=[F("asset_id"), F("requirement_id")],
                    order_by=[F("timestamp").desc(), F("created_at").desc()],
                )
            )
            .filter(rn__gt=self.history_depth)
            .values_list("pk", flat=True)
        )
        if stale:
            self.results.filter(pk__in=stale).delete()
            self.runs.filter(results__isnull=True).delete()


class PostureRun(AbstractBaseModel):
    posture_assessment = models.ForeignKey(
        PostureAssessment, on_delete=models.CASCADE, related_name="runs"
    )
    started_at = models.DateTimeField()
    tool = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = _("Posture run")
        verbose_name_plural = _("Posture runs")
        indexes = [models.Index(fields=["posture_assessment", "started_at"])]

    def __str__(self):
        return f"{self.tool or 'run'} @ {self.started_at:%Y-%m-%d %H:%M}"


class PostureResult(AbstractBaseModel):
    class Result(models.TextChoices):
        PASSED = "pass", _("Pass")
        FAILED = "fail", _("Fail")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")
        ERROR = "error", _("Error")
        NOT_CHECKED = "not_checked", _("Not checked")

    class Source(models.TextChoices):
        MANUAL = "manual", _("Manual")
        API = "api", _("API")
        IMPORT = "import", _("Import")

    run = models.ForeignKey(
        PostureRun, on_delete=models.CASCADE, related_name="results"
    )
    requirement = models.ForeignKey(
        RequirementNode, on_delete=models.CASCADE, related_name="posture_results"
    )
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name="posture_results"
    )
    result = models.CharField(
        max_length=20, choices=Result.choices, default=Result.NOT_CHECKED
    )
    timestamp = models.DateTimeField()
    actual = models.CharField(max_length=255, blank=True)
    expected = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.API)
    imported_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("Posture result")
        verbose_name_plural = _("Posture results")
        indexes = [
            models.Index(fields=["asset", "requirement", "timestamp"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "asset", "requirement"],
                name="unique_posture_result_per_run",
            ),
        ]

    def __str__(self):
        return f"{self.requirement.ref_id or self.requirement.urn} on {self.asset}: {self.result}"


common_exclude = ["created_at", "updated_at"]
auditlog.register(
    PostureAssessment,
    m2m_fields={"authors", "assets"},
    exclude_fields=common_exclude,
)
