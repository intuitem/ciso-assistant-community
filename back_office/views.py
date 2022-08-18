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
from general.models import Asset, ParentRisk, Project, ProjectsGroup, Solution

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

class QuickStartView(PermissionRequiredMixin, ListView):
    permission_required = 'general.view_projectsgroup'
    template_name = 'back_office/quick_start.html'
    context_object_name = 'quick-start'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects_domain_create_form'] = ProjectsGroupUpdateForm
        context['project_create_form'] = ProjectForm
        context['analysis_create_form'] = RiskAnalysisCreateForm
        context['threat_create_form'] = ThreatCreateForm
        context['security_function_create_form'] = SecurityFunctionCreateForm
        context['asset_create_form']= AssetForm
        return context

    def get_queryset(self):
        return True

class ProjectListView(UserPassesTestMixin, ListView):
    permission_required = 'general.view_project'
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
                    if project.parent_group in ra.domains.all():
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
        if self.request.user.is_superuser:
            return True
        else:
            return RoleAssignment.is_access_allowed(self.request.user, Permission.objects.get(codename="change_project"))

class AssetListView(PermissionRequiredMixin, ListView):
    permission_required = 'general.view_asset'
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

class ProjectsGroupListView(PermissionRequiredMixin, ListView):
    permission_required = 'general.view_projectsgroup'
    template_name = 'back_office/project_domain_list.html'
    context_object_name = 'domains'

    ordering = 'id'
    paginate_by = 10
    model = ProjectsGroup

    def get_queryset(self):
        qs = self.model.objects.all().order_by('id')
        filtered_list = ProjectsDomainFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProjectsDomainFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['projects_domain_create_form'] = ProjectsGroupUpdateForm
        return context

class RiskAnalysisListView(UserPassesTestMixin, ListView):
    permission_required = 'core.view_analysis'
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
                    if analysis.project.parent_group in ra.domains.all():
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
        if self.request.user.is_superuser:
            return True
        else:
            return RoleAssignment.is_access_allowed(self.request.user, Permission.objects.get(codename="view_analysis"))

class RiskInstanceListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_riskinstance'
    template_name = 'back_office/ri_list.html'
    context_object_name = 'scenarios'

    ordering = 'id'
    paginate_by = 10
    model = RiskInstance

    def get_queryset(self):
        qs = self.model.objects.all().order_by('treatment', 'id')
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

class MitigationListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_mitigation'
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
        qs = self.model.objects.all().order_by('status', 'id')
        filtered_list = MeasureFilter(self.request.GET, queryset=qs)
        return filtered_list.qs
        # if not self.request.user.is_superuser:
        #     agg_data = Mitigation.objects.filter(risk_instance__analysis__auditor=self.request.user).order_by('id')
        # else:
        #     agg_data = Mitigation.objects.all().order_by('id')
        # return agg_data

class SecurityFunctionListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_solution'
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


class ParentRiskListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_parentrisk'
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

class RiskAcceptanceListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_riskacceptance'
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
        qs = self.model.objects.all().order_by('type', 'id')
        filtered_list = RiskAcceptanceFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

class UserListView(PermissionRequiredMixin, ListView):
    permission_required = 'auth.view_user'
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

class UserCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'auth.add_user'
    template_name = 'back_office/user_create.html'
    context_object_name = 'user'
    form_class = UserCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')

class UserUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'auth.change_user'
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

class GroupListView(PermissionRequiredMixin, ListView):
    permission_required = 'auth.view_group'
    template_name = 'back_office/group_list.html'
    context_object_name = 'groups'

    ordering = 'id'
    paginate_by = 10
    model = UserGroup

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

class RoleAssignmentListView(PermissionRequiredMixin, ListView):
    permission_required = 'back_office.view_roleassignment'
    template_name = 'back_office/role_list.html'
    context_object_name = 'assignments'

    ordering = 'id'
    paginate_by = 10
    model = RoleAssignment

    def get_queryset(self):
        qs = self.model.objects.all().order_by('id')
        filtered_list = GroupFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = GroupFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['roles'] = Role.objects.all().order_by('id')
        return context

class RoleAssignmentCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'back_office.add_roleassignment'
    template_name = 'back_office/role_assignment_create.html'
    context_object_name = 'assignment'
    form_class = RoleAssignmentForm

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'role-list': _('Role assignment')}
        return context

class RoleAssignmentUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'back_office.change_roleassignment'
    template_name = 'back_office/role_assignment_update.html'
    context_object_name = 'assignment'
    model = RoleAssignment
    form_class = RoleAssignmentForm

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'role-list': _('Role assignment')}
        return context

class RoleAssignmentDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'back_office.delete_roleassignment'
    model = RoleAssignment
    success_url = reverse_lazy('role-list')
    template_name = 'back_office/snippets/role_assignment_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')
    


class GroupCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'auth.add_group'
    template_name = 'back_office/group_create.html'
    context_object_name = 'group'
    form_class = GroupCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('group-list')

class GroupUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'auth.change_group'
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

class RoleUpdateView(PermissionRequiredMixin, UpdateView):
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

class RiskAnalysisCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_analysis'
    model = Analysis
    template_name = 'back_office/ra_create.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

class MeasureCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_mitigation'
    model = Mitigation
    template_name = 'back_office/snippets/measure_create_modal.html'
    context_object_name = 'measure'
    form_class = MeasureCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

class RiskAcceptanceCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_riskacceptance'
    model = RiskAcceptance
    template_name = 'back_office/snippets/risk_acceptance_create_modal.html'
    context_object_name = 'acceptance'
    form_class = RiskAcceptanceCreateUpdateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

