from collections import Counter

from auditlog.registry import auditlog
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
        default=10, verbose_name=_("History depth")
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

    def current_posture(self, asset_id=None) -> list[dict]:
        qs = self.results
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
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
                "actual",
                "expected",
                "message",
                "requirement__ref_id",
                "requirement__name",
                "asset__name",
            )
        )

    def get_score(self) -> float | None:
        counts = Counter(row["result"] for row in self.current_posture())
        applicable = counts["pass"] + counts["fail"]
        if not applicable:
            return None
        return round(100 * counts["pass"] / applicable, 1)

    def prune_history(self, pairs):
        stale = []
        for asset_id, requirement_id in pairs:
            pks = (
                self.results.filter(asset_id=asset_id, requirement_id=requirement_id)
                .order_by("-timestamp", "-created_at")
                .values_list("pk", flat=True)
            )
            stale.extend(pks[self.history_depth :])
        if stale:
            self.results.filter(pk__in=stale).delete()


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

    posture_assessment = models.ForeignKey(
        PostureAssessment, on_delete=models.CASCADE, related_name="results"
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
    run_id = models.UUIDField()
    actual = models.CharField(max_length=255, blank=True)
    expected = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    tool = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.API)
    imported_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = _("Posture result")
        verbose_name_plural = _("Posture results")
        indexes = [
            models.Index(fields=["posture_assessment", "run_id"]),
            models.Index(
                fields=["posture_assessment", "asset", "requirement", "timestamp"]
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["run_id", "asset", "requirement"],
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
