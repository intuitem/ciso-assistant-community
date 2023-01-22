import uuid
from django.db import models
from django.core.exceptions import ValidationError
from asf_rm import settings
from core.base_models import AbstractBaseModel
from iam.models import Folder, FolderMixin
from openpyxl import load_workbook
import pandas as pd
import json
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from datetime import date

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

class RiskMatrix(AbstractBaseModel, FolderMixin):
    json_definition = models.JSONField(verbose_name=_("JSON definition"), help_text=_("JSON definition of the matrix. \
        See the documentation for more information."), default=dict)

    def parse_json(self) -> dict:
        return json.loads(self.json_definition)

    def get_detailed_grid(self) -> list:
        matrix = self.parse_json()
        grid = []
        for row in matrix['grid']:
            grid.append([item for item in row])
        return grid


    def render_grid_as_colors(self):
        matrix = self.parse_json()
        grid = matrix['grid']
        res = [[matrix['risk'][i] for i in row] for row in grid]

        return res

    def __str__(self) -> str:
        return self.name


class Analysis(AbstractBaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    version = models.CharField(max_length=100, blank=True, null=True, default="0.1", verbose_name=_("Version"))
    auditor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Auditor"))
    is_draft = models.BooleanField(verbose_name=_("is a draft"), default=True)
    rating_matrix = models.ForeignKey(RiskMatrix, on_delete=models.PROTECT, help_text=_("WARNING! After choosing it, you will not be able to change it"), verbose_name=_("Rating matrix"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Analysis")
        verbose_name_plural = _("Analyses")

    def __str__(self) -> str:
        return f'{self.project.folder}/{self.project}/{self.name} - {self.version}'

    @property
    def path_display(self) -> str:
        return f'{self.project.folder}/{self.project}/{self.name} - {self.version}'

    def get_scenario_count(self) -> int:
        count = RiskScenario.objects.filter(analysis=self.id).count()
        scenario_count = count
        return scenario_count

    def quality_check(self) -> dict:

        errors_lst = list()
        warnings_lst = list()
        info_lst = list()
        # --- check on the risk analysis:
        if self.is_draft:
            info_lst.append({"msg": _("Risk analysis is still in Draft mode"), "obj_type": "Analysis", "object": self})
        if not self.auditor:
            info_lst.append({"msg": _("No auditor assigned to this risk analysis yet"), "obj_type": "Analysis", "object": self})
        if not self.riskscenario_set.all():
            warnings_lst.append({"msg": _("Analysis is empty. No risk scenario declared yet"), "obj_type": "Analysis", "object": self})
        # ---

        # --- checks on the risk scenarios
        for ri in self.riskscenario_set.all().order_by('id'):

            if ri.residual_level > ri.current_level:
                errors_lst.append({"msg": _("R#{} residual risk level is higher than the current one").format(ri.id), "obj_type": "RiskScenario", "object": ri})
            if ri.residual_proba > ri.current_proba:
                errors_lst.append({"msg": _("R#{} residual risk probability is higher than the current one").format(ri.id), "obj_type": "RiskScenario", "object": ri})
            if ri.residual_impact > ri.current_impact:
                errors_lst.append({"msg": _("R#{} residual risk impact is higher than the current one").format(ri.id), "obj_type": "RiskScenario", "object": ri})

            if ri.residual_level < ri.current_level or ri.residual_proba < ri.current_proba or ri.residual_impact < ri.current_impact:
                if ri.security_measures.count() == 0:
                    errors_lst.append(
                        {"msg": _("R#{}: residual risk level has been lowered without any specific measure").format(ri.id), "obj_type": "RiskScenario", "object": ri})

            if ri.treatment == 'accepted':
                if not ri.riskacceptance_set.exists():
                    warnings_lst.append({"msg": _("R#{} risk accepted but no risk acceptance attached").format(ri.id), "obj_type": "RiskScenario", "object": ri})
        # ---

        # --- checks on the security_measures
        for mtg in SecurityMeasure.objects.filter(riskscenario__analysis=self):
            if not mtg.eta:
                warnings_lst.append({"msg": _("M#{} does not have an ETA").format(mtg.id), "obj_type": "SecurityMeasure", "object": mtg})
            else:
                if date.today() > mtg.eta:
                    errors_lst.append(
                        {"msg": _("M#{} ETA is in the past now. Consider updating its status or the date").format(mtg.id), "obj_type": "SecurityMeasure", "object": mtg})
            if not mtg.effort:
                warnings_lst.append(
                    {"msg": _("M#{} does not have an estimated effort. This will help you for prioritization").format(mtg.id), "obj_type": "SecurityMeasure", "object": mtg})
            if not mtg.link:
                info_lst.append(
                    {"msg": _("M#{} does not have an external link attached. This will help you for follow-up").format(mtg.id), "obj_type": "SecurityMeasure", "object": mtg})

        # --- checks on the risk acceptances
        for ra in RiskAcceptance.objects.filter(risk_scenario__analysis=self):
            if date.today() > ra.expiry_date:
                errors_lst.append(
                    {"msg": _("R#{} has a risk acceptance that has expired. Consider updating the status or the date").format(ra.risk_scenario.id)})

        findings = {
            "errors": errors_lst,
            "warnings": warnings_lst,
            "info": info_lst,
            "count": len(errors_lst + warnings_lst + info_lst)
        }
        return findings

    # NOTE: if your save() method throws an exception, you might want to override the clean() method to prevent 
    # 500 errors when the form submitted. See https://docs.djangoproject.com/en/dev/ref/models/instances/#django.db.models.Model.clean

def risk_scoring(probability, impact, matrix: RiskMatrix) -> int:
    fields = json.loads(matrix.json_definition)
    risk_index = fields['grid'][probability][impact]
    return risk_index


class SecurityMeasure(AbstractBaseModel):
    MITIGATION_STATUS = [
        ('open', _('Open')),
        ('in_progress', _('In progress')),
        ('on_hold', _('On hold')),
        ('done', _('Done')),
    ]

    MITIGATION_TYPE = [
        ('n/a', _('N/A')),
        ('technical', _('Technical')),
        ('organizational', _('Organizational')),
    ]

    EFFORT = [
        ('S', _('Small')),
        ('M', _('Medium')),
        ('L', _('Large')),
        ('XL', _('Extra-Large')),
    ]

    MAP_EFFORT = {None: -1, 'S': 1, 'M': 2, 'L': 4, 'XL': 8}
    # todo: think about a smarter model for ranking

    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, verbose_name=_("Domain"))
    security_function = models.ForeignKey(SecurityFunction, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Security Function"))
    type = models.CharField(max_length=20, choices=MITIGATION_TYPE, default='n/a', verbose_name=_("Type"))
    status = models.CharField(max_length=20, choices=MITIGATION_STATUS, default='open', verbose_name=_("Status"))
    eta = models.DateField(blank=True, null=True, help_text=_("Estimated Time of Arrival"), verbose_name=_("ETA"))
    link = models.CharField(null=True, blank=True, max_length=1000,
                            help_text=_("External url for action follow-up (eg. Jira ticket)"),
                            verbose_name=_("Link"))
    effort = models.CharField(null=True, blank=True, max_length=2, choices=EFFORT,
                              help_text=_("Relative effort of the measure (using T-Shirt sizing)"),
                              verbose_name=_("Effort"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Security measure")
        verbose_name_plural = _("Security measures")

    def parent_project(self):
        pass

    def __str__(self):
        return self.name

    @property
    def mid(self):
        return f'M.{self.scoped_id(scope=SecurityMeasure.objects.filter(folder=self.folder))}'

    def get_ranking_score(self):
        if self.effort:
            value = 0
            for risk_scenario in self.riskscenario_set.all():
                current = risk_scenario.current_level
                residual = risk_scenario.residual_level
                if current >= 0 and residual >= 0:
                    value += (1 + current - residual)*(current + 1)
            return round(value/self.MAP_EFFORT[self.effort], 4)
        else:
            return 0

    @property
    def get_html_url(self):
        url = reverse('MP', args=(self.folder.id,))
        return f'<a class="" href="{url}"> <b>[MT-eta]</b> {self.folder.name}: {self.name} </a>'


class RiskScenario(AbstractBaseModel):
    TREATMENT_OPTIONS = [
        ('open', _('Open')),
        ('mitigated', _('Mitigated')),
        ('accepted', _('Accepted')),
        ('blocker', _('Show-stopper')),
        ('transferred', _('Transferred')),
    ]

    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE, verbose_name=_("Analysis"))
    assets = models.ManyToManyField(Asset, verbose_name=_("Assets"), blank=True, help_text=_("Assets impacted by the risk scenario"))
    security_measures = models.ManyToManyField(SecurityMeasure, verbose_name=_("Security measures"), blank=True)
    threat = models.ForeignKey(Threat, on_delete=models.CASCADE, verbose_name=_("Threat"))
    existing_measures = models.TextField(max_length=2000,
                                         help_text=_("The existing security measures to manage this risk. Edit the risk scenario to add extra security measures."),
                                         verbose_name=_("Existing measures"), blank=True)

    # current
    current_proba = models.SmallIntegerField(default=-1, verbose_name=_("Current probability"))
    current_impact = models.SmallIntegerField(default=-1, verbose_name=_("Current impact"))
    current_level = models.SmallIntegerField(default=-1, verbose_name=_("Current level"),
                                     help_text=_('The risk level given the current measures. Automatically updated on Save, based on the chosen matrix'))

    # residual
    residual_proba = models.SmallIntegerField(default=-1, verbose_name=_("Residual probability"))
    residual_impact = models.SmallIntegerField(default=-1, verbose_name=_("Residual impact"))
    residual_level = models.SmallIntegerField(default=-1, verbose_name=_("Residual level"),
                                      help_text=_('The risk level when all the extra measures are done. Automatically updated on Save, based on the chosen matrix'))

    treatment = models.CharField(max_length=20, choices=TREATMENT_OPTIONS, default='open',
                                 verbose_name=_("Treatment status"))

    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    comments = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Comments"))

    class Meta:
        verbose_name = _("Risk scenario")
        verbose_name_plural = _("Risk scenarios")

    # def get_rating_options(self, field: str) -> list[tuple]:
    #     matrix = self.analysis.rating_matrix.parse_json()
    #     return [(k, v) for k, v in matrix.fields[field].items()]
        
    def parent_project(self):
        return self.analysis.project
    parent_project.short_description = _("Parent project")

    def get_matrix(self):
        return self.analysis.rating_matrix.parse_json()

    def get_current_risk(self):
        if self.current_level < 0:
            return {'abbreviation': '--', 'name': '--', 'description': 'not rated', 'hexcolor': '#A9A9A9'}
        matrix = self.get_matrix()
        return matrix['risk'][self.current_level]

    def get_current_impact(self):
        if self.current_impact < 0:
            return {'abbreviation': '--', 'name': '--', 'description': 'not rated'}
        matrix = self.get_matrix()
        return matrix['impact'][self.current_impact]

    def get_current_proba(self):
        if self.current_proba < 0:
            return {'abbreviation': '--', 'name': '--', 'description': 'not rated'}
        matrix = self.get_matrix()
        return matrix['probability'][self.current_proba]

    def get_residual_risk(self):
        if self.residual_level < 0:
            return {'abbreviation': '--', 'name': '--', 'description': 'not rated', 'hexcolor': '#A9A9A9'}
        matrix = self.get_matrix()
        return matrix['risk'][self.residual_level]

    def get_residual_impact(self):
        if self.residual_impact < 0:
            return {'abbreviation': '--', 'name': '--', 'description': 'not rated'}
        matrix = self.get_matrix()
        return matrix['impact'][self.residual_impact]

    def get_residual_proba(self):
        if self.residual_proba < 0:
            return {'abbreviation': '--', 'name': '--', 'description': 'not rated'}
        matrix = self.get_matrix()
        return matrix['probability'][self.residual_proba]

    def __str__(self):
        return str(self.parent_project()) + ': ' + str(self.name)

    @property
    def rid(self):
        return f'R.{self.scoped_id(scope=RiskScenario.objects.filter(analysis=self.analysis))}'

    def save(self, *args, **kwargs):
        if self.current_proba >= 0 and self.current_impact >= 0:
            self.current_level = risk_scoring(self.current_proba, self.current_impact, self.analysis.rating_matrix)
        else:
            self.current_level = -1
        if self.residual_proba >= 0 and self.residual_impact >= 0:
            self.residual_level = risk_scoring(self.residual_proba, self.residual_impact, self.analysis.rating_matrix)
        else:
            self.residual_level = -1
        super(RiskScenario, self).save(*args, **kwargs)


class RiskAcceptance(models.Model):
    ACCEPTANCE_TYPE = [
        ('temporary', _('Temporary')),
        ('permanent', _('Permanent')),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    risk_scenario = models.ForeignKey(RiskScenario, on_delete=models.CASCADE, verbose_name=_("Risk scenario"))
    validator = models.CharField(max_length=200, help_text=_("Risk owner and validator identity"), verbose_name=_("Validator"))
    type = models.CharField(max_length=20, choices=ACCEPTANCE_TYPE, default='temporary', verbose_name=_("Type"))
    expiry_date = models.DateField(help_text=_("If temporary, specify when the risk acceptance will no longer apply"),
                                   blank=True, null=True, verbose_name=_("Expiry date"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    comments = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Comments"))

    class Meta:
        verbose_name = _("Risk acceptance")
        verbose_name_plural = _("Risk acceptances")

    def __str__(self):
        return f"[{self.type}] {self.risk_scenario}"

    @property
    def get_html_url(self):
        url = reverse('RA', args=(self.risk_scenario.analysis.id,))
        return f'<a class="" href="{url}"> <b>[RA-exp]</b> {self.risk_scenario} </a>'
# you can consider nested inlines at some points


