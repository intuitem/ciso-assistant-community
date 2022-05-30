from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView, CreateView, DeleteView
from django.http import HttpResponse, HttpResponseRedirect
from django.template import context, loader
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.models import User, Group
from core.models import Analysis, RiskInstance, Mitigation, RiskAcceptance
from general.models import ParentRisk, Project, ProjectsGroup, Solution
from .forms import *

from .filters import *

def index(request):
    template = loader.get_template('back_office/index.html')
    context = {
        'hello': 'world',
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
        return context

    def get_queryset(self):
        return True

class ProjectListView(PermissionRequiredMixin, ListView):
    permission_required = 'general.view_project'
    template_name = 'back_office/project_list.html'
    context_object_name = 'projects'

    ordering = 'id'
    paginate_by = 10
    model = Project

    def get_queryset(self):
        qs = self.model.objects.all()
        filtered_list = ProjectFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProjectFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['project_create_form'] = ProjectForm
        return context

class ProjectsGroupListView(PermissionRequiredMixin, ListView):
    permission_required = 'general.view_projectsgroup'
    template_name = 'back_office/project_domain_list.html'
    context_object_name = 'domains'

    ordering = 'id'
    paginate_by = 10
    model = ProjectsGroup

    def get_queryset(self):
        qs = self.model.objects.all()
        filtered_list = ProjectsDomainFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProjectsDomainFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['projects_domain_create_form'] = ProjectsGroupUpdateForm
        return context

class RiskAnalysisListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_analysis'
    template_name = 'back_office/analysis_list.html'
    context_object_name = 'analyses'

    ordering = 'id'
    paginate_by = 10
    model = Analysis

    def get_queryset(self):
        qs = self.model.objects.all()
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
        context['analysis_create_form'] = RiskAnalysisCreateForm
        return context

class RiskInstanceListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_riskinstance'
    template_name = 'back_office/ri_list.html'
    context_object_name = 'scenarios'

    ordering = 'id'
    paginate_by = 10
    model = RiskInstance

    def get_queryset(self):
        qs = self.model.objects.all()
        filtered_list = RiskScenarioFilter(self.request.GET, queryset=qs)
        return filtered_list.qs
        # if not self.request.user.is_superuser:
        #     agg_data = RiskInstance.objects.filter(analysis__auditor=self.request.user).order_by('id')
        # else:
        #     agg_data = RiskInstance.objects.all().order_by('id')
        # return agg_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = RiskScenarioFilter(self.request.GET, queryset)
        context['filter'] = filter
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
        qs = self.model.objects.all()
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
        qs = self.model.objects.all()
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
        qs = self.model.objects.all()
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
        qs = self.model.objects.all()
        filtered_list = RiskAcceptanceFilter(self.request.GET, queryset=qs)
        return filtered_list.qs
        # if not self.request.user.is_superuser:
        #     agg_data = RiskAcceptance.objects.filter(risk_instance__analysis__auditor=self.request.user).order_by('type', 'id')
        # else:
        #     agg_data = RiskAcceptance.objects.all().order_by('type', 'id')
        # return agg_data

class UserListView(PermissionRequiredMixin, ListView):
    permission_required = 'auth.view_user'
    template_name = 'back_office/user_list.html'
    context_object_name = 'users'

    ordering = 'id'
    paginate_by = 10
    model = User

class UserCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'auth.add_user'
    template_name = 'back_office/user_create.html'
    context_object_name = 'user'
    form_class = UserCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')

class GroupListView(PermissionRequiredMixin, ListView):
    permission_required = 'auth.view_group'
    template_name = 'back_office/group_list.html'
    context_object_name = 'groups'

    ordering = 'id'
    paginate_by = 10
    model = Group

class RiskAnalysisCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_analysis'
    model = Analysis
    template_name = 'back_office/ra_create.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('ra-list')

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

    def get_success_url(self) -> str:
        return reverse_lazy('acceptance-list')

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

    # def form_valid(self, form: form_class) -> HttpResponse:
    #     if form.is_valid():
    #         form.project = get_object_or_404(Project, id=self.kwargs['parent_project'])
    #         form.auditor = self.request.user
    #         analysis = form.save(commit=False)
    #         analysis.project = get_object_or_404(Project, id=3)
    #         return super().form_valid(form)

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

class RiskAnalysisUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'core.change_analysis'
    model = Analysis
    template_name = 'back_office/ra_update.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['instances'] = RiskInstance.objects.filter(analysis=self.get_object()).order_by('id')
        context['suggested_measures'] = Mitigation.objects.all().order_by('id')
        context['crumbs'] = [_('Analyses')]
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('ra-list')

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
        context['crumbs'] = [_('Risk Scenarios')]
        context['measure_create_form'] = MeasureCreateForm(initial={'risk_instance': get_object_or_404(RiskInstance, id=self.kwargs['pk'])})
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('ra-update', kwargs = {'pk': self.object.analysis.id})

class MitigationUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'core.change_mitigation'
    model = Mitigation
    template_name = 'back_office/mtg_update.html'
    context_object_name = 'mitigation'
    form_class = MitigationUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('ri-update', kwargs = {'pk': self.object.risk_instance.id})

class SecurityFunctionUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'core.change_solution'
    model = Solution
    template_name = 'back_office/security_function_update.html'
    context_object_name = 'function'
    form_class = SecurityFunctionUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('security-function-list')

class ThreatUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'core.change_parentrisk'
    model = ParentRisk
    template_name = 'back_office/threat_update.html'
    context_object_name = 'threat'
    form_class = ThreatUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('threat-list')

class ProjectsGroupUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'general.change_projectsgroup'
    model = ProjectsGroup
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = ProjectsGroupUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(parent_group=self.get_object())
        crumbs = [_('Projects Domains')]
        context['crumbs'] = crumbs
        context['project_create_form'] = ProjectForm(initial={'parent_group': get_object_or_404(ProjectsGroup, id=self.kwargs['pk'])})
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('pd-list')

class ProjectUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'general.change_project'
    model = Project
    template_name = 'back_office/project_update.html'
    context_object_name = 'project'
    form_class = ProjectForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analyses'] = Analysis.objects.filter(project=self.get_object()).order_by('is_draft', 'id')
        context['analysis_create_form'] = RiskAnalysisCreateForm(initial={'project': get_object_or_404(Project, id=self.kwargs['pk']), 'auditor': self.request.user})
        crumbs = [_('Projects')]
        context['crumbs'] = crumbs
        return context
    
    # def get_queryset(self):
    #     if not self.request.user.is_superuser:
    #         agg_data = Analysis.objects.filter(auditor=self.request.user).order_by('is_draft', 'id')
    #     else:
    #         agg_data = Analysis.objects.all().order_by('is_draft', 'id')
    #     return agg_data

    def get_success_url(self) -> str:
        return reverse_lazy('project-list')

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
        next_url = self.request.GET.get('next')
        print(next_url)
        print(self.request.path)
        return redirect(next_url) if next_url is not None else reverse_lazy('project-list')
