from uuid import UUID
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from django.http import HttpResponse
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.db.models.query_utils import Q
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes

from core.models import Analysis, RiskScenario, SecurityMeasure, RiskMatrix
from core.models import Project
from iam.models import Folder, RoleAssignment, User

from django.contrib.auth.views import LoginView
from .forms import LoginForm

from django.db.models import Q

from django.utils.translation import gettext_lazy as _

from .helpers import *

from django.template.loader import render_to_string
from weasyprint import HTML, CSS
import logging
import csv
import time, random

from typing import Optional, Any
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView, CreateView, DeleteView, DetailView
from django.http import HttpResponse
from django.forms.models import model_to_dict
from django.template import loader
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from datetime import date
from django.contrib import messages
from core.utils import RoleCodename, UserGroupCodename
from iam.models import UserGroup, Role, RoleAssignment
from django.contrib.auth.views import PasswordChangeView
from django.views.generic.edit import FormView
from core.models import Analysis, RiskScenario, SecurityMeasure, RiskAcceptance
from iam.forms import *
from core.forms import *
from .filters import *

from core.helpers import get_counters, risks_count_per_level, security_measure_per_status, measures_to_review, acceptances_to_review
from django.contrib.auth import get_user_model

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from asf_rm.settings import RECAPTCHA_PUBLIC_KEY
if RECAPTCHA_PUBLIC_KEY:
    from captcha.fields import ReCaptchaField

from datetime import datetime, timedelta
import re

import json

User = get_user_model()

MAX_USERS = 20

class BaseContextMixin:

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['change_usergroup'] = RoleAssignment.has_permission(
            self.request.user, "change_usergroup")
        context['view_user'] = RoleAssignment.has_permission(
            self.request.user, "view_user")
        context['exceeded_users'] = (MAX_USERS - User.objects.all().count()) < 0
        return context


class GenericDetailView(BaseContextMixin, DetailView):
    template_name = 'generic/detail.html'
    context_object_name = 'object'

    exclude = ['id', 'is_published']

    field_order = []

    def get_object_data(self):
        object_data = model_to_dict(self.object)

        # sort fields according to field_order
        # put first fields in field_order, then the rest
        if self.field_order:
            object_data = {
                k: object_data[k] for k in self.field_order if k in object_data} | object_data

        for key in list(object_data.keys()):
            if key in self.exclude:
                object_data.pop(key)
                continue
            # replace uuids with their respective objects
            if object_data[key] and isinstance(object_data[key], UUID):
                object_data[key] = getattr(self.object, key)
            # get proper value display for choice fields
            if choices := self.get_object()._meta.get_field(key).choices:
                if key in object_data and object_data[key] in dict(choices):
                    object_data[key] = dict(choices)[object_data[key]]
            # convert all fields to iterables for template rendering
            if not isinstance(object_data[key], list):
                object_data[key] = [object_data[key]]
            # replace field names with their respective verbose names
            object_data[self.object._meta.get_field(
                key).verbose_name] = object_data.pop(key)

        return object_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, self.model)
        context['change'] = self.object.id in object_ids_change
        context['delete'] = self.object.id in object_ids_delete
        if self.model is User:
            # NOTE: using has_permission() because get_accessible_objects() doesn't handle this object_type moreover there isn't scope
            context['change'] = RoleAssignment.has_permission(self.request.user, 'change_user')
            context['delete'] = RoleAssignment.has_permission(self.request.user, 'delete_user')
        context['data'] = self.get_object_data()
        context['crumbs'] = {self.model.__name__.lower() + "-list": self.model._meta.verbose_name_plural}

        return context


class RiskScenarioDetailView(GenericDetailView):
    model = RiskScenario
    exclude = ['id', 'current_proba', 'residual_proba', 'current_impact',
               'residual_impact', 'current_level', 'residual_level']

    def get_object_data(self):
        object_data = super().get_object_data()

        _data = {}

        _data['current_proba'] = self.object.get_current_proba()['name']
        _data['residual_proba'] = self.object.get_residual_proba()['name']
        _data['current_impact'] = self.object.get_current_impact()['name']
        _data['residual_impact'] = self.object.get_residual_impact()['name']
        _data['current_level'] = self.object.get_current_risk()['name']
        _data['residual_level'] = self.object.get_residual_risk()['name']

        for key in list(_data.keys()):
            object_data[self.object._meta.get_field(
                key).verbose_name] = [_data.pop(key)]

        return object_data


class SecurityMeasureDetailView(GenericDetailView):
    model = SecurityMeasure


class RiskAcceptanceDetailView(GenericDetailView):
    model = RiskAcceptance
    template_name = "core/detail/riskacceptance_detail.html"
    exclude = ['']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.object = get_object_or_404(RiskAcceptance, id=self.kwargs['pk'])
        if self.object.state in ('created', 'submitted'):
            self.exclude = ['accepted_date', 'revoked_date', 'rejected_date']
        elif self.object.state == 'accepted':
            self.exclude = ['revoked_date', 'rejected_date']
        elif self.object.state == 'rejected':
            self.exclude = ['accepted_date', 'revoked_date']
        elif self.object.state == 'revoked':
            self.exclude = ['rejected_date']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object = get_object_or_404(RiskAcceptance, id=self.kwargs['pk'])
        if self.object.state == 'submitted':
            context['risk_acceptance_need_validation'] = (
                self.request.user == self.object.validator)
        if self.object.state == 'accepted':
            context['risk_acceptance_accepted'] = True
        if self.object.state == 'rejected':
            context['risk_acceptance_rejected'] = True
        if self.object.state == 'revoked':
            context['risk_acceptance_revoked'] = True
        context['validate_riskacceptance'] = RoleAssignment.is_access_allowed(user=self.request.user, 
                                            perm=Permission.objects.get(codename='validate_riskacceptance'), 
                                            folder=self.object.folder)
        return context

    def post(self, request, *args, **kwargs):
        self.object = get_object_or_404(RiskAcceptance, id=self.kwargs['pk'])
        if RoleAssignment.is_access_allowed(user=self.request.user, 
                                            perm=Permission.objects.get(codename='validate_riskacceptance'), 
                                            folder=self.object.folder):
            if 'accepted' in request.POST:
                self.object.set_state('accepted')
                messages.success(request, _("Risk acceptance: {} accepted with success!".format(self.object.name)))
            elif 'rejected' in request.POST:
                self.object.set_state('rejected')
                messages.success(request, _("Risk acceptance: {} rejected with success!".format(self.object.name)))
            elif 'revoked' in request.POST:
                self.object.set_state('revoked')
                messages.success(request, _("Risk acceptance: {} revoked with success!".format(self.object.name)))
            else:
                messages.error(request, "An internal error has occured.")
        else:
                messages.error(request, "Permission denied: you are not allowed to validate this risk acceptance.")
        return redirect("riskacceptance-detail", self.object.id)


