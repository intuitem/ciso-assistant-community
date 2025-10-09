from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Case, When, IntegerField, Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel, ETADueDateMixin, NameDescriptionMixin
from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    RiskAssessment,
    RiskMatrix,
    Threat,
    Terminology,
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
        {"steps": [{"status": "to_do"}, {"status": "to_do"}, {"status": "to_do"}]},
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

    class QuotationMethod(models.TextChoices):
        MANUAL = "manual", "Manual"
        EXPRESS = "express", "Express"

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

    quotation_method = models.CharField(
        max_length=100,
        choices=QuotationMethod.choices,
        default=QuotationMethod.MANUAL,
        verbose_name=_("Quotation method"),
        help_text=_(
            "Method used to quote the study: 'manual' for manual likelihood assessment, 'express' for automatic propagation from operating modes"
        ),
    )

    fields_to_check = ["name", "version"]

    class Meta:
        verbose_name = _("Ebios RM Study")
        verbose_name_plural = _("Ebios RM Studies")
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.quotation_method == "express":
            for scenario in self.operational_scenarios.all():
                scenario.update_likelihood_from_operating_modes()

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

    def get_counters(self):
        """Return all counters as a dictionary"""
        from core.models import RequirementAssessment

        # Get compliance applied controls count
        requirement_assessments = RequirementAssessment.objects.filter(
            compliance_assessment__in=self.compliance_assessments.all()
        )
        compliance_applied_control_count = (
            AppliedControl.objects.filter(
                requirement_assessments__in=requirement_assessments
            )
            .distinct()
            .count()
        )

        # Get risk assessment applied controls count
        risk_assessment_applied_control_count = 0
        if self.last_risk_assessment:
            risk_scenarios = self.last_risk_assessment.risk_scenarios.all()
            risk_assessment_applied_control_count = (
                AppliedControl.objects.filter(risk_scenarios__in=risk_scenarios)
                .distinct()
                .count()
            )

        return {
            "selected_asset_count": self.assets.count(),
            "selected_feared_event_count": FearedEvent.objects.filter(
                ebios_rm_study=self, is_selected=True
            ).count(),
            "compliance_assessment_count": self.compliance_assessments.count(),
            "roto_count": self.roto_set.count(),
            "stakeholder_count": Stakeholder.objects.filter(
                ebios_rm_study=self, is_selected=True
            ).count(),
            "strategic_scenario_count": StrategicScenario.objects.filter(
                ebios_rm_study=self
            ).count(),
            "operational_scenario_count": self.operational_scenarios.count(),
            "compliance_applied_control_count": compliance_applied_control_count,
            "risk_assessment_applied_control_count": risk_assessment_applied_control_count,
        }

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

        # Workshop 4 uses 0-based indexing (steps 0, 1, 2)
        min_step = 0 if workshop == 4 else 1

        if step < min_step or step > len(
            self.meta["workshops"][workshop - 1]["steps"]
        ) - (1 - min_step):
            raise ValueError(
                f"Workshop {workshop} has only {len(self.meta['workshops'][workshop - 1]['steps'])} steps"
            )

        # Workshop 4 uses step directly, others use step - 1
        index = step if workshop == 4 else step - 1
        self.meta["workshops"][workshop - 1]["steps"][index]["status"] = new_status
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
        Terminology,
        verbose_name="Qualifications",
        related_name="feared_events_qualifications",
        limit_choices_to={
            "field_path": Terminology.FieldPath.QUALIFICATIONS,
            "is_visible": True,
        },
        blank=True,
    )

    ref_id = models.CharField(max_length=100, blank=True)
    gravity = models.SmallIntegerField(default=-1, verbose_name=_("Gravity"))
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    fields_to_check = ["ebios_rm_study", "name", "ref_id"]

    class Meta:
        verbose_name = _("Feared event")
        verbose_name_plural = _("Feared events")
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        # Ensure the folder is set to the study's folder
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