class RiskAcceptanceUpdateView(PermissionRequiredMixin, UpdateView):
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

class ThreatCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_parentrisk'
    model = ParentRisk
    template_name = 'back_office/snippets/threat_create_modal.html'
    context_object_name = 'threat'
    form_class = ThreatCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

class SecurityFunctionCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_solution'
    model = Solution
    template_name = 'back_office/snippets/security_function_create_modal.html'
    context_object_name = 'function'
    form_class = SecurityFunctionCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

class RiskAnalysisCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_analysis'
    model = Analysis
    template_name = 'back_office/snippets/analysis_create_modal.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

class RiskScenarioCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_analysis'
    model = RiskInstance
    template_name = 'back_office/snippets/risk_scenario_create_modal.html'
    context_object_name = 'scenario'
    form_class = RiskScenarioCreateForm


    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

class ProjectsGroupCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'general.add_projectsgroup'
    model = ProjectsGroup
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = ProjectsGroupUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('pd-list')

class ProjectsGroupCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'general.add_projectsgroup'
    model = ProjectsGroup
    template_name = 'back_office/snippets/projects_domain_create_modal.html'
    context_object_name = 'domain'
    form_class = ProjectsGroupUpdateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

class RiskInstanceCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_riskinstance'
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

class RiskInstanceCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_riskinstance'
    model = RiskInstance
    template_name = 'back_office/ri_create_modal.html'
    context_object_name = 'instance'
    form_class = RiskInstanceCreateForm

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
        if self.request.user.is_superuser:
            return True
        else:
            return RoleAssignment.is_access_allowed(self.request.user, Permission.objects.get(codename="change_analysis"), self.get_object().project.parent_group)

class RiskAnalysisDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'core.delete_analysis'

    model = Analysis
    success_url = reverse_lazy('ra-list')
    template_name = 'back_office/snippets/ra_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('ra-list')

class RiskScenarioDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'core.delete_riskinstance'

    model = RiskInstance
    success_url = reverse_lazy('ri-list')
    template_name = 'back_office/snippets/risk_scenario_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('ri-list')

class RiskAcceptanceDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'core.delete_riskacceptance'

    model = RiskAcceptance
    success_url = reverse_lazy('acceptance-list')
    template_name = 'back_office/snippets/risk_acceptance_delete_modal.html'

    success_url = reverse_lazy('acceptance-list')

class MeasureDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'core.delete_mitigation'

    model = Mitigation
    success_url = reverse_lazy('mtg-list')
    template_name = 'back_office/snippets/measure_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('mtg-list')

class SecurityFunctionDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'core.delete_solution'

    model = Solution
    success_url = reverse_lazy('security-function-list')
    template_name = 'back_office/snippets/security_function_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('security-function-list')

class ThreatDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'core.delete_threat'

    model = ParentRisk
    success_url = reverse_lazy('threat-list')
    template_name = 'back_office/snippets/threat_delete_modal.html'

class ProjectDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'general.delete_project'

    model = Project
    success_url = reverse_lazy('project-list')
    template_name = 'back_office/snippets/project_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('project-list')

class AssetDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'general.delete_asset'

    model = Asset
    success_url = reverse_lazy('asset-list')
    template_name = 'back_office/snippets/asset_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('asset-list')

class ProjectsGroupDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'general.delete_projectsgroup'

    model = ProjectsGroup
    success_url = reverse_lazy('pd-list')
    template_name = 'back_office/snippets/projects_domain_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('pd-list')
   
class RiskInstanceUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'core.change_riskinstance'
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

class MitigationUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'core.change_mitigation'
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

class SecurityFunctionUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'core.change_solution'
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

class ThreatUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'core.change_parentrisk'
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

class ProjectsGroupUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'general.change_projectsgroup'
    model = ProjectsGroup
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = ProjectsGroupUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(parent_group=self.get_object())
        context['crumbs'] = {'pd-list': _('Projects domains')}
        context['project_create_form'] = ProjectForm(initial={'parent_group': get_object_or_404(ProjectsGroup, id=self.kwargs['pk'])})
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('pd-list')
        else:
          return self.request.POST.get('next', '/')


class GroupDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'auth.delete_group'

    model = UserGroup
    success_url = reverse_lazy('group-list')
    template_name = 'back_office/snippets/group_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('group-list')

class UserDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = 'auth.delete_user'

    model = User
    success_url = reverse_lazy('user-list')
    template_name = 'back_office/snippets/user_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')

class ProjectUpdateView(UserPassesTestMixin, UpdateView):
    permission_required = 'general.change_project'
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
        if self.request.user.is_superuser:
            return True
        else:
            return RoleAssignment.is_access_allowed(self.request.user, Permission.objects.get(codename="change_project"), self.get_object().parent_group)


class AssetUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'general.change_asset'
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

class ProjectCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'general.add_project'
    model = Project
    template_name = 'back_office/project_create.html'
    context_object_name = 'project'
    form_class = ProjectForm

    def get_success_url(self) -> str:
        return reverse_lazy('project-list')

class ProjectCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'general.add_project'
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

class AssetCreateViewModal(PermissionRequiredMixin, CreateView):
    permission_required = 'general.add_asset'
    model = Asset
    template_name = 'back_office/snippets/asset_create_modal.html'
    context_object_name = 'asset'
    form_class = AssetForm

    def get_success_url(self):
        return self.request.POST.get('next', '/')

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