class FolderDetailView(GenericDetailView):
    model = Folder
    exclude = ['id', 'content_type', 'builtin', "hide_public_asset",
               "hide_public_matrix", "hide_public_threat", "hide_public_security_function"]

    template_name = "core/detail/folder_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"folder-list": _("Projects domains")}
        context['projects'] = Project.objects.filter(folder=self.object)
        context['project_create_form'] = ProjectFormInherited(
            initial={'folder': self.object})
        return context


class ProjectDetailView(GenericDetailView):
    model = Project

    template_name = "core/detail/project_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"project-list": _("Projects")}
        context['analysis_create_form'] = RiskAnalysisCreateFormInherited(
            initial={'project': self.object})
        context['analyses'] = Analysis.objects.filter(project=self.object)
        context['no_matrix'] = (RiskMatrix.objects.all().count() - RiskMatrix.objects.filter(is_enabled=False).count()) < 1
        return context


class AssetDetailView(GenericDetailView):
    model = Asset


class ThreatDetailView(GenericDetailView):
    model = Threat


class SecurityFunctionDetailView(GenericDetailView):
    model = SecurityFunction


class UserDetailView(GenericDetailView):
    model = User

    exclude = ['id', 'password', 'first_login']


class AnalysisListView(BaseContextMixin, ListView):
    template_name = 'core/index.html'
    context_object_name = 'context'

    ordering = 'id'
    paginate_by = 10
    model = Analysis

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.first_login:
            messages.info(self.request, format_html(_(
                "Welcome to MIRA! 👋<br>Question or feedback? click <a class='text-blue-600 underline hover:text-blue-500' target='_blank' href='https://intuitem.com/contact/'>here</a>")))
            self.request.user.first_login = False
            self.request.user.save()
        if not UserGroup.get_user_groups(self.request.user):
            messages.warning(self.request, _(
                "Warning! You are not assigned to any group. Without a group you will not have access to any functionality. Please contact your administrator."))
        return context

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        return qs


class UserLogin(LoginView):
    template_name = 'registration/login.html'
    form_class = LoginForm


def password_reset_request(request):
    context = {}
    if request.method == "POST":
        now = datetime.now()
        password_reset_form = ResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(email=data)
            if associated_users and associated_users.exists():
                associated_user = associated_users[0]
                try:
                    if 'last_email_sent' in request.session:
                        last_sent_time = datetime.strptime(
                            request.session['last_email_sent'], '%Y-%m-%d %H:%M:%S')
                        elapsed_time = now - last_sent_time
                        # Vérifier si 30 secondes se sont écoulées depuis le dernier envoi de mail
                        if elapsed_time < timedelta(seconds=30):
                            # Si oui, retourner une réponse d'erreur
                            messages.error(
                                request, "Please wait before requesting another password reset.")
                            context["password_reset_form"] = password_reset_form
                            return render(request=request, template_name="registration/password_reset.html", context=context)
                    # Si tout est OK, envoyer l'email et enregistrer la date et l'heure actuelle dans la session
                    print("Sending reset mail to", data)
                    associated_user.mailing(email_template_name="registration/password_reset_email.txt", subject=_("Password Reset Requested"))
                    request.session['last_email_sent'] = now.strftime('%Y-%m-%d %H:%M:%S')
                except Exception as e:
                    messages.error(
                        request, 'An error has occured, please try later.')
                    print("Exception:", e)
                    password_reset_form = ResetForm()
                    context["password_reset_form"] = password_reset_form
                    return render(request=request, template_name="registration/password_reset.html", context=context)
            else:
                # wrong, but we won't tell the requester for security reasons
                time.sleep(random.random()*1.5)
                print("wrong email reset:", data)
            return redirect("/password_reset/done/")
        else:
            messages.error(request, "Invalid email or captcha.")
    password_reset_form = ResetForm()
    context["password_reset_form"] = password_reset_form
    return render(request=request, template_name="registration/password_reset.html", context=context)


class ResetPasswordConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    form_class = ResetConfirmForm


class FirstConnexionPasswordConfirmView(PasswordResetConfirmView):
    template_name = "registration/first_connexion_confirm.html"
    form_class = FirstConnexionConfirmForm


@method_decorator(login_required, name='dispatch')
class SecurityMeasurePlanView(UserPassesTestMixin, ListView):
    template_name = 'core/mp.html'
    context_object_name = 'context'

    ordering = 'id'
    model = RiskScenario

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskScenario)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        return qs

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


def build_ri_clusters(analysis: Analysis):
    matrix = analysis.rating_matrix.parse_json()
    grid = matrix['grid']
    matrix_current = [[set() for _ in range(len(grid[0]))]
                      for _ in range(len(grid))]
    matrix_residual = [[set() for _ in range(len(grid[0]))]
                       for _ in range(len(grid))]

    for ri in RiskScenario.objects.filter(analysis=analysis).order_by('created_at'):
        if ri.current_level >= 0:
            matrix_current[ri.current_proba][ri.current_impact].add(ri.rid)
        if ri.residual_level >= 0:
            matrix_residual[ri.residual_proba][ri.residual_impact].add(ri.rid)

    return {'current': matrix_current, 'residual': matrix_residual}


@method_decorator(login_required, name='dispatch')
class RiskAnalysisView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/ra.html'
    context_object_name = 'context'

    model = RiskScenario
    ordering = 'created_at'

    def get_queryset(self):
        self.analysis = get_object_or_404(Analysis, id=self.kwargs['analysis'])
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskScenario)
        qs = self.model.objects.filter(id__in=object_ids_view).filter(
            analysis=self.analysis).order_by(self.ordering)
        return qs

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # then Add in
        context['analysis'] = self.analysis
        context['ri_clusters'] = build_ri_clusters(self.analysis)
        context['scenarios'] = RiskScenario.objects.filter(
            analysis=self.analysis).order_by('created_at')
        context['matrix'] = self.analysis.rating_matrix
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="view_analysis"), folder=get_object_or_404(Analysis, id=self.kwargs['analysis']).project.folder)


@login_required
# analysis parameter is the id of the chosen Analysis
def generate_ra_pdf(request, analysis: Analysis):
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.objects.get(content_type=Folder.ContentType.ROOT), request.user, Analysis)
    if UUID(analysis) in object_ids_view:
        ra = get_object_or_404(Analysis, pk=analysis)
        context = RiskScenario.objects.filter(analysis=analysis).order_by('created_at')
        data = {'context': context, 'analysis': ra,
                'ri_clusters': build_ri_clusters(ra), 'matrix': ra.rating_matrix}
        html = render_to_string('core/ra_pdf.html', data)
        pdf_file = HTML(string=html).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'filename="RA-{ra.id}-{ra.project}-v-{ra.version}.pdf"'
        return response
    else:
        raise PermissionDenied()


