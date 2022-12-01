from ast import Dict
from typing import Any, Iterable, Optional
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
    internal_reference = models.CharField(max_length=100,
                                   null=True, blank=True, verbose_name=_("Internal reference"))
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, verbose_name=_("Domain"))
    lc_status = models.CharField(max_length=20, default='in_design',
                                 choices=PRJ_LC_STATUS, verbose_name=_("Status"))

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

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

    def clean(self):
        content_type = self.type
        parent_asset = self.parent_asset
        field_errors = {}
        for field in self._meta.fields:
            if field.name != 'id' and field.name != 'created_at' and field.name != 'is_published':
                field_errors[field.name] = []
        if content_type == Asset.Type.SUPPORT and parent_asset is None:
            field_errors['parent_asset'].append(ValidationError(_('A support asset must have a parent asset.')))
        if content_type == Asset.Type.PRIMARY and parent_asset is not None:
            field_errors['parent_asset'].append(ValidationError(_('A primary asset cannot have a parent asset.')))
        if self.parent_asset == self:
            field_errors['parent_asset'].append(ValidationError(_('An asset cannot be its own parent.')))
        if not self.validate_tree():
            field_errors['parent_asset'].append(ValidationError(_('The asset tree is not valid. Please check for cycles.')))
        super().clean()
        for e in field_errors:
            if len(field_errors[e]) > 0:
                raise ValidationError(field_errors)

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

    def get_sub_assets(self):
        """
        Returns all the assets downstream of the current asset by running a breadth-first search.
        """
        visited = set()
        stack = [self]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            for child in Asset.objects.filter(parent_asset=node):
                stack.append(child)
        visited.remove(self)
        return visited

    def validate_tree(self) -> bool:
        """
        Validates the tree of the current asset by running a breadth-first search to check for cycles.
        """
        visited = set()
        stack = [self]
        while stack:
            node = stack.pop()
            if node in visited:
                return False
            visited.add(node)
            if node.parent_asset is not None:
                stack.append(node.parent_asset)
        return True

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
