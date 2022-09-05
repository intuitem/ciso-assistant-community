from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView, CreateView, DeleteView
from django.views.generic.edit import FormView
from django.http import HttpResponse, HttpResponseRedirect
from django.template import context, loader
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator


from datetime import date

from django.contrib.auth.models import User
from .models import UserGroup, RoleAssignment, Role
from django.contrib.auth.views import PasswordChangeView
from core.models import Analysis, RiskInstance, Mitigation, RiskAcceptance
from general.models import Asset, ParentRisk, Project, Folder, Solution

from .forms import *

from .filters import *

from core.helpers import get_counters, risks_count_per_level, mitigation_per_status, measures_to_review, acceptances_to_review

def index(request):
    template = loader.get_template('back_office/index.html')

    context = {
        "counters": get_counters(),
        "risks_level": risks_count_per_level(),
        "mitigation_status": mitigation_per_status(),
        "measures_to_review": measures_to_review(),
        "acceptances_to_review": acceptances_to_review(),
        "today": date.today()
    }
    return HttpResponse(template.render(context, request))

class QuickStartView(UserPassesTestMixin, ListView):
    template_name = 'back_office/quick_start.html'
    context_object_name = 'quick-start'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects_domain_create_form'] = FolderUpdateForm
        context['project_create_form'] = ProjectForm
        context['analysis_create_form'] = RiskAnalysisCreateForm
        context['threat_create_form'] = ThreatCreateForm
        context['security_function_create_form'] = SecurityFunctionCreateForm
        context['asset_create_form']= AssetForm
        return context

    def get_queryset(self):
        return True
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_folder"))

class ProjectListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/project_list.html'
    context_object_name = 'projects'

    ordering = 'id'
    paginate_by = 10
    model = Project

    def get_queryset(self):
        projects_list = []
        if self.request.user.is_superuser:
            qs = self.model.objects.all()
        else:
            for ra in self.request.user.roleassignment_set.all():
                for project in self.model.objects.all():
                    if project.folder in ra.folders.all():
                        projects_list.append(project.name)
            for userGroup in UserGroup.get_userGroups(self.request.user):
                for ra in userGroup.roleassignment_set.all():
                    for project in self.model.objects.all():
                        if project.folder in ra.folders.all():
                            projects_list.append(project.name)
            qs = self.model.objects.filter(name__in=projects_list)
        filtered_list = ProjectFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProjectFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['project_create_form'] = ProjectForm
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename='view_project'))

class AssetListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/asset_list.html'
    context_object_name = 'assets'

    ordering = 'id'
    paginate_by = 10
    model = Asset

    def get_queryset(self):
        qs = self.model.objects.all().order_by('id')
        filtered_list = AssetFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = AssetFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['asset_create_form'] = AssetForm
        return context
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_asset"))

class FolderListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/project_domain_list.html'
    context_object_name = 'domains'

    ordering = 'id'
    paginate_by = 10
    model = Folder

    def get_queryset(self):
        folders_list =  RoleAssignment.get_accessible_folders(Folder.objects.get(name="Global"), self.request.user, "DO")
        if folders_list == True:
            qs = self.model.objects.filter(content_type="DO")
        else:
            qs = self.model.objects.filter(name__in=folders_list)
        filtered_list = ProjectsDomainFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProjectsDomainFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['projects_domain_create_form'] = FolderUpdateForm
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_folder"))

class RiskAnalysisListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/analysis_list.html'
    context_object_name = 'analyses'

    ordering = 'id'
    paginate_by = 10
    model = Analysis

    def get_queryset(self):
        analyses_list = []
        if self.request.user.is_superuser:
            qs = self.model.objects.all()
        else:
            for ra in self.request.user.roleassignment_set.all():
                for analysis in self.model.objects.all():
                    if analysis.project.folder in ra.folders.all():
                        analyses_list.append(analysis.project)
            for userGroup in UserGroup.get_userGroups(self.request.user):
                for ra in userGroup.roleassignment_set.all():
                    for analysis in self.model.objects.all():
                        if analysis.project.folder in ra.folders.all():
                            analyses_list.append(analysis.project)
            qs = self.model.objects.filter(project__in=analyses_list)
        filtered_list = AnalysisFilter(self.request.GET, queryset=qs)
        return filtered_list.qs
        # if not self.request.user.is_superuser:
        #     agg_data = Analysis.objects.filter(auditor=self.request.user).order_by('is_draft', 'id')
        # else:
        #     agg_data = Analysis.objects.all().order_by('is_draft', 'id')
        # return agg_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = AnalysisFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['model'] = 'analysis' # self.model._meta.verbose_name # TODO: Find a way to get unlocalized model verbose_name, as localization may break stuff e.g. urls
        context['analysis_create_form'] = RiskAnalysisCreateForm
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_analysis"))