@login_required
# analysis parameter is the id of the choosen Analysis
def generate_mp_pdf(request, analysis):
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.objects.get(content_type=Folder.ContentType.ROOT), request.user, Analysis)
    if UUID(analysis) in object_ids_view:
        ra = get_object_or_404(Analysis, pk=analysis)
        context = RiskScenario.objects.filter(analysis=analysis).order_by('created_at')
        data = {'context': context, 'analysis': ra}
        html = render_to_string('core/mp_pdf.html', data)
        pdf_file = HTML(string=html).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'filename="MP-{ra.id}-{ra.project}-v-{ra.version}.pdf"'
        return response
    else:
        raise PermissionDenied()


@method_decorator(login_required, name='dispatch')
class SearchResults(ListView):
    context_object_name = 'context'
    template_name = 'core/search_results.html'

    def get_queryset(self):
        query = self.request.GET.get('q')
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskScenario)
        ri_list = RiskScenario.objects.filter(Q(name__icontains=query) | Q(
            threat__name__icontains=query)).filter(id__in=object_ids_view)[:10]
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, SecurityMeasure)
        mtg_list = SecurityMeasure.objects.filter(Q(name__icontains=query) | Q(
            security_function__name__icontains=query)).filter(id__in=object_ids_view)[:10]
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)
        ra_list = Analysis.objects.filter(Q(name__icontains=query) | Q(project__name__icontains=query) | Q(
            project__folder__name__icontains=query) | Q(version__icontains=query)).filter(id__in=object_ids_view)[:10]
        return {"Analysis": ra_list, "RiskScenario": ri_list, "SecurityMeasure": mtg_list}


@method_decorator(login_required, name='dispatch')
class Browser(ListView):
    context_object_name = 'context'
    template_name = 'core/browser.html'

    map_rsk = {'0': "open", '1': "mitigated",
               '2': "accepted", '3': "blocker", '4': "transferred"}
    map_mtg = {'0': "open", '1': "in_progress", '2': "on_hold", '3': "done"}

    def get_queryset(self):

        rsk = self.request.GET.get('rsk')
        mtg = self.request.GET.get('mtg')
        if rsk:
            (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
                Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskScenario)
            return {"type": _("risk scenarios"), "filter": self.map_rsk[rsk], "items": RiskScenario.objects.filter(treatment=self.map_rsk[rsk]).filter(id__in=object_ids_view)}
        if mtg:
            (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
                Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, SecurityMeasure)
            return {"type": _("security measures"), "filter": self.map_mtg[mtg], "items": SecurityMeasure.objects.filter(status=self.map_mtg[mtg]).filter(id__in=object_ids_view)}


@login_required
def global_overview(request):
    template = 'core/overview.html'

    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.objects.get(content_type=Folder.ContentType.ROOT), request.user, SecurityMeasure)

    viewable_analyses = RoleAssignment.get_accessible_object_ids(
        Folder.objects.get(content_type=Folder.ContentType.ROOT), request.user, Analysis)[0]

    _ord_security_measures = SecurityMeasure.objects.filter(id__in=object_ids_view).exclude(status='done').order_by('eta')

    context = {
        "counters": get_counters(request.user),
        "risks_level": risks_count_per_level(request.user),
        "security_measure_status": security_measure_per_status(request.user),
        "measures_to_review": measures_to_review(request.user),
        "acceptances_to_review": acceptances_to_review(request.user),
        "today": date.today(),
        "agg_data": risk_status(request.user, Analysis.objects.filter(id__in=viewable_analyses)),
        "ord_security_measures": sorted(_ord_security_measures, key=lambda mtg: mtg.get_ranking_score(), reverse=True),
        "analyses": Analysis.objects.filter(id__in=viewable_analyses).order_by('created_at'),
        "colors": get_risk_color_ordered_list(request.user),
        "viewable_measures": object_ids_view,
        "updatable_measures": object_ids_change,
        "view_user": RoleAssignment.has_permission(request.user, "view_user"), # NOTE: Need to factorize with BaseContextMixin
        "exceeded_users": (MAX_USERS - User.objects.all().count()) < 0,
        "change_usergroup": RoleAssignment.has_permission(request.user, "change_usergroup"),
    }

    return render(request, template, context)


def compile_analysis_for_composer(user: User, analysis_list: list):
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.objects.get(content_type=Folder.ContentType.ROOT), user, Analysis)

    rc = risks_count_per_level(user, analysis_list)
    current_level = rc['current']
    residual_level = rc['residual']

    untreated = RiskScenario.objects.filter(analysis__in=analysis_list).exclude(
        treatment__in=['mitigated', 'accepted'])
    untreated_h_vh = RiskScenario.objects.filter(analysis__in=analysis_list).exclude(
        treatment__in=['mitigated', 'accepted']).filter(current_level__gte=2)
    accepted = RiskScenario.objects.filter(
        analysis__in=analysis_list).filter(treatment='accepted')

    values = list()
    labels = list()
    color_map = {"open": "#fac858", "in_progress": "#5470c6",
                 "on_hold": "#ee6666", "done": "#91cc75"}
    for st in SecurityMeasure.MITIGATION_STATUS:
        count = SecurityMeasure.objects.filter(status=st[0]).filter(
            riskscenario__analysis__in=analysis_list).count()
        v = {
            "value": count,
            "itemStyle": {"color": color_map[st[0]]}
        }
        values.append(v)
        labels.append(st[1])

    analysis_objects = list()

    for _ra in analysis_list:
        synth_table = list()
        _rc = risks_count_per_level(user=user, analyses=[_ra])
        length = len(_rc['current'])
        for i in range(length):
            count_c = _rc['current'][i]['value']
            count_r = _rc['residual'][i]['value']
            lvl = _rc['current'][i]['name']
            synth_table.append(
                {"lvl": lvl, "current": count_c, "residual": count_r})
        hvh_risks = RiskScenario.objects.filter(
            analysis__id=_ra).filter(current_level__gte=2)
        analysis_objects.append(
            {"analysis": get_object_or_404(
                Analysis, pk=_ra), "synth_table": synth_table, "hvh_risks": hvh_risks}
        )

    return {
        "analysis_objects": analysis_objects,
        "current_level": current_level,
        "residual_level": residual_level,
        "view_user": RoleAssignment.has_permission(user, "view_user"), # NOTE: Need to factorize with BaseContextMixin
        "exceeded_users": (MAX_USERS - User.objects.all().count()) < 0,
        "change_usergroup": RoleAssignment.has_permission(user, "change_usergroup"),
        "counters": {"untreated": untreated.count(), "untreated_h_vh": untreated_h_vh.count(), "accepted": accepted.count()},
        "riskscenarios": {"untreated": untreated, "untreated_h_vh": untreated_h_vh, "accepted": accepted},
        "security_measure_status": {"labels": labels, "values": values},
        "colors": get_risk_color_ordered_list(user),
    }


