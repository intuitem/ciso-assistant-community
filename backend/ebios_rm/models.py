from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.base_models import AbstractBaseModel, NameDescriptionMixin, ETADueDateMixin
from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Qualification,
    RiskMatrix,
    Threat,
)
from iam.models import FolderMixin, User
from tprm.models import Entity


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
        blank=True,
    )
    assets = models.ManyToManyField(
        Asset,
        verbose_name=_("Assets"),
        related_name="ebios_rm_studies",
        help_text=_("Assets that are pertinent to the study"),
        blank=True,
    )
    compliance_assessments = models.ManyToManyField(
        ComplianceAssessment,
        blank=True,
        verbose_name=_("Compliance assessments"),
        related_name="ebios_rm_studies",
        help_text=_(
            "Compliance assessments established as security baseline during workshop 1.4"
        ),
    )
    reference_entity = models.ForeignKey(
        Entity,
        on_delete=models.PROTECT,
        verbose_name=_("Reference entity"),
        related_name="ebios_rm_studies",
        help_text=_("Entity that is the focus of the study"),
        default=Entity.get_main_entity,
    )

    ref_id = models.CharField(max_length=100, blank=True)
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

    @property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()


class FearedEvent(NameDescriptionMixin, FolderMixin):
    ebios_rm_study = models.ForeignKey(
        EbiosRMStudy,
        verbose_name=_("EBIOS RM study"),
        on_delete=models.CASCADE,
    )
    assets = models.ManyToManyField(
        Asset,
        blank=True,
        verbose_name=_("Assets"),
        related_name="feared_events",
        help_text=_("Assets that are affected by the feared event"),
    )
    qualifications = models.ManyToManyField(
        Qualification,
        blank=True,
        verbose_name=_("Qualifications"),
        related_name="feared_events",
        help_text=_("Qualifications carried by the feared event"),
    )

    ref_id = models.CharField(max_length=100, blank=True)
    gravity = models.SmallIntegerField(default=-1, verbose_name=_("Gravity"))
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    class Meta:
        verbose_name = _("Feared event")
        verbose_name_plural = _("Feared events")
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.ebios_rm_study.folder
        super().save(*args, **kwargs)

    @property
    def risk_matrix(self):
        return self.ebios_rm_study.risk_matrix

    @property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()

    def get_gravity_display(self):
        if self.gravity < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
            }
        risk_matrix = self.parsed_matrix
        return {
            **risk_matrix["impact"][self.gravity],
            "value": self.gravity,
        }


class RoTo(AbstractBaseModel, FolderMixin):
    class RiskOrigin(models.TextChoices):
        STATE = "state", _("State")
        ORGANIZED_CRIME = "organized_crime", _("Organized crime")
        TERRORIST = "terrorist", _("Terrorist")
        ACTIVIST = "activist", _("Activist")
        PROFESSIONAL = "professional", _("Professional")
        AMATEUR = "amateur", _("Amateur")
        AVENGER = "avenger", _("Avenger")
        PATHOLOGICAL = "pathological", _("Pathological")

    class Motivation(models.IntegerChoices):
        UNDEFINED = 0, "undefined"
        VERY_LOW = 1, "very_low"
        LOW = 2, "low"
        SIGNIFICANT = 3, "significant"
        STRONG = 4, "strong"

    class Resources(models.IntegerChoices):
        UNDEFINED = 0, "undefined"
        LIMITED = 1, "limited"
        SIGNIFICANT = 2, "significant"
        IMPORTANT = 3, "important"
        UNLIMITED = 4, "unlimited"

    class Pertinence(models.IntegerChoices):
        UNDEFINED = 0, "undefined"
        IRRELAVANT = 1, "irrelevant"
        PARTIALLY_RELEVANT = 2, "partially_relevant"
        FAIRLY_RELEVANT = 3, "fairly_relevant"
        HIGHLY_RELEVANT = 4, "highly_relevant"

    ebios_rm_study = models.ForeignKey(
        EbiosRMStudy,
        verbose_name=_("EBIOS RM study"),
        on_delete=models.CASCADE,
    )
    feared_events = models.ManyToManyField(
        FearedEvent, verbose_name=_("Feared events"), related_name="ro_to_couples"
    )

    risk_origin = models.CharField(
        max_length=32, verbose_name=_("Risk origin"), choices=RiskOrigin.choices
    )
    target_objective = models.TextField(verbose_name=_("Target objective"))
    motivation = models.PositiveSmallIntegerField(
        verbose_name=_("Motivation"),
        choices=Motivation.choices,
        default=Motivation.UNDEFINED,
    )
    resources = models.PositiveSmallIntegerField(
        verbose_name=_("Resources"),
        choices=Resources.choices,
        default=Resources.UNDEFINED,
    )
    pertinence = models.PositiveSmallIntegerField(
        verbose_name=_("Pertinence"),
        choices=Pertinence.choices,
        default=Pertinence.UNDEFINED,
    )
    activity = models.PositiveSmallIntegerField(
        verbose_name=_("Activity"), default=0, validators=[MaxValueValidator(4)]
    )
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    def __str__(self) -> str:
        return f"{self.get_risk_origin_display()} - {self.target_objective}"

    class Meta:
        verbose_name = _("RO/TO couple")
        verbose_name_plural = _("RO/TO couples")
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.ebios_rm_study.folder
        super().save(*args, **kwargs)


