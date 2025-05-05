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


class AssetAssessment(AbstractBaseModel, FolderMixin):
    asset = ForeignKey(Asset, on_delete=models.CASCADE)
    dependencies = ManyToManyField(Asset, related_name="dependencies", blank=True)
    associated_controls = ManyToManyField(AppliedControl, blank=True)

    bia = ForeignKey(BusinessImpactAnalysis, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return str(self.asset)


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
    quali_impact_level = IntegerField(default=-1)  # based on the matrix
    quanti_impact_number = FloatField(default=0)
    quanti_impact_unit = CharField(
        max_length=20, choices=QUANT_IMPACT_UNIT, default="currency"
    )
    rationale = TextField(null=True, blank=True)

    asset_assessment = ForeignKey(AssetAssessment, on_delete=models.CASCADE)
