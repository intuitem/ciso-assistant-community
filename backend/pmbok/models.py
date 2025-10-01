from django.db import models
from iam.models import User, FolderMixin
from core.models import (
    FilteringLabelMixin,
    FindingsAssessment,
    I18nObjectMixin,
    Policy,
    ReferentialObjectMixin,
    ComplianceAssessment,
    RiskAssessment,
    Evidence,
    SecurityException,
)
from crq.models import QuantitativeRiskStudy
from ebios_rm.models import EbiosRMStudy
from tprm.models import EntityAssessment
from core.base_models import NameDescriptionMixin, AbstractBaseModel
from django.db.models import Count


class NameDescriptionFolderMixin(NameDescriptionMixin, FolderMixin):
    class Meta:
        abstract = True


class GenericCollection(NameDescriptionFolderMixin, FilteringLabelMixin):
    ref_id = models.CharField(max_length=100, blank=True)
    compliance_assessments = models.ManyToManyField(
        ComplianceAssessment,
        blank=True,
    )
    risk_assessments = models.ManyToManyField(
        RiskAssessment,
        blank=True,
    )
    crq_studies = models.ManyToManyField(
        QuantitativeRiskStudy,
        blank=True,
    )

    ebios_studies = models.ManyToManyField(
        EbiosRMStudy,
        blank=True,
    )
    entity_assessments = models.ManyToManyField(
        EntityAssessment,
        blank=True,
    )
    findings_assessments = models.ManyToManyField(
        FindingsAssessment,
        blank=True,
    )
    documents = models.ManyToManyField(
        Evidence,
        blank=True,
    )
    security_exceptions = models.ManyToManyField(
        SecurityException,
        blank=True,
    )

    policies = models.ManyToManyField(
        Policy,
        blank=True,
    )

    dependencies = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
    )


class Accreditation(NameDescriptionFolderMixin, FilteringLabelMixin):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("accredited", "Accredited"),
        ("not_accredited", "Not Accredited"),
        ("obsolete", "Obsolete"),
    )
    CATEGORY_CHOICES = (
        ("acc_simplified", "accSimplified"),
        ("acc_elaborated", "accElaborated"),
        ("acc_advanced", "accAdvanced"),
        ("acc_sensitive", "accSensitive"),
        ("acc_restricted", "accRestricted"),
        ("other", "Other"),
    )

    ref_id = models.CharField(max_length=100, blank=True)
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default="other"
    )
    authority = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="authored_accreditations",
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
    )
    linked_collection = models.ForeignKey(
        GenericCollection, null=True, on_delete=models.SET_NULL
    )
    checklist = models.ForeignKey(
        ComplianceAssessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accreditation_checklist",
    )
    observation = models.TextField(verbose_name="Observation", blank=True, null=True)
