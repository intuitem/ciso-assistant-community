from django.db import models
from core.models import (
    AppliedControl,
    Asset,
    Assessment,
    Evidence,
    RiskMatrix,
    AbstractBaseModel,
    Terminology,
)
from django.db.models import (
    BooleanField,
    CharField,
    FloatField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    TextField,
)
from iam.models import FolderMixin
from django.db.models import Count, Q
from django.utils.functional import cached_property


class BusinessImpactAnalysis(Assessment):
    risk_matrix = models.ForeignKey(
        RiskMatrix,
        on_delete=models.PROTECT,
    )

    @cached_property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()

    def metrics(self):
        qs = AssetAssessment.objects.filter(bia=self).aggregate(
            total=Count("id"),
            documented=Count("id", filter=Q(recovery_documented=True)),
            tested=Count("id", filter=Q(recovery_tested=True)),
            objectives=Count("id", filter=Q(recovery_targets_met=True)),
        )
        total_assets = qs["total"]
        documented_count = qs["documented"]
        tested_count = qs["tested"]
        objectives_met_count = qs["objectives"]

        doc_percentage = (
            round((documented_count / total_assets) * 100) if total_assets else 0
        )
        test_percentage = (
            round((tested_count / total_assets) * 100) if total_assets else 0
        )
        obj_percentage = (
            round((objectives_met_count / total_assets) * 100) if total_assets else 0
        )

        progress = {
            "progress": {
                "documentation": doc_percentage,
                "tests": test_percentage,
                "objectives": obj_percentage,
            }
        }

        return progress

    def build_table(self):
        table = list()
        xAxis = set()
        xAxis.add(0)
        asset_assessments = (
            AssetAssessment.objects.filter(bia=self)
            .prefetch_related(
                models.Prefetch(
                    "escalationthreshold_set",
                    queryset=EscalationThreshold.objects.order_by("point_in_time"),
                    to_attr="prefetched_thresholds",
                )
            )
            .order_by("asset__folder")
        )

        # First pass: collect all threshold points
        for aa in asset_assessments:
            thresholds = EscalationThreshold.objects.filter(
                asset_assessment=aa
            ).order_by("point_in_time")
            for th in thresholds:
                xAxis.add(th.point_in_time)

        # Sort the x-axis values for consistent timeline
        xAxis = sorted(xAxis)

        # Second pass: build the table with proper padding
        for aa in asset_assessments:
            thresholds = list(
                EscalationThreshold.objects.filter(asset_assessment=aa).order_by(
                    "point_in_time"
                )
            )

            data_dict = {}

            # Default for time 0 if no threshold exists
            if not thresholds or thresholds[0].point_in_time > 0:
                data_dict[0] = {"value": -1, "name": "--", "hexcolor": "#f9fafb"}

            # For each threshold, extend its impact to the next threshold
            for i, threshold in enumerate(thresholds):
                current_impact = threshold.get_impact_compact_display
                current_time = threshold.point_in_time

                # Find the next time point for this asset
                next_time = None
                if i < len(thresholds) - 1:
                    next_time = thresholds[i + 1].point_in_time

                # Apply the current impact to all points between current and next
                for point in xAxis:
                    if point == current_time or (
                        point > current_time
                        and (next_time is None or point < next_time)
                    ):
                        data_dict[point] = current_impact

            # Add entry to table
            table.append(
                {
                    "asset": aa.asset.name,
                    "folder": aa.asset.folder.name,
                    "data": data_dict,
                }
            )

        for entry in table:
            for point in xAxis:
                if point not in entry["data"]:
                    entry["data"][point] = {
                        "value": -1,
                        "name": "--",
                        "hexcolor": "#f9fafb",
                    }

        return table


class AssetAssessment(AbstractBaseModel, FolderMixin):
    asset = ForeignKey(Asset, on_delete=models.CASCADE)
    dependencies = ManyToManyField(Asset, related_name="dependencies", blank=True)
    associated_controls = ManyToManyField(AppliedControl, blank=True)
    recovery_documented = BooleanField(default=False)
    recovery_tested = BooleanField(default=False)
    recovery_targets_met = BooleanField(default=False)
    evidences = ManyToManyField(Evidence, blank=True)
    observation = TextField(null=True, blank=True)

    bia = ForeignKey(BusinessImpactAnalysis, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return str(self.asset)

    def metrics(self):
        thresholds = EscalationThreshold.objects.filter(asset_assessment=self).order_by(
            "point_in_time"
        )
        res = [
            {"pit": et.get_human_pit, "impact": et.get_impact_display}
            for et in thresholds
        ]
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
    qualifications = models.ManyToManyField(
        Terminology,
        verbose_name="Qualifications",
        related_name="escalation_thresholds_qualifications",
        limit_choices_to={
            "field_path": Terminology.FieldPath.QUALIFICATIONS,
            "is_visible": True,
        },
        blank=True,
    )
    quanti_impact = FloatField(default=0)
    quanti_impact_unit = CharField(
        max_length=20, choices=QUANT_IMPACT_UNIT, default="currency"
    )
    justification = TextField(null=True, blank=True)

    asset_assessment = ForeignKey(AssetAssessment, on_delete=models.CASCADE)

    class Meta:
        unique_together = ["asset_assessment", "point_in_time"]

    def __str__(self):
        return f"Downtime on {self.asset_assessment.asset}"

    @property
    def risk_matrix(self):
        return self.asset_assessment.bia.risk_matrix

    @cached_property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()

    @property
    def get_human_pit(self):
        seconds = self.point_in_time
        days, seconds = divmod(seconds, 86400)  # 24 * 3600
        hours, seconds = divmod(seconds, 3600)
        minutes, _ = divmod(seconds, 60)

        return {"day": days, "hour": hours, "minute": minutes}

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

    @property
    def get_impact_compact_display(self):
        raw = self.get_impact_display
        return {
            "value": raw["value"],
            "name": raw["name"],
            "description": raw["description"],
            "hexcolor": raw["hexcolor"],
        }
