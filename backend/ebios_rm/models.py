from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel, ETADueDateMixin, NameDescriptionMixin
from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Qualification,
    RiskMatrix,
    Threat,
    RiskAssessment,
)
from core.validators import (
    JSONSchemaInstanceValidator,
)
from iam.models import FolderMixin, User
from tprm.models import Entity

INITIAL_META = {
    "workshops": [
        {
            "steps": [
                {"status": "to_do"},
                {"status": "to_do"},
                {"status": "to_do"},
                {"status": "to_do"},
            ]
        },
        {"steps": [{"status": "to_do"}, {"status": "to_do"}, {"status": "to_do"}]},
        {"steps": [{"status": "to_do"}, {"status": "to_do"}, {"status": "to_do"}]},
        {"steps": [{"status": "to_do"}, {"status": "to_do"}]},
        {
            "steps": [
                {"status": "to_do"},
                {"status": "to_do"},
                {"status": "to_do"},
                {"status": "to_do"},
                {"status": "to_do"},
            ]
        },
    ]
}


def get_initial_meta():
    return INITIAL_META


class EbiosRMStudy(NameDescriptionMixin, ETADueDateMixin, FolderMixin):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        IN_PROGRESS = "in_progress", _("In progress")
        IN_REVIEW = "in_review", _("In review")
        DONE = "done", _("Done")
        DEPRECATED = "deprecated", _("Deprecated")

    META_JSONSCHEMA = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://ciso-assistant.com/schemas/ebiosrmstudy/meta.schema.json",
        "title": "Metadata",
        "description": "Metadata of the EBIOS RM Study",
        "type": "object",
        "properties": {
            "workshops": {
                "type": "array",
                "description": "A list of workshops, each containing steps",
                "items": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "description": "The list of steps in the workshop",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "status": {
                                        "type": "string",
                                        "description": "The current status of the step",
                                        "enum": ["to_do", "in_progress", "done"],
                                    },
                                },
                                "required": ["status"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["steps"],
                    "additionalProperties": False,
                },
            }
        },
    }

    risk_matrix = models.ForeignKey(
        RiskMatrix,
        on_delete=models.PROTECT,
        verbose_name=_("Risk matrix"),
        related_name="ebios_rm_studies",
        help_text=_("Risk matrix used as a reference for the study"),
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
    meta = models.JSONField(
        default=get_initial_meta,
        verbose_name=_("Metadata"),
        validators=[JSONSchemaInstanceValidator(META_JSONSCHEMA)],
    )

    fields_to_check = ["name", "version"]

    class Meta:
        verbose_name = _("Ebios RM Study")
        verbose_name_plural = _("Ebios RM Studies")
        ordering = ["created_at"]

    @property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()

    @property
    def roto_count(self):
        return self.roto_set.count()

    @property
    def selected_roto_count(self):
        return self.roto_set.filter(is_selected=True).count()

    @property
    def selected_attack_path_count(self):
        return self.attackpath_set.filter(is_selected=True).count()

    @property
    def operational_scenario_count(self):
        return self.operational_scenarios.count()

    @property
    def applied_control_count(self):
        return AppliedControl.objects.filter(stakeholders__ebios_rm_study=self).count()

    @property
    def last_risk_assessment(self):
        """Get the latest risk assessment for the study
        Returns:
            RiskAssessment: The latest risk assessment for the study
        """
        try:
            return RiskAssessment.objects.filter(ebios_rm_study=self).latest(
                "created_at"
            )
        except RiskAssessment.DoesNotExist:
            return None

    def update_workshop_step_status(self, workshop: int, step: int, new_status: str):
        if workshop < 1 or workshop > 5:
            raise ValueError("Workshop must be between 1 and 5")
        if step < 1 or step > len(self.meta["workshops"][workshop - 1]["steps"]):
            raise ValueError(
                f"Worshop {workshop} has only {len(self.meta['workshops'][workshop - 1]['steps'])} steps"
            )
        status = new_status
        self.meta["workshops"][workshop - 1]["steps"][step - 1]["status"] = status
        return self.save()


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

    fields_to_check = ["name", "ref_id"]

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

    @staticmethod
    def format_gravity(gravity: int, parsed_matrix: dict):
        if gravity < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
                "hexcolor": "#f9fafb",
            }
        risk_matrix = parsed_matrix
        if not risk_matrix["impact"][gravity].get("hexcolor"):
            risk_matrix["impact"][gravity]["hexcolor"] = "#f9fafb"
        return {
            **risk_matrix["impact"][gravity],
            "value": gravity,
        }

    def get_gravity_display(self):
        return FearedEvent.format_gravity(self.gravity, self.parsed_matrix)


