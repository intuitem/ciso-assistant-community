from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator
from core.base_models import NameDescriptionMixin, AbstractBaseModel
from core.models import (
    Assessment,
    ComplianceAssessment,
    Evidence,
    Asset,
    Terminology,
    FilteringLabelMixin,
)
from core.constants import COUNTRY_CHOICES, CURRENCY_CHOICES
from core.dora import (
    DORA_ENTITY_TYPE_CHOICES,
    DORA_ENTITY_HIERARCHY_CHOICES,
    DORA_CONTRACTUAL_ARRANGEMENT_CHOICES,
    TERMINATION_REASON_CHOICES,
    DORA_ICT_SERVICE_CHOICES,
    DORA_SENSITIVENESS_CHOICES,
    DORA_RELIANCE_CHOICES,
    DORA_PROVIDER_PERSON_TYPE_CHOICES,
    DORA_SUBSTITUTABILITY_CHOICES,
    DORA_NON_SUBSTITUTABILITY_REASON_CHOICES,
    DORA_BINARY_CHOICES,
    DORA_REINTEGRATION_POSSIBILITY_CHOICES,
    DORA_DISCONTINUING_IMPACT_CHOICES,
)
from iam.models import Folder, FolderMixin, PublishInRootFolderMixin
from iam.views import User

from auditlog.registry import auditlog


