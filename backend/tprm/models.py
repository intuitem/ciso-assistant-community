from django.db import models
from django.utils.translation import gettext_lazy as _
from core.base_models import NameDescriptionMixin, AbstractBaseModel
from iam.models import FolderMixin, PublishInRootFolderMixin


class Entity(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    """
    An entity represents a legal entity, a corporate body, an administrative body, an association
    """
    
    mission = models.TextField(blank=True, null=True)
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
    
    entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="solutions",
        verbose_name=_("Entity"),
    )
    ref_id = models.CharField(max_length=255, blank=True)
    criticality = models.IntegerField(
        default=0,
        verbose_name=_("Criticality")
    )
    
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