from typing import Iterable, Optional
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from iam.models import Folder


class Project(models.Model):
    PRJ_LC_STATUS = [
        ('undefined', _('--')),
        ('in_design', _('Design')),
        ('in_dev', _('Development')),
        ('in_prod', _('Production')),
        ('eol', _('End Of Life')),
        ('dropped', _('Dropped')),

    ]
    name = models.CharField(max_length=200, default=_(
        "<short project name>"), verbose_name=_("Project Name"))
    internal_id = models.CharField(max_length=100, default=_("<if an internal reference applies>"),
                                   null=True, blank=True, verbose_name=_("Internal ID"))
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, verbose_name=_("Domain"))
    lc_status = models.CharField(max_length=20, default='in_design',
                                 choices=PRJ_LC_STATUS, verbose_name=_("Status"))
    summary = models.TextField(max_length=1000, blank=True, null=True,
                               default=_("<brief summary of the project>"),
                               help_text=_(
                                   "This summary is optional and will appear in the risk analysis for context"),
                               verbose_name=_("Summary"))

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def description(self):
        return self.folder.description
    description.short_description = _("Description")

    def __str__(self):
        return self.name


class Threat(models.Model):
    title = models.CharField(max_length=200, default=_(
        "<threat short title>"), verbose_name=_("Title"))
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE)
    is_published = models.BooleanField(_('published'), default=True)

    class Meta:
        verbose_name = _("Threat")
        verbose_name_plural = _("Threats")

    def __str__(self):
        return self.title


class Asset(models.Model):
    class Type(models.TextChoices):
        """
        The type of the asset.

        An asset can either be a primary or a support asset.
        A support asset must be linked to another "parent" asset.
        """
        PRIMARY = 'PR', _('Primary')
        SUPPORT = 'SP', _('Support')

    name = models.CharField(max_length=100, verbose_name=_('name'))
    business_value = models.TextField(
        blank=True, verbose_name=_('business value'))
    comments = models.TextField(blank=True, verbose_name=_('comments'))
    type = models.CharField(
        max_length=2, choices=Type.choices, default=Type.PRIMARY, verbose_name=_('type'))
    parent_asset = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, verbose_name=_('parent asset'))
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE)
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


class SecurityFunction(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    provider = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Provider"))
    contact = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Contact"))
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE)
    is_published = models.BooleanField(_('published'), default=True)

    class Meta:
        verbose_name = _("Security function")
        verbose_name_plural = _("Security functions")

    def __str__(self):
        return self.name