class Entity(
    NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin, FilteringLabelMixin
):
    """
    An entity represents a legal entity, a corporate body, an administrative body, an association
    """

    ref_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    default_dependency = models.PositiveSmallIntegerField(
        verbose_name=_("Default dependency"),
        default=0,
        blank=True,
        validators=[MaxValueValidator(4)],
        help_text=_("Default dependency level for stakeholder assessment (0-4)"),
    )
    default_penetration = models.PositiveSmallIntegerField(
        verbose_name=_("Default penetration"),
        default=0,
        blank=True,
        validators=[MaxValueValidator(4)],
        help_text=_("Default penetration level for stakeholder assessment (0-4)"),
    )
    default_maturity = models.PositiveSmallIntegerField(
        verbose_name=_("Default maturity"),
        default=1,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text=_("Default maturity level for stakeholder assessment (1-4)"),
    )
    default_trust = models.PositiveSmallIntegerField(
        verbose_name=_("Default trust"),
        default=1,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text=_("Default trust level for stakeholder assessment (1-4)"),
    )
    mission = models.TextField(blank=True)
    reference_link = models.URLField(blank=True, null=True, max_length=2048)
    owned_folders = models.ManyToManyField(
        "iam.Folder",
        related_name="owner",
        blank=True,
        verbose_name=_("Owned folders"),
    )
    builtin = models.BooleanField(default=False)
    parent_entity = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="branches",
        verbose_name=_("Parent entity"),
        help_text=_("Parent entity for branch/subsidiary relationships"),
    )
    relationship = models.ManyToManyField(
        Terminology,
        blank=True,
        related_name="entities",
        limit_choices_to={
            "field_path": Terminology.FieldPath.ENTITY_RELATIONSHIP,
            "is_visible": True,
        },
        verbose_name=_("Relationship"),
        help_text=_("Type of relationship with this entity"),
    )
    legal_identifiers = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Legal identifiers"),
        help_text=_("Legal identifiers (LEI, EUID, VAT, DUNS, etc.)"),
    )
    country = models.CharField(
        max_length=3,
        choices=COUNTRY_CHOICES,
        blank=True,
        verbose_name=_("Country"),
        help_text=_("Country where the entity is located"),
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        blank=True,
        verbose_name=_("Currency"),
        help_text=_("Default currency for the entity"),
    )
    dora_entity_type = models.CharField(
        max_length=20,
        choices=DORA_ENTITY_TYPE_CHOICES,
        blank=True,
        verbose_name=_("DORA entity type"),
        help_text=_("DORA entity type classification"),
    )
    dora_entity_hierarchy = models.CharField(
        max_length=20,
        choices=DORA_ENTITY_HIERARCHY_CHOICES,
        blank=True,
        verbose_name=_("DORA entity hierarchy"),
        help_text=_("DORA entity hierarchy classification"),
    )
    dora_assets_value = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("DORA assets value"),
        help_text=_("Total assets value for DORA reporting"),
    )
    dora_competent_authority = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("DORA competent authority"),
        help_text=_("Competent authority overseeing this entity for DORA compliance"),
    )
    dora_provider_person_type = models.CharField(
        max_length=20,
        choices=DORA_PROVIDER_PERSON_TYPE_CHOICES,
        blank=True,
        verbose_name=_("DORA provider person type"),
        help_text=_("Type of person for ICT third-party service providers"),
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Entity")
        verbose_name_plural = _("Entities")

    @classmethod
    def get_main_entity(cls):
        return (
            cls.objects.filter(builtin=True)
            .filter(owned_folders=Folder.get_root_folder())
            .order_by("created_at")
            .first()
        )


class EntityAssessment(Assessment):
    class Conclusion(models.TextChoices):
        BLOCKER = "blocker", _("Blocker")
        WARNING = "warning", _("Warning")
        OK = "ok", _("Ok")
        NA = "not_applicable", _("Not applicable")

    criticality = models.IntegerField(default=0, verbose_name=_("Criticality"))
    penetration = models.IntegerField(default=0, verbose_name=_("Penetration"))
    dependency = models.IntegerField(default=0, verbose_name=_("Dependency"))
    maturity = models.IntegerField(default=0, verbose_name=_("Maturity"))
    trust = models.IntegerField(default=0, verbose_name=_("Trust"))
    representatives = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Representative"),
        related_name="entity_assessments",
    )
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
    )
    solutions = models.ManyToManyField(
        "tprm.Solution",
        related_name="entity_assessments",
        blank=True,
        verbose_name=_("Solutions"),
    )
    compliance_assessment = models.ForeignKey(
        ComplianceAssessment, on_delete=models.SET_NULL, blank=True, null=True
    )
    evidence = models.ForeignKey(
        Evidence, on_delete=models.SET_NULL, blank=True, null=True
    )
    conclusion = models.CharField(
        max_length=14,
        choices=Conclusion.choices,
        verbose_name=_("Conclusion"),
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Entity assessment")
        verbose_name_plural = _("Entity assessments")


class Representative(AbstractBaseModel, FilteringLabelMixin):
    """
    This represents a person that is linked to an entity (typically an employee),
    and that is relevant for the main entity, like a contact person for an assessment
    """

    ref_id = models.CharField(max_length=255, blank=True)
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="representatives",
        verbose_name=_("Entity"),
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    fields_to_check = ["email"]


class Solution(NameDescriptionMixin, FilteringLabelMixin):
    """
    A solution represents a product or service that is offered by an entity
    """

    provider_entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="provided_solutions",
        verbose_name=_("Provider entity"),
    )
    recipient_entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="received_solutions",
        verbose_name=_("Recipient entity"),
        null=True,
        blank=True,
    )
    ref_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    reference_link = models.URLField(blank=True, null=True, max_length=2048)
    criticality = models.IntegerField(default=0, verbose_name=_("Criticality"))

    assets = models.ManyToManyField(
        Asset,
        verbose_name=_("Related assets"),
        blank=True,
        help_text=_("Assets related to the solution"),
        related_name="solutions",
    )
    dora_ict_service_type = models.CharField(
        max_length=20,
        choices=DORA_ICT_SERVICE_CHOICES,
        blank=True,
        verbose_name=_("DORA ICT service type"),
        help_text=_("DORA ICT service type classification"),
    )
    storage_of_data = models.BooleanField(
        default=False,
        verbose_name=_("Storage of data"),
        help_text=_("Whether data is stored by the ICT service provider"),
    )
    data_location_storage = models.CharField(
        max_length=3,
        choices=COUNTRY_CHOICES,
        blank=True,
        verbose_name=_("Location of data at rest"),
        help_text=_("Country where data is stored"),
    )
    data_location_processing = models.CharField(
        max_length=3,
        choices=COUNTRY_CHOICES,
        blank=True,
        verbose_name=_("Location of data processing"),
        help_text=_("Country where data is processed/managed"),
    )
    dora_data_sensitiveness = models.CharField(
        max_length=20,
        choices=DORA_SENSITIVENESS_CHOICES,
        blank=True,
        verbose_name=_("Data sensitiveness"),
        help_text=_("Sensitiveness of the data stored"),
    )
    dora_reliance_level = models.CharField(
        max_length=20,
        choices=DORA_RELIANCE_CHOICES,
        blank=True,
        verbose_name=_("Level of reliance"),
        help_text=_("Level of reliance on the ICT service"),
    )
    dora_substitutability = models.CharField(
        max_length=20,
        choices=DORA_SUBSTITUTABILITY_CHOICES,
        blank=True,
        verbose_name=_("Substitutability"),
        help_text=_("Substitutability of the ICT third-party service provider"),
    )
    dora_non_substitutability_reason = models.CharField(
        max_length=20,
        choices=DORA_NON_SUBSTITUTABILITY_REASON_CHOICES,
        blank=True,
        verbose_name=_("Non-substitutability reason"),
        help_text=_(
            "Reason if the ICT third-party service provider is considered not substitutable or difficult to be substitutable"
        ),
    )
    dora_has_exit_plan = models.CharField(
        max_length=20,
        choices=DORA_BINARY_CHOICES,
        blank=True,
        verbose_name=_("Exit plan"),
        help_text=_("Existence of an exit plan"),
    )
    dora_reintegration_possibility = models.CharField(
        max_length=20,
        choices=DORA_REINTEGRATION_POSSIBILITY_CHOICES,
        blank=True,
        verbose_name=_("Reintegration possibility"),
        help_text=_("Possibility of reintegration of the contracted ICT service"),
    )
    dora_discontinuing_impact = models.CharField(
        max_length=20,
        choices=DORA_DISCONTINUING_IMPACT_CHOICES,
        blank=True,
        verbose_name=_("Discontinuing impact"),
        help_text=_("Impact of discontinuing the ICT services"),
    )
    dora_alternative_providers_identified = models.CharField(
        max_length=20,
        choices=DORA_BINARY_CHOICES,
        blank=True,
        verbose_name=_("Alternative providers identified"),
        help_text=_(
            "Are there alternative ICT third-party service providers identified?"
        ),
    )
    dora_alternative_providers = models.TextField(
        blank=True,
        verbose_name=_("Alternative providers"),
        help_text=_("Identification of alternative ICT third-party service providers"),
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Solution")
        verbose_name_plural = _("Solutions")


class Contract(NameDescriptionMixin, FolderMixin, FilteringLabelMixin):
    """
    A contract represents an agreement between multiple entities
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ACTIVE = "active", _("Active")
        EXPIRED = "expired", _("Expired")
        TERMINATED = "terminated", _("Terminated")

    owner = models.ManyToManyField(
        User,
        verbose_name=_("Owner"),
        related_name="contracts",
        blank=True,
    )
    provider_entity = models.ForeignKey(
        Entity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
        verbose_name=_("Provider entity"),
        help_text=_("Entity providing this contract"),
    )
    beneficiary_entity = models.ForeignKey(
        Entity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="beneficiary_contracts",
        verbose_name=_("Beneficiary entity"),
        help_text=_("Entity benefiting from/receiving this contract"),
    )
    evidences = models.ManyToManyField(
        Evidence,
        blank=True,
        related_name="contracts",
        verbose_name=_("Evidences"),
        help_text=_("Supporting evidence for this contract"),
    )
    solution = models.ForeignKey(
        "tprm.Solution",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="contracts",
        verbose_name=_("Solution"),
        help_text=_("Solution covered by this contract"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Status"),
    )
    start_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Start date"),
    )
    end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("End date"),
    )
    ref_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Reference ID"),
        help_text=_("Contract reference number or identifier"),
    )
    dora_contractual_arrangement = models.CharField(
        max_length=20,
        choices=DORA_CONTRACTUAL_ARRANGEMENT_CHOICES,
        default="eba_CO:x1",
        verbose_name=_("DORA contractual arrangement"),
        help_text=_("DORA contractual arrangement type"),
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        blank=True,
        verbose_name=_("Currency"),
        help_text=_("Currency for contract expenses"),
    )
    annual_expense = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Annual expense"),
        help_text=_("Annual expense amount for this contract"),
    )
    termination_reason = models.CharField(
        max_length=20,
        choices=TERMINATION_REASON_CHOICES,
        blank=True,
        verbose_name=_("Termination reason"),
        help_text=_("Reason for contract termination"),
    )
    is_intragroup = models.BooleanField(
        default=False,
        verbose_name=_("Is intragroup"),
        help_text=_("Whether this is an intragroup contract"),
    )
    overarching_contract = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinate_contracts",
        verbose_name=_("Overarching contract"),
        help_text=_("Parent/overarching contract if this is a subordinate arrangement"),
    )
    governing_law_country = models.CharField(
        max_length=3,
        choices=COUNTRY_CHOICES,
        blank=True,
        verbose_name=_("Governing law country"),
        help_text=_("Country whose law governs this contract"),
    )
    notice_period_entity = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Notice period for entity (days)"),
        help_text=_("Notice period in days for the financial entity"),
    )
    notice_period_provider = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Notice period for provider (days)"),
        help_text=_("Notice period in days for the ICT third-party service provider"),
    )

    fields_to_check = ["name"]

    def save(self, *args, **kwargs):
        # If beneficiary_entity is not set, default to main entity
        if not self.beneficiary_entity:
            main_entity = Entity.get_main_entity()
            if main_entity:
                self.beneficiary_entity = main_entity
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Contract")
        verbose_name_plural = _("Contracts")


common_exclude = ["created_at", "updated_at"]

auditlog.register(
    Entity,
    exclude_fields=common_exclude,
)
auditlog.register(
    EntityAssessment,
    exclude_fields=common_exclude,
)
auditlog.register(
    Representative,
    exclude_fields=common_exclude,
)
auditlog.register(
    Solution,
    exclude_fields=common_exclude,
)
auditlog.register(
    Contract,
    exclude_fields=common_exclude,
)