class RoTo(AbstractBaseModel, FolderMixin):
    class RiskOrigin(models.TextChoices):
        STATE = "state", _("State")
        ORGANIZED_CRIME = "organized_crime", _("Organized crime")
        TERRORIST = "terrorist", _("Terrorist")
        ACTIVIST = "activist", _("Activist")
        COMPETITOR = "competitor", _("Competitor")
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

    class Activity(models.IntegerChoices):
        UNDEFINED = 0, "undefined"
        VERY_LOW = 1, "very_low"
        LOW = 2, "low"
        MODERATE = 3, "moderate"
        IMPORTANT = 4, "important"

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
        FearedEvent,
        verbose_name=_("Feared events"),
        related_name="ro_to_couples",
        blank=True,
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
    activity = models.PositiveSmallIntegerField(
        verbose_name=_("Activity"),
        choices=Activity.choices,
        default=Activity.UNDEFINED,
        validators=[MaxValueValidator(4)],
    )
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    fields_to_check = ["target_objective", "risk_origin"]

    def __str__(self) -> str:
        return f"{self.get_risk_origin_display()} - {self.target_objective}"

    class Meta:
        verbose_name = _("RO/TO couple")
        verbose_name_plural = _("RO/TO couples")
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.ebios_rm_study.folder
        super().save(*args, **kwargs)

    @property
    def get_pertinence(self):
        PERTINENCE_MATRIX = [
            [1, 1, 2, 2],
            [1, 2, 3, 3],
            [2, 3, 3, 4],
            [2, 3, 4, 4],
        ]
        if self.motivation == 0 or self.resources == 0:
            return self.Pertinence(self.Pertinence.UNDEFINED).label
        return self.Pertinence(
            PERTINENCE_MATRIX[self.motivation - 1][self.resources - 1]
        ).label

    def get_gravity(self):
        gravity = -1
        for feared_event in self.feared_events.all():
            if feared_event.gravity > gravity and feared_event.is_selected:
                gravity = feared_event.gravity
        return gravity


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

    fields_to_check = ["entity", "category"]

    class Meta:
        verbose_name = _("Stakeholder")
        verbose_name_plural = _("Stakeholders")
        ordering = ["created_at"]

    def get_scope(self):
        return self.__class__.objects.filter(ebios_rm_study=self.ebios_rm_study)

    def __str__(self):
        return f"{self.entity.name}-{self.get_category_display()}"

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

    def get_current_criticality_display(self) -> str:
        return (
            f"{self.current_criticality:.2f}".rstrip("0").rstrip(".")
            if "." in f"{self.current_criticality:.2f}"
            else f"{self.current_criticality:.2f}"
        )

    def get_residual_criticality_display(self) -> str:
        return (
            f"{self.residual_criticality:.2f}".rstrip("0").rstrip(".")
            if "." in f"{self.residual_criticality:.2f}"
            else f"{self.residual_criticality:.2f}"
        )


class StrategicScenario(NameDescriptionMixin, FolderMixin):
    ebios_rm_study = models.ForeignKey(
        EbiosRMStudy,
        verbose_name=_("EBIOS RM study"),
        related_name="strategic_scenarios",
        on_delete=models.CASCADE,
    )
    ro_to_couple = models.ForeignKey(
        RoTo,
        verbose_name=_("RO/TO couple"),
        on_delete=models.CASCADE,
        help_text=_("RO/TO couple from which the attach path is derived"),
    )
    ref_id = models.CharField(max_length=100, blank=True)

    fields_to_check = ["name", "ref_id"]

    class Meta:
        verbose_name = _("Strategic Scenario")
        verbose_name_plural = _("Strategic Scenarios")
        ordering = ["created_at"]

    def get_scope(self):
        return self.__class__.objects.filter(ebios_rm_study=self.ebios_rm_study)

    def save(self, *args, **kwargs):
        self.folder = self.ebios_rm_study.folder
        super().save(*args, **kwargs)

    def get_gravity_display(self):
        return FearedEvent.format_gravity(
            self.ro_to_couple.get_gravity(), self.ebios_rm_study.parsed_matrix
        )


