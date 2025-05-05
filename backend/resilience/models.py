from django.db import models
from core.models import AppliedControl, Asset, Assessment, RiskMatrix, AbstractBaseModel
from django.db.models import (
    CharField,
    FloatField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    OneToOneField,
)


class BusinessImpactAnalysis(Assessment):
    risk_matrix = models.ForeignKey(
        RiskMatrix,
        on_delete=models.PROTECT,
    )


class AssetAssessment(AbstractBaseModel):
    asset = OneToOneField(Asset, on_delete=models.CASCADE)
    dependencies = ManyToManyField(Asset, related_name="dependencies")
    associated_controls = ManyToManyField(AppliedControl)

    bia = ForeignKey(BusinessImpactAnalysis, on_delete=models.CASCADE)


class EscalationThreshold(AbstractBaseModel):
    TIME_UNIT_CHOICES = (("m", "Minutes"), ("H", "Hours"), ("d", "Days"))
    QUANT_IMPACT_UNIT = (
        ("people", "People"),
        ("currency", "Currency"),
        ("records", "Records"),
        ("man_hours", "Man-hours"),
        ("generic", "Generic"),
    )
    point_in_time = IntegerField(default=0)
    time_unit = CharField(max_length=2, choices=TIME_UNIT_CHOICES, default="H")
    quali_impact_level = IntegerField(default=-1)  # based on the matrix
    quanti_impact_number = FloatField(default=0)
    quanti_impact_unit = CharField(
        max_length=20, choices=QUANT_IMPACT_UNIT, default="currency"
    )
    rationale = CharField(max_length=250)

    asset_assessment = ForeignKey(AssetAssessment, on_delete=models.CASCADE)