class RoToQuerySet(models.QuerySet):
    def with_pertinence(self):
        """Annotate queryset with pertinence for ordering"""
        pertinence_annotation = Case(
            # Handle undefined cases (motivation = 0 or resources = 0)
            models.When(Q(motivation=0) | models.Q(resources=0), then=0),  # UNDEFINED
            # Matrix[0][0-3] - motivation=1
            When(motivation=1, resources=1, then=1),
            When(motivation=1, resources=2, then=1),
            When(motivation=1, resources=3, then=2),
            When(motivation=1, resources=4, then=2),
            # Matrix[1][0-3] - motivation=2
            When(motivation=2, resources=1, then=1),
            When(motivation=2, resources=2, then=2),
            When(motivation=2, resources=3, then=3),
            When(motivation=2, resources=4, then=3),
            # Matrix[2][0-3] - motivation=3
            When(motivation=3, resources=1, then=2),
            When(motivation=3, resources=2, then=3),
            When(motivation=3, resources=3, then=3),
            When(motivation=3, resources=4, then=4),
            # Matrix[3][0-3] - motivation=4
            When(motivation=4, resources=1, then=2),
            When(motivation=4, resources=2, then=3),
            When(motivation=4, resources=3, then=4),
            When(motivation=4, resources=4, then=4),
            default=0,
            output_field=IntegerField(),
        )
        return self.annotate(pertinence=pertinence_annotation)


class RoToManager(models.Manager):
    def get_queryset(self):
        return RoToQuerySet(self.model, using=self._db)

    def with_pertinence(self):
        return self.get_queryset().with_pertinence()


