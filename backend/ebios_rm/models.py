from typing import Final

from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.base_models import (
    AbstractBaseModel,
    ETADueDateMixin,
    NameDescriptionMixin,
)
from core.models import (
    Actor,
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
from ebios_rm import rating_kit
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
        MANUAL = "manual", "quotationMethodExpressDirect"
        EXPRESS = "express", "quotationMethodExpressOperatingModes"
        STANDARD = "standard", "quotationMethodStandard"
        ADVANCED = "advanced", "quotationMethodAdvanced"

    AVAILABLE_QUOTATION_METHODS = (
        QuotationMethod.MANUAL,
        QuotationMethod.EXPRESS,
        QuotationMethod.STANDARD,
        QuotationMethod.ADVANCED,
    )
    COMPUTED_QUOTATION_METHODS = (
        QuotationMethod.EXPRESS,
        QuotationMethod.STANDARD,
        QuotationMethod.ADVANCED,
    )
    STEP_QUOTATION_METHODS = (QuotationMethod.STANDARD, QuotationMethod.ADVANCED)

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
    reviewers = models.ManyToManyField(
        Actor,
        blank=True,
        verbose_name=_("Reviewers"),
        related_name="ebios_rm_study_reviewers",
    )
    authors = models.ManyToManyField(
        Actor,
        blank=True,
        verbose_name=_("Authors"),
        related_name="ebios_rm_study_authors",
    )
    observation = models.TextField(null=True, blank=True, verbose_name=_("Observation"))
    objectives = models.TextField(blank=True, verbose_name=_("Objectives"))
    constraints_hypotheses = models.TextField(
        blank=True, verbose_name=_("Constraints and hypotheses")
    )
    responsibility_matrix = models.ForeignKey(
        "pmbok.ResponsibilityMatrix",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_rm_studies",
        verbose_name=_("Responsibility matrix"),
        help_text=_("RACI of the study participants"),
    )
    classification = models.ForeignKey(
        "core.ClassificationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Classification"),
        help_text=_("Protection marking of the study"),
    )
    meta = models.JSONField(
        default=get_initial_meta,
        verbose_name=_("Metadata"),
        validators=[JSONSchemaInstanceValidator(META_JSONSCHEMA)],
    )

    quotation_method = models.CharField(
        max_length=100,
        choices=QuotationMethod.choices,
        default=QuotationMethod.EXPRESS,
        verbose_name=_("Quotation method"),
        help_text=_(
            "Likelihood method: 'manual' and 'express' are variants of the guide's express method (direct estimate, most likely operating mode); 'standard' and 'advanced' rate each elementary action"
        ),
    )

    fields_to_check = ["name", "version"]

    class Meta:
        verbose_name = _("Ebios RM Study")
        verbose_name_plural = _("Ebios RM Studies")
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        folder_changed = False
        if self.pk:
            old_study = (
                EbiosRMStudy.objects.filter(pk=self.pk)
                .values("risk_matrix_id", "folder_id")
                .first()
            )
            old_matrix_id = old_study["risk_matrix_id"] if old_study else None
            folder_changed = (
                old_study is not None and old_study["folder_id"] != self.folder_id
            )

            if old_matrix_id != self.risk_matrix_id:
                probabilities = list(range(len(self.risk_matrix.probability or [])))
                impacts = list(range(len(self.risk_matrix.impact or [])))
                min_prob, max_prob = min(probabilities), max(probabilities)
                min_impact, max_impact = min(impacts), max(impacts)
                for feared_event in self.feared_events.all():
                    if feared_event.gravity >= 0:
                        feared_event.gravity = max(
                            min_impact, min(feared_event.gravity, max_impact)
                        )
                        feared_event.save(update_fields=["gravity"])
                modes = OperatingMode.objects.filter(
                    operational_scenario__ebios_rm_study=self
                )
                modes.filter(likelihood__gt=max_prob).update(likelihood=max_prob)
                modes.filter(computed_likelihood__gt=max_prob).update(
                    computed_likelihood=max_prob
                )
                for operational_scenario in self.operational_scenarios.all():
                    if operational_scenario.likelihood_forced is not None:
                        operational_scenario.likelihood_forced = max(
                            min_prob,
                            min(operational_scenario.likelihood_forced, max_prob),
                        )
                    if operational_scenario.likelihood >= 0:
                        operational_scenario.likelihood = max(
                            min_prob, min(operational_scenario.likelihood, max_prob)
                        )
                        operational_scenario.save(
                            update_fields=["likelihood", "likelihood_forced"]
                        )
                for strategic_scenario in self.strategic_scenarios.filter(
                    gravity_forced__isnull=False
                ):
                    strategic_scenario.gravity_forced = max(
                        min_impact, min(strategic_scenario.gravity_forced, max_impact)
                    )
                    strategic_scenario.save(update_fields=["gravity_forced"])
                steps = KillChain.objects.filter(
                    operating_mode__operational_scenario__ebios_rm_study=self
                )
                steps.filter(success_probability__gt=max_prob).update(
                    success_probability=max_prob
                )
                steps.filter(technical_difficulty__gt=max_prob).update(
                    technical_difficulty=max_prob
                )
                self.__dict__.pop("_rating_kit_cache", None)
                for ro_to in self.roto_set.all():
                    ro_to.ebios_rm_study = self
                    ro_to.save(update_fields=["pertinence"])

        with transaction.atomic():
            super().save(*args, **kwargs)
            if folder_changed:
                for model, study_path in STUDY_FOLDER_CASCADE_MODELS.items():
                    model.objects.filter(**{study_path: self}).update(
                        folder=self.folder
                    )

        if self.quotation_method in self.STEP_QUOTATION_METHODS:
            for operating_mode in OperatingMode.objects.filter(
                operational_scenario__ebios_rm_study=self
            ):
                operating_mode.save(update_fields=["computed_likelihood"])
        elif self.quotation_method == self.QuotationMethod.EXPRESS:
            for scenario in self.operational_scenarios.all():
                scenario.update_likelihood_from_operating_modes()

    def rating_kit(self, translated: bool = False) -> dict:
        """The matrix's EBIOS RM scales and grids, defaults filled in."""
        cache = self.__dict__.setdefault("_rating_kit_cache", {})
        key = (self.risk_matrix_id, translated)
        if key not in cache:
            definition = (
                self.risk_matrix.parse_json_translated()
                if translated
                else self.risk_matrix.json_definition
            )
            cache[key] = rating_kit.resolve(definition)
        return cache[key]

    def ro_to_scales(self, translated: bool = False) -> dict:
        return self.rating_kit(translated)["ro_to"]

    def refresh_ratings(self):
        self.__dict__.pop("_rating_kit_cache", None)
        for ro_to in self.roto_set.all():
            ro_to.ebios_rm_study = self
            ro_to.save(update_fields=["pertinence"])
        if self.quotation_method in self.STEP_QUOTATION_METHODS:
            for operating_mode in OperatingMode.objects.filter(
                operational_scenario__ebios_rm_study=self
            ):
                operating_mode.save(update_fields=["computed_likelihood"])

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
        related_name="feared_events",
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
        EbiosRMStudy.objects.filter(id=self.ebios_rm_study.id).update(
            updated_at=timezone.now()
        )

    def delete(self, *args, **kwargs):
        ebios_rm_study_id = self.ebios_rm_study.id
        result = super().delete(*args, **kwargs)
        EbiosRMStudy.objects.filter(id=ebios_rm_study_id).update(
            updated_at=timezone.now()
        )
        return result

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
    target_objective_category = models.ForeignKey(
        Terminology,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Target objective category"),
        related_name="roto_target_objective_categories",
        limit_choices_to={
            "field_path": Terminology.FieldPath.ROTO_TARGET_OBJECTIVE_CATEGORY,
            "is_visible": True,
        },
    )
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
    pertinence = models.PositiveSmallIntegerField(
        verbose_name=_("Pertinence"),
        choices=Pertinence.choices,
        default=Pertinence.UNDEFINED,
        editable=False,
        help_text=_("Derived from motivation and resources through the study's matrix"),
    )
    is_selected = models.BooleanField(verbose_name=_("Is selected"), default=False)
    justification = models.TextField(verbose_name=_("Justification"), blank=True)

    fields_to_check = ["ebios_rm_study", "target_objective", "risk_origin"]

    def __str__(self) -> str:
        return f"{self.risk_origin.get_name_translated} - {self.target_objective}"

    class Meta:
        verbose_name = _("RO/TO couple")
        verbose_name_plural = _("RO/TO couples")
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.ebios_rm_study.folder
        self.pertinence = rating_kit.pertinence(
            self.ebios_rm_study.ro_to_scales(), self.motivation, self.resources
        )
        if (update_fields := kwargs.get("update_fields")) is not None:
            kwargs["update_fields"] = {*update_fields, "pertinence"}
        super().save(*args, **kwargs)
        EbiosRMStudy.objects.filter(id=self.ebios_rm_study.id).update(
            updated_at=timezone.now()
        )

    def delete(self, *args, **kwargs):
        ebios_rm_study_id = self.ebios_rm_study.id
        result = super().delete(*args, **kwargs)
        EbiosRMStudy.objects.filter(id=ebios_rm_study_id).update(
            updated_at=timezone.now()
        )
        return result

    def _scale_label(self, scale: str, level: int) -> str:
        if not level:
            return "undefined"
        return self.ebios_rm_study.ro_to_scales(translated=True)[scale][level - 1][
            "name"
        ]

    def get_motivation_display(self):
        return self._scale_label("motivation", self.motivation)

    def get_resources_display(self):
        return self._scale_label("resources", self.resources)

    def get_activity_display(self):
        return self._scale_label("activity", self.activity)

    def get_pertinence_display(self):
        return self._scale_label("pertinence", self.pertinence)

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

    IAM_SCOPE_FIELD = "entity"

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
        EbiosRMStudy.objects.filter(id=self.ebios_rm_study.id).update(
            updated_at=timezone.now()
        )

    def delete(self, *args, **kwargs):
        ebios_rm_study_id = self.ebios_rm_study.id
        result = super().delete(*args, **kwargs)
        EbiosRMStudy.objects.filter(id=ebios_rm_study_id).update(
            updated_at=timezone.now()
        )
        return result

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
    focused_feared_event = models.ForeignKey(
        FearedEvent,
        verbose_name=_("Focused feared event"),
        related_name="focused_strategic_scenarios",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("Override gravity with this specific feared event's gravity"),
    )
    gravity_forced = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Forced gravity"),
        help_text=_("Gravity level set by the analyst, replacing the computed one"),
    )

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
        EbiosRMStudy.objects.filter(id=self.ebios_rm_study.id).update(
            updated_at=timezone.now()
        )

    def delete(self, *args, **kwargs):
        ebios_rm_study_id = self.ebios_rm_study.id
        result = super().delete(*args, **kwargs)
        EbiosRMStudy.objects.filter(id=ebios_rm_study_id).update(
            updated_at=timezone.now()
        )
        return result

    @property
    def computed_gravity(self) -> int:
        if self.focused_feared_event:
            return self.focused_feared_event.gravity
        return self.ro_to_couple.get_gravity()

    @property
    def gravity(self) -> int:
        """Gravity in effect: forced, else focused feared event, else the RoTo's."""
        if self.gravity_forced is not None:
            return self.gravity_forced
        return self.computed_gravity

    def get_gravity_display(self):
        return FearedEvent.format_gravity(
            self.gravity, self.ebios_rm_study.parsed_matrix
        )

    def get_computed_gravity_display(self):
        return FearedEvent.format_gravity(
            self.computed_gravity, self.ebios_rm_study.parsed_matrix
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
        EbiosRMStudy.objects.filter(id=self.ebios_rm_study.id).update(
            updated_at=timezone.now()
        )

    def delete(self, *args, **kwargs):
        ebios_rm_study_id = self.ebios_rm_study.id
        result = super().delete(*args, **kwargs)
        EbiosRMStudy.objects.filter(id=ebios_rm_study_id).update(
            updated_at=timezone.now()
        )
        return result

    @classmethod
    def get_default_ref_id(cls, strategic_scenario):
        attack_paths_ref_ids = list(
            strategic_scenario.attack_paths.values_list("ref_id", flat=True)
        )
        nb_attack_paths = len(attack_paths_ref_ids) + 1
        candidates = [f"AP.{i:02d}" for i in range(1, nb_attack_paths + 1)]
        return next(x for x in candidates if x not in attack_paths_ref_ids)

    @property
    def form_display_name(self):
        """Returns attack path name with strategic scenario for form dropdown display"""
        base_name = self.name or f"Attack Path {str(self.id)[:8]}"
        if self.strategic_scenario:
            return f"{base_name} ({self.strategic_scenario.name})"
        return base_name

    @property
    def ro_to_couple(self):
        return self.strategic_scenario.ro_to_couple

    @property
    def gravity(self):
        return self.strategic_scenario.gravity


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
        "carrot": {"hex": "f787", "fa": "fa-solid fa-carrot"},
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
    technique = models.ForeignKey(
        "sec_intel.Technique",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ebios_rm_elementary_actions",
        verbose_name=_("Technique"),
        help_text=_("Catalogue technique this elementary action derives from"),
    )
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

    fields_to_check = ["ref_id", "name"]

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
    likelihood = models.SmallIntegerField(default=-1, verbose_name="Likelihood")
    computed_likelihood = models.SmallIntegerField(
        default=-1,
        editable=False,
        verbose_name="Computed likelihood",
        help_text="Roll-up of the step ratings under the standard and advanced methods",
    )
    graph_columns = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stage column positions and sizes in the graph editor",
    )

    fields_to_check = ["name", "operational_scenario", "ref_id"]

    class Meta:
        verbose_name = "Operating Mode"
        verbose_name_plural = "Operating Modes"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.operational_scenario.folder
        if self.pk and (quotation := self.quotation()) is not None:
            self.computed_likelihood = quotation.likelihood
        super().save(*args, **kwargs)
        self.operational_scenario.update_likelihood_from_operating_modes()
        EbiosRMStudy.objects.filter(id=self.ebios_rm_study.id).update(
            updated_at=timezone.now()
        )

    def delete(self, *args, **kwargs):
        operational_scenario = self.operational_scenario
        ebios_rm_study_id = self.ebios_rm_study.id
        super().delete(*args, **kwargs)
        operational_scenario.update_likelihood_from_operating_modes()
        EbiosRMStudy.objects.filter(id=ebios_rm_study_id).update(
            updated_at=timezone.now()
        )

    @property
    def ebios_rm_study(self):
        return self.operational_scenario.ebios_rm_study

    @property
    def risk_matrix(self):
        return self.operational_scenario.risk_matrix

    @property
    def parsed_matrix(self):
        return self.risk_matrix.parse_json_translated()

    @property
    def effective_likelihood(self) -> int:
        """The computed roll-up under step methods; the analyst's own value otherwise."""
        if self.ebios_rm_study.quotation_method in EbiosRMStudy.STEP_QUOTATION_METHODS:
            return self.computed_likelihood
        return self.likelihood

    def get_likelihood_display(self):
        return OperationalScenario.format_likelihood(
            self.effective_likelihood, self.parsed_matrix
        )

    def quotation(self):
        """Roll-up of the step ratings under a standard or advanced study, else None."""
        from ebios_rm.quotation import quote_operating_mode

        return quote_operating_mode(self)

    def refresh_likelihood(self):
        if self.ebios_rm_study.quotation_method in EbiosRMStudy.STEP_QUOTATION_METHODS:
            self.save(update_fields=["computed_likelihood"])

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
    techniques = models.ManyToManyField(
        "sec_intel.Technique",
        verbose_name=_("Techniques"),
        blank=True,
        related_name="operational_scenarios",
        help_text=_("Adversary techniques leveraged by the operational scenario"),
    )

    operating_modes_description = models.TextField(
        verbose_name=_("Operating modes description"),
        help_text=_("Description of the operating modes of the operational scenario"),
        blank=True,
    )
    likelihood = models.SmallIntegerField(default=-1, verbose_name=_("Likelihood"))
    likelihood_forced = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Forced likelihood"),
        help_text=_("Likelihood level set by the analyst, replacing the computed one"),
    )
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
        # `likelihood` always holds the value in effect, so every reader picks up
        # a forced value; clearing it falls back to the computed one.
        if self.likelihood_forced is not None:
            self.likelihood = self.likelihood_forced
        elif self.pk and self.computed_likelihood is not None:
            self.likelihood = self.computed_likelihood
        super().save(*args, **kwargs)
        EbiosRMStudy.objects.filter(id=self.ebios_rm_study.id).update(
            updated_at=timezone.now()
        )

    def delete(self, *args, **kwargs):
        ebios_rm_study_id = self.ebios_rm_study.id
        result = super().delete(*args, **kwargs)
        EbiosRMStudy.objects.filter(id=ebios_rm_study_id).update(
            updated_at=timezone.now()
        )
        return result

    @property
    def computed_likelihood(self) -> int | None:
        """Likelihood derived by the study's method; None when it is estimated directly."""
        if (
            self.ebios_rm_study.quotation_method
            not in EbiosRMStudy.COMPUTED_QUOTATION_METHODS
        ):
            return None
        source = (
            "computed_likelihood"
            if self.ebios_rm_study.quotation_method
            in EbiosRMStudy.STEP_QUOTATION_METHODS
            else "likelihood"
        )
        max_likelihood = self.operating_modes.aggregate(max_l=models.Max(source))[
            "max_l"
        ]
        return -1 if max_likelihood is None else max_likelihood

    def get_computed_likelihood_display(self):
        if self.computed_likelihood is None:
            return None
        return OperationalScenario.format_likelihood(
            self.computed_likelihood, self.parsed_matrix
        )

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

    def most_likely_operating_mode(self) -> dict | None:
        """
        The operating mode the computed likelihood comes from (the least-effort one),
        with the critical steps of its kill chain under standard and advanced methods.
        """
        if (
            self.ebios_rm_study.quotation_method
            not in EbiosRMStudy.COMPUTED_QUOTATION_METHODS
        ):
            return None
        candidates = []
        for operating_mode in self.operating_modes.all():
            if operating_mode.effective_likelihood < 0:
                continue
            quotation = operating_mode.quotation()
            effort = quotation.effort if quotation else -1
            # Highest likelihood first; on a tie, the lowest cumulative difficulty.
            rank = (operating_mode.effective_likelihood, -effort if effort >= 0 else 0)
            candidates.append((rank, operating_mode, quotation))
        if not candidates:
            return None
        _, operating_mode, quotation = max(candidates, key=lambda c: c[0])
        critical_steps = []
        if quotation is not None:
            steps = {
                str(step.id): step
                for step in operating_mode.kill_chain_steps.select_related(
                    "elementary_action"
                )
            }
            critical_steps = [
                {"id": step_id, "name": steps[step_id].elementary_action.name}
                for step_id in quotation.critical_steps()
            ]
        return {
            "id": str(operating_mode.id),
            "str": " - ".join(
                filter(None, [operating_mode.ref_id, operating_mode.name])
            ),
            "likelihood": operating_mode.get_likelihood_display(),
            "critical_steps": critical_steps,
        }

    def update_likelihood_from_operating_modes(self):
        if (
            self.ebios_rm_study.quotation_method
            not in EbiosRMStudy.COMPUTED_QUOTATION_METHODS
        ):
            return
        if self.likelihood_forced is not None:
            return
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
        "self",
        symmetrical=False,
        related_name="successors",
        blank=True,
        help_text="Kill chain steps of the same operating mode that precede this step",
    )
    # Action-based antecedents from before steps became graph nodes, kept untouched
    legacy_antecedent_actions = models.ManyToManyField(
        ElementaryAction,
        related_name="kill_chain_antecedents",
        blank=True,
        editable=False,
        help_text="Antecedent elementary actions recorded before antecedents pointed to steps",
    )
    assets = models.ManyToManyField(
        Asset,
        blank=True,
        related_name="kill_chain_steps",
        verbose_name=_("Supporting assets"),
        help_text=_("Supporting assets this elementary action applies to"),
    )
    success_probability = models.SmallIntegerField(
        default=-1,
        verbose_name=_("Success probability"),
        help_text=_("Level on the study's likelihood scale, -1 when not rated"),
    )
    success_probability_pct = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Success probability (%)"),
    )
    technical_difficulty = models.SmallIntegerField(
        default=-1,
        verbose_name=_("Technical difficulty"),
        help_text=_("Level on the study's likelihood scale, -1 when not rated"),
    )
    position_x = models.FloatField(
        default=0,
        help_text="X position of the node in the graph editor",
    )
    position_y = models.FloatField(
        default=0,
        help_text="Y position of the node in the graph editor",
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

    def descendant_ids(self) -> set:
        """Ids of every step reachable from this one through successors."""
        edges: dict = {}
        for step_id, antecedent_id in KillChain.antecedents.through.objects.filter(
            from_killchain__operating_mode_id=self.operating_mode_id
        ).values_list("from_killchain_id", "to_killchain_id"):
            edges.setdefault(antecedent_id, set()).add(step_id)
        seen: set = set()
        stack = [self.pk]
        while stack:
            for successor_id in edges.get(stack.pop(), ()):
                if successor_id not in seen:
                    seen.add(successor_id)
                    stack.append(successor_id)
        return seen

    def __str__(self):
        return f"{self.operating_mode} - {self.elementary_action.name}"


# Models whose folder mirrors the study's folder, mapped to the queryset path
# leading back to the study. EbiosRMStudy.save() cascades folder changes over
# this mapping, so a folder-scoped ebios_rm model must be added here to follow
# the study on a domain move (ElementaryAction is intentionally excluded: it is
# a shared catalog object with a user-managed folder).
STUDY_FOLDER_CASCADE_MODELS: Final[dict[type[models.Model], str]] = {
    FearedEvent: "ebios_rm_study",
    RoTo: "ebios_rm_study",
    Stakeholder: "ebios_rm_study",
    StrategicScenario: "ebios_rm_study",
    AttackPath: "ebios_rm_study",
    OperationalScenario: "ebios_rm_study",
    OperatingMode: "operational_scenario__ebios_rm_study",
    KillChain: "operating_mode__operational_scenario__ebios_rm_study",
}


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
auditlog.register(
    ElementaryAction,
    exclude_fields=common_exclude,
)
auditlog.register(
    KillChain,
    exclude_fields=common_exclude,
)
auditlog.register(
    OperatingMode,
    exclude_fields=common_exclude,
)
