from django.db import models
from django.utils.translation import gettext_lazy as _
from core.base_models import NameDescriptionMixin, AbstractBaseModel
from core.models import Assessment, ComplianceAssessment, Evidence
from iam.models import FolderMixin, PublishInRootFolderMixin


class Entity(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    """
    An entity represents a legal entity, a corporate body, an administrative body, an association
    """

    mission = models.TextField(blank=True)
    reference_link = models.URLField(blank=True, null=True)
    owned_folders = models.ManyToManyField(
        "iam.Folder",
        related_name="owner",
        blank=True,
        verbose_name=_("Owned folders"),
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Entity")
        verbose_name_plural = _("Entities")


class EntityAssessment(Assessment):
    criticality = models.IntegerField(default=0, verbose_name=_("Criticality"))
    penetration = models.IntegerField(default=0, verbose_name=_("Penetration"))
    dependency = models.IntegerField(default=0, verbose_name=_("Dependency"))
    maturity = models.IntegerField(default=0, verbose_name=_("Maturity"))
    trust = models.IntegerField(default=0, verbose_name=_("Trust"))
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
    )
    compliance_assessment = models.ForeignKey(
        ComplianceAssessment, on_delete=models.SET_NULL, blank=True, null=True
    )
    evidence = models.ForeignKey(
        Evidence, on_delete=models.SET_NULL, blank=True, null=True
    )

    class Meta:
        verbose_name = _("Entity assessment")
        verbose_name_plural = _("Entity assessments")


class Representative(AbstractBaseModel):
    """
    This represents a person that is linked to an entity (typically an employee),
    and that is relevant for the main entity, like a contact person for an assessment
    """

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

    fields_to_check = ["name"]


class Solution(NameDescriptionMixin):
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
    )
    ref_id = models.CharField(max_length=255, blank=True)
    criticality = models.IntegerField(default=0, verbose_name=_("Criticality"))

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Solution")
        verbose_name_plural = _("Solutions")


class Product(NameDescriptionMixin):
    """
    Product offered in a solution
    """

    solution = models.ForeignKey(
        Solution,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name=_("Solution"),
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
