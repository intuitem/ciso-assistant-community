from django.db import models
from core.models import AppliedControl, Asset, Assessment, RiskMatrix, AbstractBaseModel
from django.db.models import (
    CharField,
    FloatField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    OneToOneField,
    TextField,
)

from iam.models import User, FolderMixin


class BusinessImpactAnalysis(Assessment):
    risk_matrix = models.ForeignKey(
        RiskMatrix,
        on_delete=models.PROTECT,
    )

    @property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()


class AssetAssessment(AbstractBaseModel, FolderMixin):
    asset = ForeignKey(Asset, on_delete=models.CASCADE)
    dependencies = ManyToManyField(Asset, related_name="dependencies", blank=True)
    associated_controls = ManyToManyField(AppliedControl, blank=True)

    bia = ForeignKey(BusinessImpactAnalysis, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return str(self.asset)

    def metrics(self):
        thresholds = EscalationThreshold.objects.filter(asset_assessment=self)
        res = [
            {"pit": et.get_human_pit, "impact": et.get_impact_display}
            for et in thresholds
        ]
        xAxis = []
        yAxis = []
        for et in thresholds:
            xAxis.append(et.get_human_pit)
            yAxis.append(
                {
                    "value": int(et.get_impact_display.get("value")) + 1,
                    "itemStyle": {"color": et.get_impact_display.get("hexcolor")},
                }
            )
        return res

    class Meta:
        unique_together = ["bia", "asset"]


class EscalationThreshold(AbstractBaseModel, FolderMixin):
    QUANT_IMPACT_UNIT = (
        ("people", "People"),
        ("currency", "Currency"),
        ("records", "Records"),
        ("man_hours", "Man-hours"),
        ("data_gb", "Data (GB)"),
        ("gu", "Generic Unit"),
    )
    point_in_time = IntegerField()  # seconds and manage the display and units on front
    quali_impact = IntegerField(default=-1)  # based on the matrix
    quanti_impact = FloatField(default=0)
    quanti_impact_unit = CharField(
        max_length=20, choices=QUANT_IMPACT_UNIT, default="currency"
    )
    justification = TextField(null=True, blank=True)

    asset_assessment = ForeignKey(AssetAssessment, on_delete=models.CASCADE)

    class Meta:
        unique_together = ["asset_assessment", "point_in_time"]

    @property
    def risk_matrix(self):
        return self.asset_assessment.bia.risk_matrix

    @property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()

    @property
    def get_human_pit(self):
        seconds = self.point_in_time
        days, seconds = divmod(seconds, 86400)  # 24 * 3600
        hours, seconds = divmod(seconds, 3600)
        minutes, _ = divmod(seconds, 60)

        parts = []
        if days:
            parts.append(f"{days} {'Day' if days == 1 else 'Days'}")
        if hours:
            parts.append(f"{hours} {'Hour' if hours == 1 else 'Hours'}")
        if minutes:
            parts.append(f"{minutes} {'Minute' if minutes == 1 else 'Minutes'}")

        return ", ".join(parts) or "0 Minutes"

    @staticmethod
    def format_impact(impact: int, parsed_matrix: dict):
        if impact < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
                "hexcolor": "#f9fafb",
            }
        risk_matrix = parsed_matrix
        if not risk_matrix["impact"][impact].get("hexcolor"):
            risk_matrix["impact"][impact]["hexcolor"] = "#f9fafb"
        return {
            **risk_matrix["impact"][impact],
            "value": impact,
        }

    @property
    def get_impact_display(self):
        return self.format_impact(self.quali_impact, self.parsed_matrix)