class RoTo(AbstractBaseModel, FolderMixin):
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

    risk_origin = models.ForeignKey(
        Terminology,
        on_delete=models.PROTECT,
        verbose_name=_("Risk origin"),
        related_name="roto_risk_origins",
        limit_choices_to={
            "field_path": Terminology.FieldPath.ROTO_RISK_ORIGIN,
            "is_visible": True,
        },
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

    fields_to_check = ["ebios_rm_study", "target_objective", "risk_origin"]

    objects = RoToManager()

    def __str__(self) -> str:
        return f"{self.risk_origin.get_name_translated} - {self.target_objective}"

    class Meta:
        verbose_name = _("RO/TO couple")
        verbose_name_plural = _("RO/TO couples")
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.ebios_rm_study.folder
        super().save(*args, **kwargs)

    def get_pertinence_display(self):
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

    category = models.ForeignKey(
        Terminology,
        on_delete=models.PROTECT,
        verbose_name=_("Category"),
        related_name="stakeholders_category",
        limit_choices_to={
            "field_path": Terminology.FieldPath.ENTITY_RELATIONSHIP,
            "is_visible": True,
        },
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

    fields_to_check = ["ebios_rm_study", "entity", "category"]

    class Meta:
        verbose_name = _("Stakeholder")
        verbose_name_plural = _("Stakeholders")
        ordering = ["created_at"]

    def get_scope(self):
        return self.__class__.objects.filter(ebios_rm_study=self.ebios_rm_study)

    def __str__(self):
        return f"{self.entity.name} ({self.category.get_name_translated if self.category else 'N/A'})"

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

    fields_to_check = ["ebios_rm_study", "name", "ref_id"]

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

    fields_to_check = ["ebios_rm_study", "name", "ref_id"]

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


class ElementaryAction(NameDescriptionMixin, FolderMixin):
    ICON_MAP = {
        "server": {"hex": "f233", "fa": "fas fa-server"},
        "computer": {"hex": "f108", "fa": "fas fa-desktop"},
        "cloud": {"hex": "f0c2", "fa": "fas fa-cloud"},
        "file": {"hex": "f15b", "fa": "fas fa-file"},
        "diamond": {"hex": "f3a5", "fa": "far fa-gem"},
        "phone": {"hex": "f095", "fa": "fas fa-phone"},
        "cube": {"hex": "f1b2", "fa": "fas fa-cube"},
        "blocks": {"hex": "f1b3", "fa": "fas fa-cubes"},
        "shapes": {"hex": "f61f", "fa": "fas fa-shapes"},
        "network": {"hex": "f6ff", "fa": "fas fa-network-wired"},
        "database": {"hex": "f1c0", "fa": "fas fa-database"},
        "key": {"hex": "f084", "fa": "fas fa-key"},
        "search": {"hex": "f002", "fa": "fa-solid fa-magnifying-glass"},
        "carrot": {"hex": "f084", "fa": "fa-solid fa-carrot"},
        "money": {"hex": "f81d", "fa": "fa-solid fa-sack-dollar"},
        "skull": {"hex": "f714", "fa": "fa-solid fa-skull-crossbones"},
        "globe": {"hex": "f0ac", "fa": "fa-solid fa-globe"},
        "usb": {"hex": "f287", "fa": "fa-brands fa-usb"},
    }

    class Icon(models.TextChoices):
        SERVER = "server", "Server"
        COMPUTER = "computer", "Computer"
        CLOUD = "cloud", "Cloud"
        FILE = "file", "File"
        DIAMOND = "diamond", "Diamond"
        PHONE = "phone", "Phone"
        CUBE = "cube", "Cube"
        BLOCKS = "blocks", "Blocks"
        SHAPES = "shapes", "Shapes"
        NETWORK = "network", "Network"
        DATABASE = "database", "Database"
        KEY = "key", "Key"
        SEARCH = "search", "Search"
        CARROT = "carrot", "Carrot"
        MONEY = "money", "Money"
        SKULL = "skull", "Skull"
        GLOBE = "globe", "Globe"
        USB = "usb", "USB"

    class AttackStage(models.IntegerChoices):
        KNOW = 0, "ebiosReconnaissance"
        ENTER = 1, "ebiosInitialAccess"
        DISCOVER = 2, "ebiosDiscovery"
        EXPLOIT = 3, "ebiosExploitation"

    ref_id = models.CharField(max_length=100, blank=True, verbose_name="Reference ID")
    threat = models.ForeignKey(
        Threat,
        on_delete=models.SET_NULL,
        verbose_name=_("Threat"),
        related_name="elementary_actions",
        help_text=_("Threat that the elementary action is derived from"),
        null=True,
        blank=True,
    )
    attack_stage = models.SmallIntegerField(
        choices=AttackStage.choices,
        default=AttackStage.KNOW,
        verbose_name="Attack Stage",
        help_text="Stage of the attack in the kill chain (e.g., 'Know', 'Enter', 'Discover', 'Exploit')",
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=Icon.choices,
        verbose_name="Icon",
        help_text="Icon representing the elementary action",
    )

    @property
    def icon_fa_hex(self):
        return f"&#x{self.ICON_MAP.get(self.icon)['hex']};" if self.icon else None

    @property
    def icon_fa_class(self):
        return self.ICON_MAP.get(self.icon)["fa"] if self.icon else None

    fields_to_check = ["name"]

    def __str__(self):
        return self.name if hasattr(self, "name") else f"ElementaryAction {self.id}"

    class Meta:
        verbose_name = "Elementary Action"
        verbose_name_plural = "Elementary Actions"
        ordering = ["name"]


class OperatingMode(NameDescriptionMixin, FolderMixin):
    ref_id = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Reference ID"
    )
    operational_scenario = models.ForeignKey(
        "OperationalScenario",
        verbose_name=_("Operational scenario"),
        on_delete=models.CASCADE,
        related_name="operating_modes",
    )
    elementary_actions = models.ManyToManyField(
        ElementaryAction,
        verbose_name=_("Elementary actions"),
        related_name="operating_modes",
        help_text=_("Elementary actions that are part of the operating mode"),
        blank=True,
    )
    likelihood = models.SmallIntegerField(default=-1, verbose_name="Likelihood")

    fields_to_check = ["name", "operational_scenario", "ref_id"]

    class Meta:
        verbose_name = "Operating Mode"
        verbose_name_plural = "Operating Modes"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.operational_scenario.folder
        super().save(*args, **kwargs)
        self.operational_scenario.update_likelihood_from_operating_modes()

    def delete(self, *args, **kwargs):
        operational_scenario = self.operational_scenario
        super().delete(*args, **kwargs)
        operational_scenario.update_likelihood_from_operating_modes()

    @property
    def ebios_rm_study(self):
        return self.operational_scenario.ebios_rm_study

    @property
    def risk_matrix(self):
        return self.operational_scenario.risk_matrix

    @property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()

    def get_likelihood_display(self):
        return OperationalScenario.format_likelihood(
            self.likelihood, self.parsed_matrix
        )

    @classmethod
    def get_default_ref_id(cls, operational_scenario):
        """return associated risk assessment id"""
        operating_modes_ref_ids = [
            x.ref_id for x in operational_scenario.operating_modes.all()
        ]
        nb_operating_modes = len(operating_modes_ref_ids) + 1
        candidates = [f"MO.{i:02d}" for i in range(1, nb_operating_modes + 1)]
        return next(x for x in candidates if x not in operating_modes_ref_ids)


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
        blank=True,
    )
    likelihood = models.SmallIntegerField(default=-1, verbose_name=_("Likelihood"))
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    @property
    def quotation_method(self):
        return self.ebios_rm_study.quotation_method

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

    def update_likelihood_from_operating_modes(self):
        if self.ebios_rm_study.quotation_method != "express":
            return

        max_likelihood = (
            self.operating_modes.aggregate(max_l=models.Max("likelihood"))["max_l"]
            if self.operating_modes.exists()
            else -1
        )

        self.likelihood = max_likelihood
        self.save(update_fields=["likelihood"])


