from typing import Iterable, Optional
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from iam.models import Folder, FolderMixin
from core.base_models import AbstractBaseModel


class Project(AbstractBaseModel):
    PRJ_LC_STATUS = [
        ('undefined', _('--')),
        ('in_design', _('Design')),
        ('in_dev', _('Development')),
        ('in_prod', _('Production')),
        ('eol', _('End Of Life')),
        ('dropped', _('Dropped')),

    ]
    internal_id = models.CharField(max_length=100, help_text=_("If an internal reference applies"),
                                   null=True, blank=True, verbose_name=_("Internal ID"))
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, verbose_name=_("Domain"))
    lc_status = models.CharField(max_length=20, default='in_design',
                                 choices=PRJ_LC_STATUS, verbose_name=_("Status"))

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def description(self):
        return self.folder.description
    description.short_description = _("Description")

    def __str__(self):
        return self.name


class Threat(AbstractBaseModel, FolderMixin):
    is_published = models.BooleanField(_('published'), default=True)

    class Meta:
        verbose_name = _("Threat")
        verbose_name_plural = _("Threats")

    def __str__(self):
        return self.name


class Asset(AbstractBaseModel, FolderMixin):
    class Type(models.TextChoices):
        """
        The type of the asset.

        An asset can either be a primary or a support asset.
        A support asset must be linked to another "parent" asset.
        """
        PRIMARY = 'PR', _('Primary')
        SUPPORT = 'SP', _('Support')

    business_value = models.TextField(
        blank=True, verbose_name=_('business value'))
    type = models.CharField(
        max_length=2, choices=Type.choices, default=Type.PRIMARY, verbose_name=_('type'))
    parent_asset = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, verbose_name=_('parent asset'))
    is_published = models.BooleanField(_('published'), default=True)

    class Meta:
        verbose_name_plural = _("Assets")
        verbose_name = _("Asset")

    def __str__(self) -> str:
        return str(self.name)

    def is_primary(self) -> bool:
        """
        Returns True if the asset is a primary asset.
        """
        return self.type == Asset.Type.PRIMARY

    def is_support(self) -> bool:
        """
        Returns True if the asset is a support asset.
        """
        return self.type == Asset.Type.SUPPORT

    def get_parent_asset(self) -> Optional['Asset']:
        """
        Returns the parent asset if the current asset is a support asset.
        """
        return self.parent_asset

    def get_sub_assets(self):
        """
        Returns all the sub assets.
        """
        return Asset.objects.filter(parent_asset=self)


class SecurityFunction(AbstractBaseModel, FolderMixin):
    provider = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Provider"))
    contact = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Contact"))
    is_published = models.BooleanField(_('published'), default=True)

    class Meta:
        verbose_name = _("Security function")
        verbose_name_plural = _("Security functions")

    def __str__(self):
        return self.name