class RiskInstanceListView(UserPassesTestMixin, ListView):
    permission_required = 'core.view_riskinstance'
    template_name = 'back_office/ri_list.html'
    context_object_name = 'scenarios'

    ordering = 'id'
    paginate_by = 10
    model = RiskInstance

    def get_queryset(self):
        ri_list = []
        if self.request.user.is_superuser:
            qs = self.model.objects.all().order_by('treatment', 'id')
        else:
            for ra in self.request.user.roleassignment_set.all():
                for ri in self.model.objects.all():
                    if ri.analysis.project.folder in ra.folders.all():
                        ri_list.append(ri.analysis)
            for userGroup in UserGroup.get_userGroups(self.request.user):
                for ra in userGroup.roleassignment_set.all():
                    for ri in self.model.objects.all():
                        if ri.analysis.project.folder in ra.folders.all():
                            ri_list.append(ri.analysis)
            qs = self.model.objects.filter(analysis__in=ri_list).order_by('treatment', 'id')
        filtered_list = RiskScenarioFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = RiskScenarioFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['model'] = 'risk-scenario'
        context['risk_scenario_create_form'] = RiskScenarioCreateForm
        return context
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_riskinstance"))

class MitigationListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/mtg_list.html'
    context_object_name = 'measures'

    ordering = 'id'
    paginate_by = 10
    model = Mitigation

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = MeasureFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['measure_create_form'] = MeasureCreateForm
        return context

    def get_queryset(self):
        mitigation_list = []
        if self.request.user.is_superuser:
            qs = self.model.objects.all().order_by('status', 'id')
        else:
            for ra in self.request.user.roleassignment_set.all():
                for mitigation in self.model.objects.all():
                    if mitigation.risk_instance.analysis.project.folder in ra.folders.all():
                        mitigation_list.append(mitigation.risk_instance)
            for userGroup in UserGroup.get_userGroups(self.request.user):
                for ra in userGroup.roleassignment_set.all():
                    for mitigation in self.model.objects.all():
                        if mitigation.risk_instance.analysis.project.folder in ra.folders.all():
                            mitigation_list.append(mitigation.risk_instance)
            qs = self.model.objects.filter(risk_instance__in=mitigation_list).order_by('status', 'id')
        filtered_list = MeasureFilter(self.request.GET, queryset=qs)
        return filtered_list.qs
        # if not self.request.user.is_superuser:
        #     agg_data = Mitigation.objects.filter(risk_instance__analysis__auditor=self.request.user).order_by('id')
        # else:
        #     agg_data = Mitigation.objects.all().order_by('id')
        # return agg_data

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_mitigation"))

class SecurityFunctionListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/security_function_list.html'
    context_object_name = 'functions'

    ordering = 'id'
    paginate_by = 10
    model = Solution

    def get_queryset(self):
        qs = self.model.objects.all().order_by('id')
        filtered_list = SecurityFunctionFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = SecurityFunctionFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['security_function_create_form'] = SecurityFunctionCreateForm
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_solution"))


class ParentRiskListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/threat_list.html'
    context_object_name = 'threats'

    ordering = 'id'
    paginate_by = 10
    model = ParentRisk

    def get_queryset(self):
        qs = self.model.objects.all().order_by('id')
        filtered_list = ThreatFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ThreatFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['threat_create_form'] = ThreatCreateForm
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_parentrisk"))

class RiskAcceptanceListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/acceptance_list.html'
    context_object_name = 'acceptances'

    ordering = 'id'
    paginate_by = 10
    model = RiskAcceptance

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = RiskAcceptanceFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['risk_acceptance_create_form'] = RiskAcceptanceCreateUpdateForm
        context['risk_acceptance_update_form'] = RiskAcceptanceCreateUpdateForm
        return context

    def get_queryset(self):
        risk_acceptance_list = []
        if self.request.user.is_superuser:
            qs = self.model.objects.all().order_by('type', 'id')
        else:
            for ra in self.request.user.roleassignment_set.all():
                for risk_acceptance in self.model.objects.all():
                    if risk_acceptance.risk_instance.analysis.project.folder in ra.folders.all():
                        risk_acceptance_list.append(risk_acceptance.risk_instance)
            for userGroup in UserGroup.get_userGroups(self.request.user):
                for ra in userGroup.roleassignment_set.all():
                    for risk_acceptance in self.model.objects.all():
                        if risk_acceptance.risk_instance.analysis.project.folder in ra.folders.all():
                            risk_acceptance_list.append(risk_acceptance.risk_instance)
            qs = self.model.objects.filter(risk_instance__in=risk_acceptance_list).order_by('type', 'id')
        
        filtered_list = RiskAcceptanceFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_riskacceptance"))

class UserListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/user_list.html'
    context_object_name = 'users'

    ordering = 'id'
    paginate_by = 10
    model = User

    def get_queryset(self):
        qs = self.model.objects.all().order_by('-is_active', '-is_superuser', 'username', 'id')
        filtered_list = UserFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserFilter(self.request.GET, queryset)
        context['filter'] = filter
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="view_user"))

class UserCreateView(UserPassesTestMixin, CreateView):
    template_name = 'back_office/user_create.html'
    context_object_name = 'user'
    form_class = UserCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_user"))

class UserUpdateView(UserPassesTestMixin, UpdateView):
    template_name = 'back_office/user_update.html'
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
        return self.request.POST.get('next', '/')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_user"))

class GroupListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/group_list.html'
    context_object_name = 'groups'

    ordering = 'id'
    paginate_by = 10
    model = UserGroup

    def get_queryset(self):
        admin = False
        for userGroup in UserGroup.get_userGroups(self.request.user):
            for ra in userGroup.roleassignment_set.all():
                if Folder.objects.get(content_type="GL") in ra.folders.all() and Permission.objects.get(codename="view_usergroup") in ra.role.permissions.all():
                    admin=True
        if admin:
            qs = self.model.objects.all()
        else:
            qs = self.model.objects.filter(name__in=UserGroup.get_manager_userGroups(self.request.user))
        filtered_list = GroupFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = GroupFilter(self.request.GET, queryset)
        context['filter'] = filter
        return context
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename='view_usergroup'))

class RoleAssignmentListView(PermissionRequiredMixin, ListView):
    permission_required = 'auth.view_role'
    template_name = 'back_office/role_list.html'
    context_object_name = 'roles'

    ordering = 'id'
    paginate_by = 10
    model = Role

    def get_queryset(self):
        qs = self.model.objects.all().order_by('name', 'id')
        filtered_list = GroupFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = GroupFilter(self.request.GET, queryset)
        context['filter'] = filter
        return context


