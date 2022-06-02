from django.db import models
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _


class ProjectsGroup(models.Model):
    name = models.CharField(max_length=200, default=_("<Group title>"), verbose_name=_("Name"))
    department = models.CharField(
        max_length=100, default=_("<Internal organization division>"), 
        blank=True, null=True, verbose_name=_("Department"))

    class Meta:
        verbose_name = _("Projects Group")
        verbose_name_plural = _("Projects Groups")

    def __str__(self):
        return self.name


class Project(models.Model):
    PRJ_LC_STATUS = [
        ('undefined', _('--')),
        ('in_design', _('In Design')),
        ('in_dev', _('In Dev')),
        ('in_prod', _('In Production')),
        ('eol', _('End Of Life')),
        ('dropped', _('Dropped')),

    ]
    name = models.CharField(max_length=200, default=_("<short project name>"), verbose_name=_("Project Name"))
    internal_id = models.CharField(max_length=100, default=_("<if an internal reference applies>"), 
        null=True, blank=True, verbose_name=_("Internal ID"))
    parent_group = models.ForeignKey(ProjectsGroup, on_delete=models.CASCADE, verbose_name=_("Parent domain"))
    lc_status = models.CharField(max_length=20, default='in_design', 
        choices=PRJ_LC_STATUS, verbose_name=_("Status"))
    summary = models.TextField(max_length=1000, blank=True, null=True, 
        default=_("<brief summary of the project>"),
        help_text=_("This summary is optional and will appear in the risk analysis for context"),
        verbose_name=_("Summary"))
    
    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def department(self):
        return self.parent_group.department
    department.short_description = _("Department")

    def __str__(self):
        return self.name


class ParentRisk(models.Model):
    title = models.CharField(max_length=200, default=_("<parent risk short title>"), verbose_name=_("Title"))

    class Meta:
        verbose_name = _("Threat")
        verbose_name_plural = _("Threats")

    def __str__(self):
        return self.title


class Asset(models.Model):
    ASSETS_TYPES_LIST = [
        ('undefined', _('--')),
        ('cs', _('control systems')),
        ('das', _('data acquisition systems')),
        ('ne', _('networking equipment')),
        ('hpvms', _('hardware platforms for virtual machines or storage')),
    ]
   

    name = models.CharField(max_length=200, verbose_name=_("name"))
    type = models.CharField(max_length=20, default='undefined', 
        choices=ASSETS_TYPES_LIST, verbose_name=_("type"))
    is_critical = models.BooleanField(verbose_name=_("critical"), default=False)

    class Meta:
        verbose_name = _("asset")
        verbose_name_plural = _("assets")

    def __str__(self):
        return self.name


class Solution(models.Model):
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    provider = models.CharField(max_length=200, blank=True, null=True, verbose_name=_("Provider"))
    contact = models.CharField(max_length=200, blank=True, null=True, verbose_name=_("Contact"))

    class Meta:
        verbose_name = _("Solution")
        verbose_name_plural = _("Solutions")

    def __str__(self):
        return self.name


class GroupExtra(models.Model):
    """
    Overwrites original Django Group.
    """

    def __str__(self):
        return "{}".format(self.group.name)

    group = models.OneToOneField('auth.Group', unique=True, on_delete=models.CASCADE)
    group_email = models.EmailField(max_length=70, blank=True, default="", 
        help_text=_("Group email for notifications"),
        verbose_name=_("Group email"))
    prj_groups = models.ManyToManyField(ProjectsGroup, blank=True, 
        verbose_name=_("Allowed Projects Groups"), 
        help_text=_("Project groups allowed for read access on the Portal. "))