class ComposerListView(ListView):

    def get(self, request, *args, **kwargs):
        v = request.GET.get('analysis')
        if v:
            request_list = request.GET.getlist('analysis')[0]
            data = [item for item in request_list.split(',')]
            # debug print(f"got {len(data)} analysis in {data}")
            context = {
                "context": compile_analysis_for_composer(self.request.user, data),
                "view_user": RoleAssignment.has_permission(request.user, "view_user"), # NOTE: Need to factorize with BaseContextMixin
                "exceeded_users": (MAX_USERS - User.objects.all().count()) < 0,
                "change_usergroup": RoleAssignment.has_permission(request.user, "change_usergroup"),
            }
            return render(request, 'core/composer.html', context)
        else:
            (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
                Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)
            context = {'context': Analysis.objects.filter(
                id__in=object_ids_view)}
            return render(request, 'core/project_select.html', context)


def index(request):
    return HttpResponse("Hello, world. You're at the core index.")


@login_required
def export_risks_csv(request, analysis):
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.objects.get(content_type=Folder.ContentType.ROOT), request.user, Analysis)
    if UUID(analysis) in object_ids_view:
        ra = get_object_or_404(Analysis, pk=analysis)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="RA-{ra.id}-{ra.project}-v-{ra.version}.csv"'

        writer = csv.writer(response, delimiter=';')
        columns = ['rid', 'threat', 'name', 'scenario',
                   'existing_measures', 'current_level', 'measures', 'residual_level',
                   'treatment']
        writer.writerow(columns)

        for ri in ra.riskscenario_set.all().order_by('created_at'):
            security_measures = ''
            for mtg in ri.security_measures.all():
                security_measures += f"[{mtg.status}]{mtg.name} \n"
            row = [ri.rid, ri.threat, ri.name, ri.description,
                   ri.existing_measures, ri.get_current_risk()['name'],
                   security_measures, ri.get_residual_risk()[
                       'name'], ri.treatment,
                   ]
            writer.writerow(row)

        return response
    else:
        raise PermissionDenied()


@login_required
def export_mp_csv(request, analysis):
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.objects.get(content_type=Folder.ContentType.ROOT), request.user, Analysis)
    if UUID(analysis) in object_ids_view:
        ra = get_object_or_404(Analysis, pk=analysis)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="MP-{ra.id}-{ra.project}-v-{ra.version}.csv"'

        writer = csv.writer(response, delimiter=';')
        columns = ['risk_scenario',
                   'measure_id', 'measure_name', 'measure_desc', 'type', 'security_function', 'eta', 'effort', 'link', 'status',
                   ]
        writer.writerow(columns)
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), request.user, SecurityMeasure)
        for mtg in SecurityMeasure.objects.filter(id__in=object_ids_view).filter(riskscenario__analysis=analysis):
            risk_scenarios = []
            for rs in mtg.riskscenario_set.all():
                risk_scenarios.append(str(rs.rid) + ": " + rs.name)
            row = [risk_scenarios,
                   mtg.id, mtg.name, mtg.description, mtg.type, mtg.security_function, mtg.eta, mtg.effort, mtg.link, mtg.status,
                   ]
            writer.writerow(row)

        return response
    else:
        raise PermissionDenied()


def scoring_assistant(request):
    template = 'core/scoring.html'
    context = {}
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.objects.get(content_type=Folder.ContentType.ROOT), request.user, RiskMatrix)
    context['matrices'] = list(
        RiskMatrix.objects.all().values_list('json_definition', flat=True))
    context['change_usergroup'] = RoleAssignment.has_permission(
        request.user, "change_usergroup") # NOTE: Need to factorize with BaseContextMixin
    context['view_user'] = RoleAssignment.has_permission(
        request.user, "view_user")
    context['exceeded_users'] = (MAX_USERS - User.objects.all().count()) < 0
    return render(request, template, context)


def show_risk_matrix(request):
    template = 'core/risk_matrix.html'
    context = {}
    return render(request, template, context)


class ReviewView(BaseContextMixin, ListView):
    template_name = 'core/review.html'
    context_object_name = 'context'
    model = Analysis
    ordering = 'id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)
        return Analysis.objects.filter(id__in=object_ids_view)


class CreateViewModal(BaseContextMixin, CreateView):
    template_name: str = 'core/fallback_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        url_name = self.model.__name__.lower()
        if self.model.__name__.lower() == "folder":
            plural_name = _("Projects domains")
            name = "projects domain"
        elif self.model.__name__.lower() == "securityfunction":
            plural_name = _("Security functions")
            name = "security function"
        else:
            plural_name = self.model._meta.verbose_name_plural
            name = self.model.__name__.replace('Risk', 'Risk ').lower()        
        context["cancel_url"] = reverse_lazy(f'{url_name}-list')
        context["crumbs"] = {url_name + "-list": plural_name}
        context["object_type"] = _("Add" + " " + name)
        return context

    def get_success_url(self):
        return self.request.POST.get('next', reverse_lazy(f'{self.model.__name__.lower()}-list'))


class QuickStartView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/quick_start.html'
    context_object_name = 'quick-start'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects_domain_create_form'] = FolderUpdateForm
        context['project_create_form'] = ProjectForm
        context['analysis_create_form'] = RiskAnalysisCreateForm
        context['riskscenario_create_form'] = RiskScenarioCreateForm
        context['securitymeasure_create_form'] = SecurityMeasureCreateForm
        context['threat_create_form'] = ThreatCreateForm
        context['security_function_create_form'] = SecurityFunctionCreateForm
        context['asset_create_form'] = AssetForm(user=self.request.user)
        return context

    def get_queryset(self):
        return True

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class ProjectListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/project_list.html'
    context_object_name = 'projects'

    ordering = 'created_at'
    paginate_by = 10
    model = Project
    
    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Project)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        filtered_list = ProjectFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProjectFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['project_create_form'] = ProjectForm(user=self.request.user)
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Project)
        context['add_project'] = RoleAssignment.has_permission(
            self.request.user, 'add_project')
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class ProjectCreateView(UserPassesTestMixin, CreateView):
    model = Project
    template_name = 'core/project_create.html'
    context_object_name = 'project'
    form_class = ProjectForm

    def get_success_url(self) -> str:
        return reverse_lazy('project-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename='add_project'), folder=Folder.objects.get(id=self.request.POST['folder']))


class ProjectCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = Project
    context_object_name = 'project'
    form_class = ProjectForm

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename='add_project'), folder=Folder.objects.get(id=self.request.POST['folder']))


class ProjectUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Project
    template_name = 'core/project_update.html'
    context_object_name = 'project'
    form_class = ProjectForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analyses'] = Analysis.objects.filter(
            project=self.get_object()).order_by('is_draft', 'id')
        context['analysis_create_form'] = RiskAnalysisCreateFormInherited(
            initial={'project': get_object_or_404(Project, id=self.kwargs['pk']), 'auditor': self.request.user})
        context['crumbs'] = {'project-list': _('Projects')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('project-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename='change_project'), folder=self.get_object().folder)


class ProjectDeleteView(UserPassesTestMixin, DeleteView):
    model = Project
    success_url = reverse_lazy('project-list')
    template_name = 'snippets/project_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('project-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_project"))


class AssetListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/asset_list.html'
    context_object_name = 'assets'

    ordering = 'created_at'
    paginate_by = 10
    model = Asset

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Asset)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        filtered_list = AssetFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = AssetFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['asset_create_form'] = AssetForm(user=self.request.user)
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Asset)
        context['add_asset'] = RoleAssignment.has_permission(
            self.request.user, 'add_asset')
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class AssetCreateView(UserPassesTestMixin, CreateView):
    model = Asset
    template = 'snippets/asset_create.html'
    context_object_name = 'asset'
    form_class = AssetForm

    def get_success_url(self):
        return reverse_lazy('asset-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_asset"), folder=Folder.objects.get(id=self.request.POST['folder']))


class AssetCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = Asset
    context_object_name = 'asset'
    form_class = AssetForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_asset"), folder=Folder.objects.get(id=self.request.POST['folder']))


class AssetUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Asset
    context_object_name = 'asset'
    form_class = AssetForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crumbs'] = {'asset-list': _('Assets')}
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self) -> str:
        return reverse_lazy('asset-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_asset"))


class AssetDeleteView(UserPassesTestMixin, DeleteView):
    model = Asset
    success_url = reverse_lazy('asset-list')
    template_name = 'snippets/asset_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('asset-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_asset"))


class FolderListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/project_domain_list.html'
    context_object_name = 'domains'

    ordering = 'created_at'
    paginate_by = 10
    model = Folder

    def get_queryset(self):
        folders_list = RoleAssignment.get_accessible_folders(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Folder.ContentType.DOMAIN, codename="change_folder")
        qs = self.model.objects.filter(id__in=folders_list)
        filtered_list = ProjectsDomainFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProjectsDomainFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['projects_domain_create_form'] = FolderUpdateForm
        context['add_folder'] = RoleAssignment.has_permission(
            self.request.user, 'add_folder')
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Folder)
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class FolderCreateView(UserPassesTestMixin, CreateView):
    model = Folder
    template_name = 'core/pd_update.html'
    context_object_name = 'domain'
    form_class = FolderUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('folder-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_folder"))


class FolderCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = Folder
    context_object_name = 'domain'
    form_class = FolderUpdateForm

    def get_success_url(self) -> str:
        folder = Folder.objects.latest("created_at")
        auditors = UserGroup.objects.create(
            name=UserGroupCodename.AUDITOR, folder=folder, builtin=True)
        validators = UserGroup.objects.create(
            name=UserGroupCodename.VALIDATOR, folder=folder, builtin=True)
        analysts = UserGroup.objects.create(
            name=UserGroupCodename.ANALYST, folder=folder, builtin=True)
        managers = UserGroup.objects.create(
            name=UserGroupCodename.DOMAIN_MANAGER, folder=folder, builtin=True)
        ra1 = RoleAssignment.objects.create(user_group=auditors, role=Role.objects.get(
            name=RoleCodename.AUDITOR), builtin=True, folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
        ra1.perimeter_folders.add(folder)
        ra2 = RoleAssignment.objects.create(user_group=validators, role=Role.objects.get(
            name=RoleCodename.VALIDATOR), builtin=True, folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
        ra2.perimeter_folders.add(folder)
        ra3 = RoleAssignment.objects.create(user_group=analysts, role=Role.objects.get(
            name=RoleCodename.ANALYST), builtin=True, folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
        ra3.perimeter_folders.add(folder)
        ra4 = RoleAssignment.objects.create(user_group=managers, role=Role.objects.get(
            name=RoleCodename.DOMAIN_MANAGER), builtin=True, folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
        ra4.perimeter_folders.add(folder)
        messages.info(self.request, _(
            'User groups {} - Auditors, {} - Validators, {} - Analysts and {} - Domain Managers were created').format(folder.name, folder.name, folder.name, folder.name))
        return self.request.POST.get('next', reverse_lazy('folder-list'))

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_folder"))


class FolderUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Folder
    template_name = 'core/pd_update.html'
    context_object_name = 'domain'
    form_class = FolderUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(folder=self.get_object())
        context['crumbs'] = {'folder-list': _('Projects domains')}
        context['project_create_form'] = ProjectFormInherited(
            initial={'folder': get_object_or_404(Folder, id=self.kwargs['pk'])})
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('folder-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_folder"), folder=self.get_object())


class FolderDeleteView(UserPassesTestMixin, DeleteView):
    model = Folder
    success_url = reverse_lazy('folder-list')
    template_name = 'snippets/projects_domain_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('folder-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_folder"))


class RiskAnalysisListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/analysis_list.html'
    context_object_name = 'analyses'

    ordering = 'created_at'
    paginate_by = 10
    model = Analysis

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        filtered_list = AnalysisFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = AnalysisFilter(self.request.GET, queryset)
        context['filter'] = filter
        # self.model._meta.verbose_name # TODO: Find a way to get unlocalized model verbose_name, as localization may break stuff e.g. urls
        context['model'] = 'analysis'
        context['analysis_create_form'] = RiskAnalysisCreateForm
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)
        context['add_analysis'] = RoleAssignment.has_permission(
            self.request.user, 'add_analysis')
        context['no_matrix'] = (RiskMatrix.objects.all().count() - RiskMatrix.objects.filter(is_enabled=False).count()) < 1
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class RiskAnalysisCreateView(UserPassesTestMixin, CreateView):
    model = Analysis
    template_name = 'core/ra_create.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        project = Project.objects.get(id=self.request.POST['project'])
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_analysis"), folder=Folder.objects.get(id=project.folder.id))


class RiskAnalysisCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = Analysis
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', 'analysis-list')

    def test_func(self):
        project = Project.objects.get(id=self.request.POST['project'])
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_analysis"), folder=Folder.objects.get(id=project.folder.id))


class RiskAnalysisUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Analysis
    template_name = 'core/ra_update.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['risk_scenario_create_form'] = RiskScenarioCreateForm(
            initial={'analysis': get_object_or_404(Analysis, id=self.kwargs['pk'])})
        context['scenarios'] = RiskScenario.objects.filter(
            analysis=self.get_object()).order_by('created_at')
        context['crumbs'] = {'analysis-list': _('Analyses')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('analysis-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_analysis"),
            folder=Folder.get_folder(self.get_object()))


class RiskMatrixDeleteView(UserPassesTestMixin, DeleteView):
    model = RiskMatrix
    success_url = reverse_lazy('riskmatrix-list')
    template_name = 'snippets/rm_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('riskmatrix-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_riskmatrix"))


class RiskAnalysisDeleteView(UserPassesTestMixin, DeleteView):
    model = Analysis
    success_url = reverse_lazy('analysis-list')
    template_name = 'snippets/ra_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('analysis-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_analysis"))


class RiskScenarioListView(BaseContextMixin, UserPassesTestMixin, ListView):
    permission_required = 'core.view_riskscenario'
    template_name = 'core/ri_list.html'
    context_object_name = 'scenarios'

    ordering = 'created_at'
    paginate_by = 10
    model = RiskScenario

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskScenario)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        filtered_list = RiskScenarioFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = RiskScenarioFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['model'] = 'riskscenario'
        context['risk_scenario_create_form'] = RiskScenarioCreateForm
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskScenario)
        context['add_riskscenario'] = RoleAssignment.has_permission(
            self.request.user, 'add_riskscenario')
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class RiskScenarioCreateView(BaseContextMixin, UserPassesTestMixin, CreateView):
    model = RiskScenario
    template_name = 'core/ri_create.html'
    context_object_name = 'scenario'
    form_class = RiskScenarioCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analysis'] = get_object_or_404(
            Analysis, id=self.kwargs['analysis'])

        return context

    def form_valid(self, form: RiskScenarioCreateForm) -> HttpResponse:
        if form.is_valid():
            form.scenario.analysis = get_object_or_404(
                Analysis, id=self.kwargs['analysis'])
            return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('analysis-update', kwargs={'pk': get_object_or_404(Analysis, id=self.kwargs['analysis']).id})

    def test_func(self):
        analysis = get_object_or_404(Analysis, id=self.request.POST['analysis'])
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_riskscenario"), folder=Folder.objects.get(id=analysis.project.folder.id))


class RiskScenarioCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = RiskScenario
    context_object_name = 'scenario'
    form_class = RiskScenarioCreateForm

    def test_func(self):
        analysis = get_object_or_404(Analysis, id=self.request.POST['analysis'])
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_riskscenario"), folder=Folder.objects.get(id=analysis.project.folder.id))


class RiskScenarioUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = RiskScenario
    template_name = 'core/ri_update.html'
    context_object_name = 'scenario'
    form_class = RiskScenarioUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['security_measures'] = self.get_object().security_measures.all()
        context['existing_security_measures'] = SecurityMeasure.objects.filter(
            folder=self.get_object().analysis.project.folder)
        context['crumbs'] = {'riskscenario-list': _('Risk scenarios')}
        context['measure_create_form'] = SecurityMeasureCreateFormInherited(
            initial={'folder': get_object_or_404(Folder, id=self.get_object().analysis.project.folder.id)})
        context['measures_select_form'] = SecurityMeasureSelectForm(
            initial={
                'security_measures': self.get_object().security_measures.all()},
        )
        context['measures_select_form'].fields['security_measures'].queryset = SecurityMeasure.objects.filter(
            folder=self.get_object().parent_project().folder)

        context['matrix'] = self.get_object().get_matrix()
        return context

    def get_success_url(self) -> str:
        if 'security_measure_name' in self.request.POST and SecurityMeasure.objects.get(name=self.request.POST['security_measure_name']).folder == self.get_object().analysis.project.folder:
            self.get_object().security_measures.add(SecurityMeasure.objects.get(name=self.request.POST['security_measure_name']))
        if "select_measures" in self.request.POST:
            return reverse_lazy('riskscenario-update', kwargs={'pk': self.kwargs['pk']})
        else:
            if (self.request.POST.get('next', '/') == ""):
                return reverse_lazy('riskscenario-list')
            else:
                return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_riskscenario"), folder=self.get_object().analysis.project.folder)


class RiskScenarioUpdateViewModal(UserPassesTestMixin, UpdateView):
    model = RiskScenario
    template_name = 'core/ri_update_modal.html'
    context_object_name = 'scenario'
    form_class = SecurityMeasureSelectForm

    def get_success_url(self) -> str:
        return reverse_lazy('riskscenario-update', kwargs={'pk': self.kwargs['pk']})

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_riskscenario"), folder=self.get_object().analysis.project.folder)


class RiskScenarioDeleteView(UserPassesTestMixin, DeleteView):
    model = RiskScenario
    success_url = reverse_lazy('riskscenario-list')
    template_name = 'snippets/risk_scenario_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('riskscenario-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_riskscenario"))


class SecurityMeasureListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/mtg_list.html'
    context_object_name = 'measures'

    ordering = 'created_at'
    paginate_by = 10
    model = SecurityMeasure

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = SecurityMeasureFilter(
            self.request.GET, queryset=queryset, request=self.request)
        context['filter'] = filter
        context['measure_create_form'] = SecurityMeasureCreateForm(user=self.request.user)
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, SecurityMeasure)
        context['add_securitymeasure'] = RoleAssignment.has_permission(
            self.request.user, 'add_securitymeasure')
        return context

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, SecurityMeasure)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        filtered_list = SecurityMeasureFilter(
            request=self.request.GET, queryset=qs)
        return filtered_list.qs

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class SecurityMeasureCreateViewModal(UserPassesTestMixin, CreateViewModal):
    permission_required = 'core.add_securitymeasure'
    model = SecurityMeasure
    context_object_name = 'measure'
    form_class = SecurityMeasureCreateForm

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_securitymeasure"), folder=Folder.objects.get(id=self.request.POST['folder']))


class SecurityMeasureUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = SecurityMeasure
    template_name = 'core/mtg_update.html'
    context_object_name = 'security_measure'
    form_class = SecurityMeasureUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['risk_scenarios'] = RiskScenario.objects.filter(
            security_measures=self.get_object())
        context['crumbs'] = {'securitymeasure-list': _('Security measures')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('securitymeasure-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_securitymeasure"), folder=self.get_object().folder)


class SecurityMeasureDeleteView(UserPassesTestMixin, DeleteView):
    model = SecurityMeasure
    success_url = reverse_lazy('securitymeasure-list')
    template_name = 'snippets/measure_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('securitymeasure-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_securitymeasure"))


class SecurityFunctionListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/security_function_list.html'
    context_object_name = 'functions'

    ordering = 'created_at'
    paginate_by = 10
    model = SecurityFunction

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, SecurityFunction)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        filtered_list = SecurityFunctionFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = SecurityFunctionFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['security_function_create_form'] = SecurityFunctionCreateForm
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, SecurityFunction)
        context['add_securityfunction'] = RoleAssignment.has_permission(
            self.request.user, 'add_securityfunction')
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class SecurityFunctionCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = SecurityFunction
    context_object_name = 'function'
    form_class = SecurityFunctionCreateForm

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_securityfunction"), folder=Folder.objects.get(id=self.request.POST['folder']))


class SecurityFunctionUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = SecurityFunction
    template_name = 'core/security_function_update.html'
    context_object_name = 'function'
    form_class = SecurityFunctionUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crumbs'] = {'securityfunction-list': _('Security functions')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('securityfunction-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_securityfunction"))


