from django.db import models
from django.contrib.auth.models import User
from general.models import *
from asf_rm.settings import ARM_SETTINGS
from openpyxl import load_workbook
import pandas as pd
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from datetime import date


class Analysis(models.Model):
    RATING_METHODS = [
        ('default', _('Balanced (default)')),
        ('critical', _('Critical (FAIR-based)')),
        ('custom', _('Custom (adjusted)')),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    version = models.CharField(max_length=100, blank=True, null=True, default="0.1", verbose_name=_("Version"))
    auditor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Auditor"))
    is_draft = models.BooleanField(verbose_name=_("is a draft"), default=True)
    rating_matrix = models.CharField(choices=RATING_METHODS, default='default', max_length=20, verbose_name=_("Rating matrix"))

    comments = models.TextField(max_length=1000, blank=True, null=True,
                                verbose_name=_("Comments"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Analysis")
        verbose_name_plural = _("Analyses")

    def __str__(self):
        return 'RA-' + str(self.id) + ': ' + str(self.project) + ', version ' + str(self.version)

    def save(self, *args, **kwargs):
        for ri in self.riskinstance_set.all():
            ri.save()
        super(Analysis, self).save(*args, **kwargs)

    def quality_check(self) -> dict:

        ri_value = {'VL': 1, 'L': 2, 'M': 3, 'H': 4, 'VH': 5}
        errors_lst = list()
        warnings_lst = list()
        info_lst = list()
        # --- check on the Risk Analysis:
        if self.is_draft:
            info_lst.append({"msg": _("Risk Analysis is still in Draft mode"), "obj_type": "Analysis", "object": self})
        if not self.auditor:
            info_lst.append({"msg": _("No auditor assigned to this risk analysis yet"), "obj_type": "Analysis", "object": self})
        if not self.riskinstance_set.all():
            warnings_lst.append({"msg": _("Analysis is empty. No risk scenario declared yet"), "obj_type": "Analysis", "object": self})
        # ---

        # --- checks on the risk instances
        for ri in self.riskinstance_set.all().order_by('id'):

            if ri_value[ri.residual_level] > ri_value[ri.current_level]:
                errors_lst.append({"msg": _("R#{} residual risk level is higher than the current one").format(ri.id), "obj_type": "RiskInstance", "object": ri})
            if ri_value[ri.residual_proba] > ri_value[ri.current_proba]:
                errors_lst.append({"msg": _("R#{} residual risk probability is higher than the current one").format(ri.id), "obj_type": "RiskInstance", "object": ri})
            if ri_value[ri.residual_impact] > ri_value[ri.current_impact]:
                errors_lst.append({"msg": _("R#{} residual risk impact is higher than the current one").format(ri.id), "obj_type": "RiskInstance", "object": ri})

            if ri_value[ri.residual_level] < ri_value[ri.current_level] or ri_value[ri.residual_proba] < ri_value[
                ri.current_proba] or ri_value[ri.residual_impact] < ri_value[ri.current_impact]:
                if ri.associated_mitigations() == 0:
                    errors_lst.append(
                        {"msg": _("R#{}: residual risk level has been lowered without any specific mitigation").format(ri.id), "obj_type": "RiskInstance", "object": ri})

            if ri.treatment == 'accepted':
                if not ri.riskacceptance_set.exists():
                    warnings_lst.append({"msg": _("R#{} risk accepted but no risk acceptance attached").format(ri.id), "obj_type": "RiskInstance", "object": ri})
        # ---

        # --- checks on the mitigations
        for mtg in Mitigation.objects.filter(risk_instance__analysis=self):
            if not mtg.eta:
                warnings_lst.append({"msg": _("M#{} does not have an ETA").format(mtg.id), "obj_type": "Mitigation", "object": mtg})
            else:
                if date.today() > mtg.eta:
                    errors_lst.append(
                        {"msg": _("M#{} ETA is in the past now. Consider updating its status or the date").format(mtg.id), "obj_type": "Mitigation", "object": mtg})
            if not mtg.effort:
                warnings_lst.append(
                    {"msg": _("M#{} does not have an estimated effort. This will help you for prioritization").format(mtg.id), "obj_type": "Mitigation", "object": mtg})
            if not mtg.link:
                info_lst.append(
                    {"msg": _("M#{} does not have an external link attached. This will help you for follow-up").format(mtg.id), "obj_type": "Mitigation", "object": mtg})

        # --- checks on the risk acceptances
        for ra in RiskAcceptance.objects.filter(risk_instance__analysis=self):
            if date.today() > ra.expiry_date:
                errors_lst.append(
                    {"msg": _("R#{} has a risk acceptance that has expired. Consider updating the status or the date").format(ra.risk_instance.id)})

        findings = {
            "errors": errors_lst,
            "warnings": warnings_lst,
            "info": info_lst,
            "count": len(errors_lst + warnings_lst + info_lst)
        }
        return findings


def risk_scoring(proba, impact, matrix):
    matrix_path = ARM_SETTINGS["MATRIX_PATH"]
    df = pd.read_excel(matrix_path, None)
    # None in read_excel allow to read all sheets, TODO move this elsewhere to avoid multiple IOs
    focus = df[matrix]
    return focus[(focus.proba == proba) & (focus.impact == impact)].level.values[0]


class RiskInstance(models.Model):
    TREATMENT_OPTIONS = [
        ('open', _('Open')),
        ('mitigated', _('Mitigated')),
        ('accepted', _('Accepted')),
        ('blocker', _('Show-stopper')),
    ]
    # 1 very low, 2 low, 3 medium, 4 high, 5 very high
    RATING_OPTIONS = [
        ('VL', _('Very Low')),
        ('L', _('Low')),
        ('M', _('Medium')),
        ('H', _('High')),
        ('VH', _('Very High')),
    ]

    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE, verbose_name=_("Analysis_bo"))
    parent_risk = models.ForeignKey(ParentRisk, on_delete=models.CASCADE, verbose_name=_("Threat"))
    title = models.CharField(max_length=200, default=_("<risk scenario short title>"), verbose_name=_("Title"))
    scenario = models.TextField(max_length=2000, default=_("<risk scenario and impact description>"), verbose_name=("Scenario"))
    existing_measures = models.TextField(max_length=2000,
                                         help_text=_("The existing measures to manage this risk. Edit the risk instance to add extra mitigations."),
                                         default=_("<we have solution A and Process B to handle this>"),
                                         verbose_name=_("Existing Measures"))

    # current
    current_proba = models.CharField(default='VL', max_length=2, choices=RATING_OPTIONS,
                                     verbose_name=_("Current Probability"))
    current_impact = models.CharField(default='VL', max_length=2, choices=RATING_OPTIONS, verbose_name=_("Current Impact"))
    current_level = models.CharField(default='VL', max_length=2, choices=RATING_OPTIONS, verbose_name=_("Current Level"),
                                     help_text=_('The risk level given the current measures. Automatically updated on Save, based on the chosen matrix'))

    # residual
    residual_proba = models.CharField(default='VL', max_length=2, choices=RATING_OPTIONS,
                                      verbose_name=_("Residual Probability"))
    residual_impact = models.CharField(default='VL', max_length=2, choices=RATING_OPTIONS, verbose_name=_("Residual Impact"))
    residual_level = models.CharField(default='VL', max_length=2, choices=RATING_OPTIONS,
                                      help_text=_('The risk level when all the extra mitigations are done. Automatically updated on Save, based on the chosen matrix'),
                                      verbose_name=_("Residual Level"))

    treatment = models.CharField(max_length=20, choices=TREATMENT_OPTIONS, default='open',
                                 verbose_name=_("Treatment status"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    comments = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Comments"))

    class Meta:
        verbose_name = _("Risk Instance")
        verbose_name_plural = _("Risk Instances")

    def parent_project(self):
        return self.analysis.project
    parent_project.short_description = _("Parent Project")

    def associated_mitigations(self):
        return self.mitigation_set.count()

    def __str__(self):
        return str(self.parent_project()) + ': ' + str(self.title)

    def rid(self):
        return 'R.' + str(self.id)

    def save(self, *args, **kwargs):
        self.current_level = risk_scoring(self.current_proba, self.current_impact, self.analysis.rating_matrix)
        self.residual_level = risk_scoring(self.residual_proba, self.residual_impact, self.analysis.rating_matrix)
        super(RiskInstance, self).save(*args, **kwargs)


class Mitigation(models.Model):
    MITIGATION_STATUS = [
        ('open', _('Open')),
        ('in_progress', _('In Progress')),
        ('on_hold', _('On Hold')),
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

    MAP_EFFORT = {None: -1, 'S': 1, 'M': 2, 'L': 3, 'XL': 4}
    MAP_RISK_LEVEL = {'VL': 1, 'L': 2, 'M': 3, 'H': 4, 'VH': 5}

    risk_instance = models.ForeignKey(RiskInstance, on_delete=models.CASCADE, verbose_name=_("Risk instance"))
    solution = models.ForeignKey(Solution, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Solution"))

    title = models.CharField(max_length=200, default=_("<short title for the mitigation>"), verbose_name=_("Title"))
    description = models.TextField(max_length=500, blank=True, null=True, verbose_name=_("Description"))
    type = models.CharField(max_length=20, choices=MITIGATION_TYPE, default='n/a', verbose_name=_("Type"))
    status = models.CharField(max_length=20, choices=MITIGATION_STATUS, default='open', verbose_name=_("Status"))
    eta = models.DateField(blank=True, null=True, help_text=_("Estimated Time of Arrival"), verbose_name=_("ETA"))
    link = models.CharField(null=True, blank=True, max_length=1000,
                            help_text=_("External url for action follow-up (eg. Jira ticket)"),
                            verbose_name=_("Link"))
    effort = models.CharField(null=True, blank=True, max_length=2, choices=EFFORT,
                              help_text=_("Relative effort of the mitigation (using T-Shirt sizing)"),
                              verbose_name=_("Effort"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Mitigation")
        verbose_name_plural = _("Mitigations")

    def parent_project(self):
        return self.risk_instance.parent_project()
    parent_project.short_description = _("Parent Project")

    def __str__(self):
        return self.title

    def get_ranking_score(self):
        if self.effort:
            return round(self.MAP_RISK_LEVEL[self.risk_instance.current_level]/self.MAP_EFFORT[self.effort], 4)
        else:
            return 0

    @property
    def get_html_url(self):
        url = reverse('MP', args=(self.risk_instance.analysis.id,))
        return f'<a class="" href="{url}"> <b>[MT-eta]</b> {self.risk_instance.analysis.project.name}: {self.title} </a>'


class RiskAcceptance(models.Model):
    ACCEPTANCE_TYPE = [
        ('temporary', _('Temporary')),
        ('permanent', _('Permanent')),
    ]
    risk_instance = models.ForeignKey(RiskInstance, on_delete=models.CASCADE, verbose_name=_("Risk instance"))
    validator = models.CharField(max_length=200, default=_("<Risk owner and validator identity>"), verbose_name=_("Validator"))
    type = models.CharField(max_length=20, choices=ACCEPTANCE_TYPE, default='temporary', verbose_name=_("Type"))
    expiry_date = models.DateField(help_text=_("If temporary, specify when the risk acceptance will no longer apply"),
                                   blank=True, null=True, verbose_name=_("Expiry date"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    comments = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Comments"))

    class Meta:
        verbose_name = _("Risk Acceptance")
        verbose_name_plural = _("Risk Acceptances")

    def __str__(self):
        return f"[{self.type}] {self.risk_instance}"

    @property
    def get_html_url(self):
        url = reverse('RA', args=(self.risk_instance.analysis.id,))
        return f'<a class="" href="{url}"> <b>[RA-exp]</b> {self.risk_instance} </a>'
# you can consider nested inlines at some points
