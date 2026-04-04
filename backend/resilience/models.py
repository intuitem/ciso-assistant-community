from django.db import models, transaction
from django.db.models import (
    BooleanField,
    CharField,
    FloatField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    TextField,
    Count,
    Q,
    F,
)
from django.db.models.functions import Greatest, Least
from django.utils.functional import cached_property
from auditlog.registry import auditlog

from iam.models import FolderMixin
from core.models import (
    AppliedControl,
    Asset,
    Assessment,
    Evidence,
    RiskMatrix,
    AbstractBaseModel,
    Terminology,
)


class BusinessImpactAnalysis(Assessment):
    risk_matrix = models.ForeignKey(
        RiskMatrix,
        on_delete=models.PROTECT,
    )

    @cached_property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)
            return

        old_matrix_id = (
            BusinessImpactAnalysis.objects.filter(pk=self.pk)
            .values_list("risk_matrix_id", flat=True)
            .first()
        )

        matrix_changed = old_matrix_id != self.risk_matrix_id

        with transaction.atomic():
            super().save(*args, **kwargs)

            if matrix_changed:
                impacts = self.risk_matrix.impact
                min_impact = 0
                max_impact = len(impacts) - 1 if impacts else 0

                EscalationThreshold.objects.filter(
                    asset_assessment__bia=self,
                    quali_impact__gte=0,
                ).update(
                    quali_impact=Least(
                        Greatest(F("quali_impact"), min_impact),
                        max_impact,
                    )
                )

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
        max_index = len(risk_matrix["impact"]) - 1
        clamped = min(impact, max_index)
        if not risk_matrix["impact"][clamped].get("hexcolor"):
            risk_matrix["impact"][clamped]["hexcolor"] = "#f9fafb"
        return {
            **risk_matrix["impact"][clamped],
            "value": clamped,
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


class DoraIncidentReport(AbstractBaseModel, FolderMixin):
    """
    DORA (Digital Operational Resilience Act) Incident Report.

    Captures all regulatory data required by DORA IR schema v1.2.1
    for reporting major ICT incidents to competent authorities.
    Links to an existing Incident for shared lifecycle fields
    (occurred_at, resolved_at, resolution, is_bcp_activated).
    """

    class SubmissionType(models.TextChoices):
        INITIAL = "initial_notification", "Initial notification"
        INTERMEDIATE = "intermediate_report", "Intermediate report"
        FINAL = "final_report", "Final report"
        RECLASSIFIED = (
            "major_incident_reclassified_as_non-major",
            "Reclassified as non-major",
        )

    # -- Report metadata --
    incident = models.ForeignKey(
        "core.Incident",
        on_delete=models.CASCADE,
        related_name="dora_reports",
    )
    incident_submission = models.CharField(
        max_length=60,
        choices=SubmissionType.choices,
    )
    report_currency = models.CharField(max_length=3, blank=True)

    # -- Entity references (FK to tprm.Entity) --
    submitting_entity = models.ForeignKey(
        "tprm.Entity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dora_ir_submitting",
    )
    ultimate_parent_entity = models.ForeignKey(
        "tprm.Entity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dora_ir_parent",
    )
    affected_entities = models.ManyToManyField(
        "tprm.Entity",
        blank=True,
        related_name="dora_ir_affected",
    )

    # -- Contacts (plain fields, optionally filled from User in UI) --
    primary_contact_name = models.CharField(max_length=255, blank=True)
    primary_contact_email = models.EmailField(blank=True)
    primary_contact_phone = models.CharField(max_length=255, blank=True)
    secondary_contact_name = models.CharField(max_length=255, blank=True)
    secondary_contact_email = models.EmailField(blank=True)
    secondary_contact_phone = models.CharField(max_length=255, blank=True)

    # -- Incident details (scalar fields) --
    # NOTE: occurred_at, resolved_at, resolution, is_bcp_activated live on Incident (core)
    financial_entity_code = models.CharField(max_length=255, blank=True)
    detection_date_time = models.DateTimeField(null=True, blank=True)
    classification_date_time = models.DateTimeField(null=True, blank=True)
    incident_description = models.TextField(blank=True)
    other_information = models.TextField(blank=True)
    incident_duration = models.CharField(max_length=20, blank=True)  # HHH:MM:SS pattern
    originates_from_third_party_provider = models.TextField(blank=True)
    incident_discovery = models.CharField(max_length=60, blank=True)
    competent_authority_code = models.CharField(max_length=255, blank=True)

    # -- Classification types (polymorphic array) --
    classification_types = models.JSONField(default=list, blank=True)

    # -- Incident type (nested object) --
    incident_type = models.JSONField(default=dict, blank=True)

    # -- Root cause --
    root_cause_hl_classification = models.JSONField(default=list, blank=True)
    root_causes_detailed_classification = models.JSONField(default=list, blank=True)
    root_causes_additional_classification = models.JSONField(default=list, blank=True)
    root_causes_other = models.TextField(blank=True)
    root_causes_information = models.TextField(blank=True)
    root_cause_addressing_date_time = models.DateTimeField(null=True, blank=True)

    # -- Resolution (DORA-specific fields only; summary + datetime from Incident) --
    incident_resolution_vs_planned = models.TextField(blank=True)
    assessment_of_risk_to_critical_functions = models.TextField(blank=True)
    information_relevant_to_resolution_authorities = models.TextField(blank=True)

    # -- Financial --
    financial_recoveries_amount = models.DecimalField(
        max_digits=19, decimal_places=2, null=True, blank=True
    )
    gross_amount_indirect_direct_costs = models.DecimalField(
        max_digits=19, decimal_places=2, null=True, blank=True
    )

    # -- Recurring incident --
    recurring_non_major_incidents_description = models.TextField(blank=True)
    recurring_incident_date = models.DateTimeField(null=True, blank=True)

    # -- Impact assessment (nested structure) --
    impact_assessment = models.JSONField(default=dict, blank=True)

    # -- Reporting to authorities --
    reporting_to_other_authorities = models.JSONField(default=list, blank=True)
    reporting_to_other_authorities_other = models.TextField(blank=True)
    info_duration_service_downtime_actual_or_estimate = models.CharField(
        max_length=50, blank=True
    )

    fields_to_check = []

    class Meta:
        verbose_name = "DORA incident report"
        verbose_name_plural = "DORA incident reports"

    def __str__(self):
        return f"DORA IR ({self.get_incident_submission_display()}) — {self.incident}"

    def save(self, *args, **kwargs):
        if self.incident_id:
            self.folder = self.incident.folder
        super().save(*args, **kwargs)


common_exclude = ["created_at", "updated_at"]
auditlog.register(
    AssetAssessment,
    exclude_fields=common_exclude,
)
auditlog.register(
    BusinessImpactAnalysis,
    exclude_fields=common_exclude,
)
auditlog.register(
    EscalationThreshold,
    exclude_fields=common_exclude,
)
auditlog.register(
    DoraIncidentReport,
    exclude_fields=common_exclude,
)