class GroupCreateView(UserPassesTestMixin, CreateView):
    template_name = 'back_office/group_create.html'
    context_object_name = 'group'
    form_class = GroupCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('group-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_group"))

class GroupUpdateView(UserPassesTestMixin, UpdateView):
    template_name = 'back_office/group_update.html'
    context_object_name = 'group'
    form_class = GroupUpdateForm

    model = UserGroup

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.exclude(groups=self.get_object())
        context["associated_users"] = User.objects.filter(groups=self.get_object())
        context["crumbs"] = {'group-list': _('Groups')}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('group-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename='change_usergroup'), folder=self.get_object().folder)

class RoleAssignmentUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'auth.change_role'
    template_name = 'back_office/role_update.html'
    context_object_name = 'role'
    form_class = RoleAssignmentUpdateForm

    model = Role

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'group-list': _('Groups')}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')

class RiskAnalysisCreateView(UserPassesTestMixin, CreateView):
    model = Analysis
    template_name = 'back_office/ra_create.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_analysis"))

class MeasureCreateViewModal(UserPassesTestMixin, CreateView):
    permission_required = 'core.add_mitigation'
    model = Mitigation
    template_name = 'back_office/snippets/measure_create_modal.html'
    context_object_name = 'measure'
    form_class = MeasureCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_mitigation"))

class RiskAcceptanceCreateViewModal(UserPassesTestMixin, CreateView):
    model = RiskAcceptance
    template_name = 'back_office/snippets/risk_acceptance_create_modal.html'
    context_object_name = 'acceptance'
    form_class = RiskAcceptanceCreateUpdateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_riskacceptance"))

class RiskAcceptanceUpdateView(UserPassesTestMixin, UpdateView):
    permission_required = 'core.change_riskacceptance'
    model = RiskAcceptance
    template_name = 'back_office/risk_acceptance_update.html'
    context_object_name = 'acceptance'
    form_class = RiskAcceptanceCreateUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'acceptance-list': _('Risk acceptances')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('acceptance-list')
        else:
          return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_riskacceptance"), folder = self.get_object().risk_instance.analysis.project.folder)

class ThreatCreateViewModal(UserPassesTestMixin, CreateView):
    model = ParentRisk
    template_name = 'back_office/snippets/threat_create_modal.html'
    context_object_name = 'threat'
    form_class = ThreatCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_parentrisk"))

class SecurityFunctionCreateViewModal(UserPassesTestMixin, CreateView):
    model = Solution
    template_name = 'back_office/snippets/security_function_create_modal.html'
    context_object_name = 'function'
    form_class = SecurityFunctionCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_solution"))

class RiskAnalysisCreateViewModal(UserPassesTestMixin, CreateView):
    model = Analysis
    template_name = 'back_office/snippets/analysis_create_modal.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_analysis"))

class RiskScenarioCreateViewModal(UserPassesTestMixin, CreateView):
    model = RiskInstance
    template_name = 'back_office/snippets/risk_scenario_create_modal.html'
    context_object_name = 'scenario'
    form_class = RiskScenarioCreateForm


    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_analysis"))

class FolderCreateView(UserPassesTestMixin, CreateView):
    model = Folder
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = FolderUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('pd-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_folder"))

class FolderCreateViewModal(UserPassesTestMixin, CreateView):
    model = Folder
    template_name = 'back_office/snippets/projects_domain_create_modal.html'
    context_object_name = 'domain'
    form_class = FolderUpdateForm

    def get_success_url(self) -> str:
        folder = Folder.objects.latest("id")
        auditors = UserGroup.objects.create(name= folder.name + " Auditors", folder = folder)
        analysts = UserGroup.objects.create(name= folder.name + " Analysts", folder = folder)
        managers = UserGroup.objects.create(name= folder.name + " Domain Managers", folder = folder)
        ra1 = RoleAssignment.objects.create(isUserGroup = True, userGroup = auditors, role = Role.objects.get(name="Auditor"))
        ra1.folders.add(folder)
        ra2 = RoleAssignment.objects.create(isUserGroup = True, userGroup = analysts, role = Role.objects.get(name="Analyst"))
        ra2.folders.add(folder)
        ra3 = RoleAssignment.objects.create(isUserGroup = True, userGroup = managers, role = Role.objects.get(name="Domain Manager"))
        ra3.folders.add(folder)
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_folder"))

class RiskInstanceCreateView(UserPassesTestMixin, CreateView):
    model = RiskInstance
    template_name = 'back_office/ri_create.html'
    context_object_name = 'instance'
    form_class = RiskInstanceCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analysis'] = get_object_or_404(Analysis, id=self.kwargs['parent_analysis'])

        return context

    def form_valid(self, form: RiskInstanceCreateForm) -> HttpResponse:
        if form.is_valid():
            form.instance.analysis = get_object_or_404(Analysis, id=self.kwargs['parent_analysis'])
            return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('ra-update', kwargs={'pk': get_object_or_404(Analysis, id=self.kwargs['parent_analysis']).id})

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_riskinstance"))

class RiskInstanceCreateViewModal(UserPassesTestMixin, CreateView):
    model = RiskInstance
    template_name = 'back_office/ri_create_modal.html'
    context_object_name = 'instance'
    form_class = RiskInstanceCreateForm

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_riskinstance"))

class RiskAnalysisUpdateView(UserPassesTestMixin, UpdateView):
    permission_required = 'core.change_analysis'
    model = Analysis
    template_name = 'back_office/ra_update.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['risk_scenario_create_form'] = RiskScenarioCreateForm(initial={'analysis': get_object_or_404(Analysis, id=self.kwargs['pk'])})
        context['instances'] = RiskInstance.objects.filter(analysis=self.get_object()).order_by('id')
        context['suggested_measures'] = Mitigation.objects.all().order_by('id')
        context['crumbs'] = {'ra-list': _('Analyses')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('ra-list')
        else:
          return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_analysis"), folder = self.get_object().project.folder)

class RiskAnalysisDeleteView(UserPassesTestMixin, DeleteView):
    model = Analysis
    success_url = reverse_lazy('ra-list')
    template_name = 'back_office/snippets/ra_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('ra-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_analysis"))

class RiskScenarioDeleteView(UserPassesTestMixin, DeleteView):
    model = RiskInstance
    success_url = reverse_lazy('ri-list')
    template_name = 'back_office/snippets/risk_scenario_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('ri-list')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_riskinstance"))

class RiskAcceptanceDeleteView(UserPassesTestMixin, DeleteView):
    model = RiskAcceptance
    success_url = reverse_lazy('acceptance-list')
    template_name = 'back_office/snippets/risk_acceptance_delete_modal.html'

    success_url = reverse_lazy('acceptance-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_riskacceptance"))

class MeasureDeleteView(UserPassesTestMixin, DeleteView):
    model = Mitigation
    success_url = reverse_lazy('mtg-list')
    template_name = 'back_office/snippets/measure_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('mtg-list')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_mitigation"))

class SecurityFunctionDeleteView(UserPassesTestMixin, DeleteView):
    model = Solution
    success_url = reverse_lazy('security-function-list')
    template_name = 'back_office/snippets/security_function_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('security-function-list')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_solution"))

class ThreatDeleteView(UserPassesTestMixin, DeleteView):
    model = ParentRisk
    success_url = reverse_lazy('threat-list')
    template_name = 'back_office/snippets/threat_delete_modal.html'

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_parentrisk"))

class ProjectDeleteView(UserPassesTestMixin, DeleteView):
    model = Project
    success_url = reverse_lazy('project-list')
    template_name = 'back_office/snippets/project_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('project-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_project"))

class AssetDeleteView(UserPassesTestMixin, DeleteView):
    model = Asset
    success_url = reverse_lazy('asset-list')
    template_name = 'back_office/snippets/asset_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('asset-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_asset"))

class FolderDeleteView(UserPassesTestMixin, DeleteView):
    model = Folder
    success_url = reverse_lazy('pd-list')
    template_name = 'back_office/snippets/projects_domain_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('pd-list')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_folder"))
   
class RiskInstanceUpdateView(UserPassesTestMixin, UpdateView):
    model = RiskInstance
    template_name = 'back_office/ri_update.html'
    context_object_name = 'instance'
    form_class = RiskInstanceUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mitigations'] = Mitigation.objects.filter(risk_instance=self.get_object())
        context['crumbs'] = {'ri-list': _('Risk scenarios')}
        context['measure_create_form'] = MeasureCreateForm(initial={'risk_instance': get_object_or_404(RiskInstance, id=self.kwargs['pk'])})
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('ri-list')
        else:
          return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_riskinstance"), folder = self.get_object().analysis.project.folder)

class MitigationUpdateView(UserPassesTestMixin, UpdateView):
    model = Mitigation
    template_name = 'back_office/mtg_update.html'
    context_object_name = 'mitigation'
    form_class = MitigationUpdateForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crumbs'] = {'mtg-list': _('Security measures')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('mtg-list')
        else:
          return self.request.POST.get('next', '/')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_mitigation"), folder = self.get_object().risk_instance.analysis.project.folder)

class SecurityFunctionUpdateView(UserPassesTestMixin, UpdateView):
    model = Solution
    template_name = 'back_office/security_function_update.html'
    context_object_name = 'function'
    form_class = SecurityFunctionUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crumbs'] = {'security-function-list': _('Security functions')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('security-function-list')
        else:
          return self.request.POST.get('next', '/')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_solution"))

class ThreatUpdateView(UserPassesTestMixin, UpdateView):
    model = ParentRisk
    template_name = 'back_office/threat_update.html'
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
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_parentrisk"))

class FolderUpdateView(UserPassesTestMixin, UpdateView):
    model = Folder
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = FolderUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(folder=self.get_object())
        context['crumbs'] = {'pd-list': _('Projects domains')}
        context['project_create_form'] = ProjectForm(initial={'domain': get_object_or_404(Folder, id=self.kwargs['pk'])})
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('pd-list')
        else:
          return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_folder"), folder = self.get_object())

class GroupDeleteView(UserPassesTestMixin, DeleteView):
    model = UserGroup
    success_url = reverse_lazy('group-list')
    template_name = 'back_office/snippets/group_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('group-list')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_group"))

class UserDeleteView(UserPassesTestMixin, DeleteView):
    model = User
    success_url = reverse_lazy('user-list')
    template_name = 'back_office/snippets/user_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_user"))

class ProjectUpdateView(UserPassesTestMixin, UpdateView):
    model = Project
    template_name = 'back_office/project_update.html'
    context_object_name = 'project'
    form_class = ProjectForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analyses'] = Analysis.objects.filter(project=self.get_object()).order_by('is_draft', 'id')
        context['analysis_create_form'] = RiskAnalysisCreateForm(initial={'project': get_object_or_404(Project, id=self.kwargs['pk']), 'auditor': self.request.user})
        context['crumbs'] = {'project-list': _('Projects')}
        return context
    
    # def get_queryset(self):
    #     if not self.request.user.is_superuser:
    #         agg_data = Analysis.objects.filter(auditor=self.request.user).order_by('is_draft', 'id')
    #     else:
    #         agg_data = Analysis.objects.all().order_by('is_draft', 'id')
    #     return agg_data

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('project-list')
        else:
          return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename='change_project'), folder = self.get_object().folder)

class AssetUpdateView(UserPassesTestMixin, UpdateView):
    model = Asset
    template_name = 'back_office/asset_update.html'
    context_object_name = 'asset'
    form_class = AssetForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crumbs'] = {'asset-list': _('Assets')}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('asset-list')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_asset"))

class ProjectCreateView(UserPassesTestMixin, CreateView):
    model = Project
    template_name = 'back_office/project_create.html'
    context_object_name = 'project'
    form_class = ProjectForm

    def get_success_url(self) -> str:
        return reverse_lazy('project-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename='add_project'))

class ProjectCreateViewModal(UserPassesTestMixin, CreateView):
    model = Project
    template_name = 'back_office/snippets/project_create_modal.html'
    context_object_name = 'project'
    form_class = ProjectForm

    # def get(self, request):
    #     next_url = request.GET.get('next')
    #     return render(request, template_name=self.template_name, context={'form': self.form_class, 'next': next_url})
    #     return redirect(next_url)

    # def post(self, request):
    #     form = ProjectForm(request.POST)
    #     next_url = request.POST.get('next') if 'next' in request.POST else 'project-list'
    #     return redirect(next_url)

    def get_success_url(self):
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename='add_project'))

class AssetCreateViewModal(UserPassesTestMixin, CreateView):
    model = Asset
    template_name = 'back_office/snippets/asset_create_modal.html'
    context_object_name = 'asset'
    form_class = AssetForm

    def get_success_url(self):
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_asset"))

class AdminPasswordChangeView(PasswordChangeView):
    template_name = 'back_office/password_change.html'
    form_class = AdminPasswordChangeForm
    model = User

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

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