class Stakeholder(AbstractBaseModel, FolderMixin):
    class Category(models.TextChoices):
        CLIENT = "client", _("Client")
        PARTNER = "partner", _("Partner")
        SUPPLIER = "supplier", _("Supplier")

    ebios_rm_study = models.ForeignKey(
        EbiosRMStudy,
        verbose_name=_("EBIOS RM study"),
        help_text=_("EBIOS RM study that the stakeholder is part of"),
        related_name="stakeholders",
        on_delete=models.CASCADE,
    )
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        verbose_name=_("Entity"),
        related_name="stakeholders",
        help_text=_("Entity qualified by the stakeholder"),
    )
    applied_controls = models.ManyToManyField(
        AppliedControl,
        verbose_name=_("Applied controls"),
        blank=True,
        related_name="stakeholders",
        help_text=_("Controls applied to lower stakeholder criticality"),
    )

    category = models.CharField(
        max_length=32, verbose_name=_("Category"), choices=Category.choices
    )

    current_dependency = models.PositiveSmallIntegerField(
        verbose_name=_("Current dependency"),
        default=0,
        validators=[MaxValueValidator(4)],
    )
    current_penetration = models.PositiveSmallIntegerField(
        verbose_name=_("Current penetration"),
        default=0,
        validators=[MaxValueValidator(4)],
    )
    current_maturity = models.PositiveSmallIntegerField(
        verbose_name=_("Current maturity"),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
    )
    current_trust = models.PositiveSmallIntegerField(
        verbose_name=_("Current trust"),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
    )

    residual_dependency = models.PositiveSmallIntegerField(
        verbose_name=_("Residual dependency"),
        default=0,
        validators=[MaxValueValidator(4)],
    )
    residual_penetration = models.PositiveSmallIntegerField(
        verbose_name=_("Residual penetration"),
        default=0,
        validators=[MaxValueValidator(4)],
    )
    residual_maturity = models.PositiveSmallIntegerField(
        verbose_name=_("Residual maturity"),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
    )
    residual_trust = models.PositiveSmallIntegerField(
        verbose_name=_("Residual trust"),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
    )

    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    class Meta:
        verbose_name = _("Stakeholder")
        verbose_name_plural = _("Stakeholders")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.entity.name} - {self.get_category_display()}"

    def save(self, *args, **kwargs):
        self.folder = self.ebios_rm_study.folder
        super().save(*args, **kwargs)

    @staticmethod
    def _compute_criticality(
        dependency: int, penetration: int, maturity: int, trust: int
    ):
        if (maturity * trust) == 0:
            return 0
        return (dependency * penetration) / (maturity * trust)

    @property
    def current_criticality(self):
        return self._compute_criticality(
            self.current_dependency,
            self.current_penetration,
            self.current_maturity,
            self.current_trust,
        )

    @property
    def residual_criticality(self):
        return self._compute_criticality(
            self.residual_dependency,
            self.residual_penetration,
            self.residual_maturity,
            self.residual_trust,
        )


class AttackPath(AbstractBaseModel, FolderMixin):
    ebios_rm_study = models.ForeignKey(
        EbiosRMStudy,
        verbose_name=_("EBIOS RM study"),
        on_delete=models.CASCADE,
    )
    ro_to_couple = models.ForeignKey(
        RoTo,
        verbose_name=_("RO/TO couple"),
        on_delete=models.CASCADE,
        help_text=_("RO/TO couple from which the attach path is derived"),
    )
    stakeholders = models.ManyToManyField(
        Stakeholder,
        verbose_name=_("Stakeholders"),
        related_name="attack_paths",
        help_text=_("Stakeholders leveraged by the attack path"),
    )

    description = models.TextField(verbose_name=_("Description"))
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    class Meta:
        verbose_name = _("Attack path")
        verbose_name_plural = _("Attack paths")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.ro_to_couple} - {self.description}"

    def save(self, *args, **kwargs):
        self.folder = self.ebios_rm_study.folder
        super().save(*args, **kwargs)


class OperationalScenario(AbstractBaseModel, FolderMixin):
    ebios_rm_study = models.ForeignKey(
        EbiosRMStudy,
        verbose_name=_("EBIOS RM study"),
        related_name="operational_scenarios",
        on_delete=models.CASCADE,
    )
    attack_paths = models.ManyToManyField(
        AttackPath,
        verbose_name=_("Attack paths"),
        related_name="operational_scenarios",
        help_text=_("Attack paths that are pertinent to the operational scenario"),
    )
    threats = models.ManyToManyField(
        Threat,
        verbose_name=_("Threats"),
        blank=True,
        related_name="operational_scenarios",
        help_text=_("Threats leveraged by the operational scenario"),
    )

    description = models.TextField(verbose_name=_("Description"))
    likelihood = models.SmallIntegerField(default=-1, verbose_name=_("Likelihood"))
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    class Meta:
        verbose_name = _("Operational scenario")
        verbose_name_plural = _("Operational scenarios")
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.ebios_rm_study.folder
        super().save(*args, **kwargs)

    @property
    def risk_matrix(self):
        return self.ebios_rm_study.risk_matrix

    @property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()

    def get_likelihood_display(self):
        if self.likelihood < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
            }
        risk_matrix = self.parsed_matrix
        return {
            **risk_matrix["probability"][self.likelihood],
            "value": self.likelihood,
        }
