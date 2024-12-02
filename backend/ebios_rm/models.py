from django.db import models
from django.utils.translation import gettext_lazy as _
from core.base_models import AbstractBaseModel, NameDescriptionMixin, ETADueDateMixin
from core.models import Asset, ComplianceAssessment, RiskAssessment, RiskMatrix
from iam.models import FolderMixin, User


class EbiosRMStudy(NameDescriptionMixin, ETADueDateMixin, FolderMixin):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        IN_PROGRESS = "in_progress", _("In progress")
        IN_REVIEW = "in_review", _("In review")
        DONE = "done", _("Done")
        DEPRECATED = "deprecated", _("Deprecated")

    risk_matrix = models.ForeignKey(
        RiskMatrix,
        on_delete=models.PROTECT,
        verbose_name=_("Risk matrix"),
        related_name="ebios_rm_studies",
        help_text=_(
            "Risk matrix used as a reference for the study. Defaults to `urn:intuitem:risk:library:risk-matrix-4x4-ebios-rm`"
        ),
    )
    assets = models.ManyToManyField(
        Asset,
        verbose_name=_("Assets"),
        related_name="ebios_rm_studies",
        help_text=_("Assets that are pertinent to the study"),
    )
    compliance_assessments = models.ManyToManyField(
        ComplianceAssessment,
        verbose_name=_("Compliance assessments"),
        related_name="ebios_rm_studies",
        help_text=_(
            "Compliance assessments established as security baseline during workshop 1.4"
        ),
    )
    risk_assessments = models.ManyToManyField(
        RiskAssessment,
        verbose_name=_("Risk assessments"),
        related_name="ebios_rm_studies",
        help_text=_("Risk assessments generated at the end of workshop 4"),
    )

    ref_id = models.CharField(max_length=100)
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Version of the Ebios RM study (eg. 1.0, 2.0, etc.)"),
        verbose_name=_("Version"),
        default="1.0",
    )
    status = models.CharField(
        max_length=100,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name=_("Status"),
        blank=True,
        null=True,
    )
    authors = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Authors"),
        related_name="authors",
    )
    reviewers = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Reviewers"),
        related_name="reviewers",
    )
    observation = models.TextField(null=True, blank=True, verbose_name=_("Observation"))

    class Meta:
        verbose_name = _("Ebios RM Study")
        verbose_name_plural = _("Ebios RM Studies")
        ordering = ["created_at"]


class ROTO(AbstractBaseModel):
    class RiskOrigin(models.TextChoices):
        STATE = "state", _("State")
        ORGANIZED_CRIME = "organized_crime", _("Organized crime")
        TERRORIST = "terrorist", _("Terrorist")
        ACTIVIST = "activist", _("Activist")
        PROFESSIONAL = "professional", _("Professional")
        AMATEUR = "amateur", _("Amateur")
        AVENGER = "avenger", _("Avenger")
        PATHOLOGICAL = "pathological", _("Pathological")

    study = models.ForeignKey(
        EbiosRMStudy, verbose_name=_("EBIOS RM study"), on_delete=models.CASCADE
    )
    risk_origin = models.CharField(max_length=200, verbose_name=_("Risk origin"))
    target_objective = models.CharField(
        max_length=200, verbose_name=_("Target objective")
    )
    motivation = models.PositiveSmallIntegerField(verbose_name=_("Motivation"))
    resources = models.PositiveSmallIntegerField(verbose_name=_("Resources"))
    pertinence = models.PositiveSmallIntegerField(verbose_name=_("Pertinence"))
    activity = models.PositiveSmallIntegerField(verbose_name=_("Activity"))
    is_selected = models.BooleanField(verbose_name=_("Is selected"))
    justification = models.TextField(verbose_name=_("Justification"))

    class Meta:
        verbose_name = _("RO/TO couple")
        verbose_name_plural = _("RO/TO couples")
        ordering = ["created_at"]