class AttackPath(NameDescriptionMixin, FolderMixin):
    ebios_rm_study = models.ForeignKey(
        EbiosRMStudy,
        verbose_name=_("EBIOS RM study"),
        on_delete=models.CASCADE,
    )
    strategic_scenario = models.ForeignKey(
        StrategicScenario,
        verbose_name=_("Strategic scenario"),
        on_delete=models.CASCADE,
        related_name="attack_paths",
        help_text=_("Strategic scenario from which the attack path is derived"),
    )
    stakeholders = models.ManyToManyField(
        Stakeholder,
        verbose_name=_("Stakeholders"),
        related_name="attack_paths",
        help_text=_("Stakeholders leveraged by the attack path"),
        blank=True,
    )

    ref_id = models.CharField(max_length=100, blank=True)
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    fields_to_check = ["name", "ref_id"]

    class Meta:
        verbose_name = _("Attack path")
        verbose_name_plural = _("Attack paths")
        ordering = ["created_at"]

    def get_scope(self):
        return self.__class__.objects.filter(ebios_rm_study=self.ebios_rm_study)

    def save(self, *args, **kwargs):
        self.ebios_rm_study = self.strategic_scenario.ebios_rm_study
        self.folder = self.ebios_rm_study.folder
        super().save(*args, **kwargs)

    @property
    def ro_to_couple(self):
        return self.strategic_scenario.ro_to_couple

    @property
    def gravity(self):
        return self.ro_to_couple.get_gravity()


class OperationalScenario(AbstractBaseModel, FolderMixin):
    ebios_rm_study = models.ForeignKey(
        EbiosRMStudy,
        verbose_name=_("EBIOS RM study"),
        related_name="operational_scenarios",
        on_delete=models.CASCADE,
    )
    attack_path = models.OneToOneField(
        AttackPath,
        verbose_name=_("Attack path"),
        on_delete=models.CASCADE,
        related_name="operational_scenario",
        blank=False,
    )
    threats = models.ManyToManyField(
        Threat,
        verbose_name=_("Threats"),
        blank=True,
        related_name="operational_scenarios",
        help_text=_("Threats leveraged by the operational scenario"),
    )

    operating_modes_description = models.TextField(
        verbose_name=_("Operating modes description"),
        help_text=_("Description of the operating modes of the operational scenario"),
    )
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

    @property
    def ref_id(self):
        return self.attack_path.ref_id

    @property
    def name(self):
        return (
            self.attack_path.strategic_scenario.name[:95]
            + " - "
            + self.attack_path.name[:95]
        )

    @property
    def gravity(self):
        return self.attack_path.gravity

    @property
    def stakeholders(self):
        return self.attack_path.stakeholders.all()

    @property
    def ro_to(self):
        return self.attack_path.ro_to_couple

    def get_assets(self):
        initial_assets = Asset.objects.filter(
            feared_events__in=self.ro_to.feared_events.filter(is_selected=True)
        )
        assets = set()
        for asset in initial_assets:
            assets.add(asset)
            assets.update(asset.get_descendants())
        return Asset.objects.filter(id__in=[asset.id for asset in assets])

    def get_applied_controls(self):
        return AppliedControl.objects.filter(stakeholders__in=self.stakeholders.all())

    @staticmethod
    def format_likelihood(likelihood: int, parsed_matrix: dict):
        if likelihood < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
                "hexcolor": "#f9fafb",
            }
        risk_matrix = parsed_matrix
        if not risk_matrix["probability"][likelihood].get("hexcolor"):
            risk_matrix["probability"][likelihood]["hexcolor"] = "#f9fafb"
        return {
            **risk_matrix["probability"][likelihood],
            "value": likelihood,
        }

    def get_likelihood_display(self):
        return OperationalScenario.format_likelihood(
            self.likelihood, self.parsed_matrix
        )

    def get_gravity_display(self):
        return FearedEvent.format_gravity(
            self.gravity, self.ebios_rm_study.parsed_matrix
        )

    def get_risk_level_display(self):
        if self.likelihood < 0 or self.gravity < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
            }
        risk_matrix = self.parsed_matrix
        risk_index = risk_matrix["grid"][self.likelihood][self.gravity]
        return {
            **risk_matrix["risk"][risk_index],
            "value": risk_index,
        }
