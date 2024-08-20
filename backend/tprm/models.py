from django.db import models
from django.utils.translation import gettext_lazy as _
from core.base_models import NameDescriptionMixin
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