class KillChain(AbstractBaseModel, FolderMixin):
    class LogicOperator(models.TextChoices):
        AND = "AND", "AND"
        OR = "OR", "OR"

    operating_mode = models.ForeignKey(
        OperatingMode, on_delete=models.CASCADE, related_name="kill_chain_steps"
    )
    elementary_action = models.ForeignKey(
        ElementaryAction, on_delete=models.PROTECT, related_name="as_kill_chain"
    )
    is_highlighted = models.BooleanField(default=False)
    logic_operator = models.CharField(
        max_length=10,
        choices=LogicOperator.choices,
        blank=True,
        null=True,
        help_text="Logic operator to apply between antecedents",
    )

    antecedents = models.ManyToManyField(
        ElementaryAction,
        related_name="kill_chain_antecedents",
        blank=True,
        help_text="Elementary actions that are antecedents to this action in the kill chain",
    )

    @property
    def attack_stage(self):
        return self.elementary_action.get_attack_stage_display()

    class Meta:
        verbose_name = "Kill Chain"
        verbose_name_plural = "Kill Chains"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.operating_mode.folder
        super().save(*args, **kwargs)

    def clean(self):
        existing = KillChain.objects.filter(
            operating_mode=self.operating_mode,
            elementary_action=self.elementary_action,
        )
        if self.pk:
            existing = existing.exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError(
                {
                    "elementary_action": f"The elementary action '{self.elementary_action}' is already used in this operating mode's kill chain."
                }
            )

    def __str__(self):
        return f"{self.operating_mode} - {self.elementary_action.name}"


common_exclude = ["created_at", "updated_at"]
auditlog.register(
    EbiosRMStudy,
    exclude_fields=common_exclude,
)
auditlog.register(
    FearedEvent,
    exclude_fields=common_exclude,
)
auditlog.register(
    RoTo,
    exclude_fields=common_exclude,
)
auditlog.register(
    Stakeholder,
    exclude_fields=common_exclude,
)
auditlog.register(
    StrategicScenario,
    exclude_fields=common_exclude,
)
auditlog.register(
    AttackPath,
    exclude_fields=common_exclude,
)
auditlog.register(
    OperationalScenario,
    exclude_fields=common_exclude,
)