class SecurityFunctionDeleteView(UserPassesTestMixin, DeleteView):
    model = SecurityFunction
    success_url = reverse_lazy('securityfunction-list')
    template_name = 'snippets/security_function_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('securityfunction-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_securityfunction"))


class ThreatListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/threat_list.html'
    context_object_name = 'threats'

    ordering = 'created_at'
    paginate_by = 10
    model = Threat

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Threat)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        filtered_list = ThreatFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ThreatFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['threat_create_form'] = ThreatCreateForm
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Threat)
        context['add_threat'] = RoleAssignment.has_permission(
            self.request.user, 'add_threat')
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class ThreatCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = Threat
    context_object_name = 'threat'
    form_class = ThreatCreateForm

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_threat"), folder=Folder.objects.get(id=self.request.POST['folder']))


class ThreatUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Threat
    template_name = 'core/threat_update.html'
    context_object_name = 'threat'
    form_class = ThreatUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crumbs'] = {'threat-list': _('Threats')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('threat-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_threat"))


class ThreatDeleteView(UserPassesTestMixin, DeleteView):
    model = Threat
    success_url = reverse_lazy('threat-list')
    template_name = 'snippets/threat_delete_modal.html'

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_threat"))


class RiskAcceptanceListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/acceptance_list.html'
    context_object_name = 'acceptances'

    ordering = 'created_at'
    paginate_by = 10
    model = RiskAcceptance

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = RiskAcceptanceFilter(
            self.request.GET, queryset=queryset, request=self.request)
        context['filter'] = filter
        context['risk_acceptance_create_form'] = RiskAcceptanceCreateUpdateForm(user=self.request.user)
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskAcceptance)
        context['add_riskacceptance'] = RoleAssignment.has_permission(
            self.request.user, 'add_riskacceptance')
        context['blocked_states'] = ('accepted', 'rejected', 'revoked')
        return context

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskAcceptance)
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        filtered_list = RiskAcceptanceFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class RiskAcceptanceCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = RiskAcceptance
    context_object_name = 'acceptance'
    form_class = RiskAcceptanceCreateUpdateForm

    def get_form_kwargs(self):
        form = super().get_form_kwargs()
        form['user'] = self.request.user
        return form

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if self.object.validator:
            # Mettre à jour le paramètre "state"
            self.object.set_state('submitted')
            self.object.save()
            try:
                self.object.validator.mailing("core/risk_acceptance_email.txt", _("Pending risk acceptance: ") + self.object.name, self.object.pk)
                messages.success(self.request, "Risk acceptance created and mail send successfully to: " + self.object.validator.email)
            except:
                messages.error(
                    self.request, "An error has occured, mail was not send to: " + self.object.validator.email)
        return super().form_valid(form)

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_riskacceptance"), folder=Folder.objects.get(id=self.request.POST['folder']))


class RiskAcceptanceUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    permission_required = 'core.change_riskacceptance'
    model = RiskAcceptance
    template_name = 'core/risk_acceptance_update.html'
    context_object_name = 'acceptance'
    form_class = RiskAcceptanceCreateUpdateForm

    def get_form_kwargs(self):
        form = super().get_form_kwargs()
        form['user'] = self.request.user
        return form

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if self.object.validator and self.object.state == 'created':
            # Mettre à jour le paramètre "state"
            self.object.set_state('submitted')
            self.object.save()
            try:
                self.object.validator.mailing("core/risk_acceptance_email.txt", _("Pending risk acceptance: ") + self.object.name, self.object.pk)
                messages.success(self.request, "Risk acceptance created and mail send successfully to: " + self.object.validator.email)
            except:
                messages.error(
                    self.request, "An error has occured, mail was not send to: " + self.object.validator.email)
        elif not self.object.validator and self.object.state == 'submitted':
            # Mettre à jour le paramètre "state"
            self.object.set_state('created')
            self.object.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'riskacceptance-list': _('Risk acceptances')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('riskacceptance-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return (RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_riskacceptance"), folder=self.get_object().folder) and self.get_object().state not in ('accepted', 'rejected', 'revoked'))


class RiskAcceptanceDeleteView(UserPassesTestMixin, DeleteView):
    model = RiskAcceptance
    success_url = reverse_lazy('riskacceptance-list')
    template_name = 'snippets/risk_acceptance_delete_modal.html'

    success_url = reverse_lazy('riskacceptance-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_riskacceptance"))


class MyProfileDetailView(BaseContextMixin, UserPassesTestMixin, DetailView):
    template_name = 'core/my_profile_detailed.html'
    context_object_name = 'user'

    model = User

    def get_object(self, queryset: Optional[models.query.QuerySet[Any]] = ...) -> models.Model:
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not UserGroup.get_user_groups(self.request.user):
            messages.warning(self.request, _(
                "Warning! You are not assigned to any group. Without a group you will not have access to any functionality. Please contact you administrator."))
        context['user_groups'] = self.object.user_groups.all()
        keys = ['Last name', 'First name', 'Email', 'Entry date', 'Superuser']
        values = []
        for key, value in model_to_dict(self.object, fields=['last_name', 'first_name', 'email', 'date_joined']).items():
            values.append(value)
        context['user_fields'] = dict(zip(keys, values))
        roles = []
        for user_group in self.object.user_groups.all():
            for role_assignment in user_group.roleassignment_set.all():
                roles.append(role_assignment.role.name)
        context['roles'] = roles
        return context

    def test_func(self):
        return self.request.user.is_authenticated


class MyProfileUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    template_name = 'core/user_update.html'
    context_object_name = 'user'
    form_class = MyProfileUpdateForm

    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = get_object_or_404(User, pk=self.kwargs['pk'])
        print('DEBUG: User =', get_object_or_404(User, pk=self.kwargs['pk']))
        return kwargs

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('index')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return self.request.user == get_object_or_404(User, pk=self.kwargs['pk'])


class UserListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/user_list.html'
    context_object_name = 'users'

    ordering = 'created_at'
    paginate_by = 10
    model = User

    def get_queryset(self):
        qs = self.model.objects.all().order_by(
            '-is_active', '-is_superuser', 'email', 'id')
        filtered_list = UserFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['users_number'] = User.objects.all().count()
        context['users_number_limit'] = MAX_USERS
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="view_user"))


class UserCreateView(BaseContextMixin, UserPassesTestMixin, CreateView):
    template_name = 'core/user_create.html'
    context_object_name = 'user'
    form_class = UserCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'user-list': _('Users')}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            data = form.cleaned_data['email']
            try:
                User.objects.create_user(email=data)
                messages.success(request, _('User created and email send successfully.'))
                return redirect("user-list")
            except Exception as e:
                messages.error(request, "An error has occured during user creation. If he has not received the mail, please use the forgot link on login page.")
                print("Exception:", e)
                return redirect("user-list")
        return render(request, self.template_name, {'form': form})

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_user"))


class UserUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    template_name = 'core/user_update.html'
    context_object_name = 'user'
    form_class = UserUpdateForm

    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'user-list': _('Users')}
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = get_object_or_404(User, pk=self.kwargs['pk'])
        print('DEBUG: User =', get_object_or_404(User, pk=self.kwargs['pk']))
        return kwargs

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('user-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_user"))


class UserDeleteView(UserPassesTestMixin, DeleteView):
    model = User
    success_url = reverse_lazy('user-list')
    template_name = 'snippets/user_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_user"))


class UserGroupListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/group_list.html'
    context_object_name = 'user_groups'

    ordering = 'folder'
    paginate_by = 10
    model = UserGroup

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(
                content_type=Folder.ContentType.ROOT), self.request.user, UserGroup
        )
        qs = self.model.objects.filter(
            id__in=object_ids_view).order_by(self.ordering)
        filtered_list = UserGroupFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserGroupFilter(self.request.GET, queryset)
        context['filter'] = filter
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(
                content_type=Folder.ContentType.ROOT), self.request.user, UserGroup
        )
        context['add_usergroup'] = RoleAssignment.has_permission(
            self.request.user, 'add_usergroup')
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename='view_usergroup'))


class UserGroupCreateView(UserPassesTestMixin, CreateView):
    template_name = 'core/group_create.html'
    context_object_name = 'user_group'
    form_class = UserGroupCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('usergroup-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_usergroup"))


class UserGroupUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    template_name = 'core/group_update.html'
    context_object_name = 'user_group'
    form_class = UserGroupUpdateForm

    model = UserGroup

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.exclude(user_groups=self.get_object())
        context["associated_users"] = User.objects.filter(
            user_groups=self.get_object())
        context["crumbs"] = {'usergroup-list': _('User groups')}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('usergroup-list')

    def test_func(self):
        user_group = self.get_object()
        return not (user_group.builtin) and RoleAssignment.is_access_allowed(user=self.request.user,
                                                                             perm=Permission.objects.get(
                                                                                 codename="change_usergroup"),
                                                                             folder=Folder.get_folder(user_group))


class UserGroupDeleteView(UserPassesTestMixin, DeleteView):
    model = UserGroup
    success_url = reverse_lazy('usergroup-list')
    template_name = 'snippets/group_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('usergroup-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_usergroup"))


class RoleAssignmentListView(BaseContextMixin, UserPassesTestMixin, ListView):
    permission_required = 'core.view_roleassignment'
    template_name = 'core/role_list.html'
    context_object_name = 'assignments'

    ordering = 'created_at'
    paginate_by = 10
    model = RoleAssignment

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        messages.info(self.request, _("Role assignment editing will be available in a future release. Currently you have to go through groups to assign roles."))

    def get_queryset(self):
        qs = self.model.objects.all().order_by('id')
        filtered_list = UserGroupFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserGroupFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['roles'] = Role.objects.all().order_by('id')
        return context

    def test_func(self):
        return True


class RoleAssignmentCreateView(BaseContextMixin, UserPassesTestMixin, CreateView):
    permission_required = 'core.add_roleassignment'
    template_name = 'core/role_assignment_create.html'
    context_object_name = 'assignment'
    form_class = RoleAssignmentCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'role-list': _('Role assignment')}
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_roleassignment"))


class RoleAssignmentDeleteView(UserPassesTestMixin, DeleteView):
    permission_required = 'core.delete_roleassignment'
    model = RoleAssignment
    success_url = reverse_lazy('role-list')
    template_name = 'snippets/role_assignment_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_roleassignment"))


class RoleAssignmentUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    permission_required = 'auth.change_role'
    template_name = 'core/role_update.html'
    context_object_name = 'role'
    form_class = RoleAssignmentUpdateForm

    model = Role

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'usergroup-list': _('User groups')}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')

    def test_func(self):
        ra = get_object_or_404(RoleAssignment, pk=self.kwargs['pk'])
        return not (ra.builtin) and RoleAssignment.is_access_allowed(user=self.request.user,
                                                                     perm=Permission.objects.get(codename="change_roleassignment"), folder=Folder.get_folder(ra))


class UserPasswordChangeView(BaseContextMixin, PasswordChangeView):
    """ view to change user password """
    template_name = 'core/password_change.html'
    form_class = UserPasswordChangeForm
    model = User

    def get_success_url(self) -> str:
        self.object = get_object_or_404(User, pk=self.kwargs['pk'])
        if self.object == self.request.user:
            return reverse_lazy("me-update", kwargs={'pk': self.request.user.id})
        return reverse_lazy("user-update", kwargs={'pk': self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['this_user'] = get_object_or_404(User, pk=self.kwargs['pk'])
        context["crumbs"] = {'user-list': _('Users')}
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = get_object_or_404(User, pk=self.kwargs['pk'])
        # print('DEBUG: User =', get_object_or_404(User, pk=self.kwargs['pk']))
        return kwargs


class RiskMatrixListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = 'core/risk_matrix_list.html'
    context_object_name = 'matrices'

    ordering = 'created_at'
    paginate_by = 10
    model = RiskMatrix

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskMatrix)
        qs = self.model.objects.all().order_by('created_at')
        filtered_list = RiskMatrixFilter(
            self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_ids_change"] = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskMatrix)[1]
        context["object_ids_delete"] = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskMatrix)[2]
        queryset = self.get_queryset()
        filter = RiskMatrixFilter(self.request.GET, queryset)
        context['filter'] = filter
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class RiskMatrixDetailView(BaseContextMixin, UserPassesTestMixin, DetailView):
    template_name = 'core/risk_matrix_detailed.html'
    context_object_name = 'matrix'

    model = RiskMatrix

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['viewable_projects'] = Project.objects.filter(
            id__in=RoleAssignment.get_accessible_object_ids(Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Project)[0]).filter(
            id__in=(self.get_object().projects.all().values_list('id', flat=True)))
        context['viewable_analyses'] = Analysis.objects.filter(
            id__in=RoleAssignment.get_accessible_object_ids(Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)[0]).filter(
            id__in=(self.get_object().analyses.all().values_list('id', flat=True)))
        context['changeable_analyses'] = Analysis.objects.filter(
            id__in=RoleAssignment.get_accessible_object_ids(Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)[1]).filter(
            id__in=(self.get_object().analyses.all().values_list('id', flat=True)))
        context["crumbs"] = {'riskmatrix-list': _('Matrices')}
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class RiskMatrixUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    template_name = 'core/risk_matrix_update.html'
    context_object_name = 'matrix'
    form_class = RiskMatrixUpdateForm

    model = RiskMatrix

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'riskmatrix-list': _('Matrices')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('riskmatrix-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_riskmatrix"), folder=Folder.get_folder(self.get_object()))
