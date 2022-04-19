from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView, CreateView, DeleteView
from django.http import HttpResponse
from django.template import loader

from django.contrib.auth.models import User, Group
from core.models import Analysis, RiskInstance, Mitigation, RiskAcceptance
from general.models import ParentRisk, Project, ProjectsGroup
from .forms import *

# Create your views here.
def index(request):
    template = loader.get_template('back_office/index.html')
    context = {
        'hello': 'world',
    }
    return HttpResponse(template.render(context, request))

class ProjectListView(PermissionRequiredMixin, ListView):
    permission_required = 'general.view_project'
    template_name = 'back_office/project_list.html'
    context_object_name = 'projects'

    ordering = 'id'
    paginate_by = 10
    model = Project

class ProjectsGroupListView(PermissionRequiredMixin, ListView):
    permission_required = 'general.view_projectsgroup'
    template_name = 'back_office/project_domain_list.html'
    context_object_name = 'domains'

    ordering = 'id'
    paginate_by = 10
    model = ProjectsGroup

class RiskAnalysisListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_analysis'
    template_name = 'back_office/analysis_list.html'
    context_object_name = 'analyses'

    ordering = 'id'
    paginate_by = 10
    model = Analysis

    def get_queryset(self):
        if not self.request.user.is_superuser:
            agg_data = Analysis.objects.filter(auditor=self.request.user).order_by('is_draft', 'id')
        else:
            agg_data = Analysis.objects.all().order_by('is_draft', 'id')
        return agg_data

class RiskInstanceListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_riskinstance'
    template_name = 'back_office/ri_list.html'
    context_object_name = 'instances'

    ordering = 'id'
    paginate_by = 10
    model = RiskInstance

    def get_queryset(self):
        if not self.request.user.is_superuser:
            agg_data = RiskInstance.objects.filter(analysis__auditor=self.request.user).order_by('id')
        else:
            agg_data = RiskInstance.objects.all().order_by('id')
        return agg_data

class MitigationListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_mitigation'
    template_name = 'back_office/mtg_list.html'
    context_object_name = 'mitigations'

    ordering = 'id'
    paginate_by = 10
    model = Mitigation

    def get_queryset(self):
        if not self.request.user.is_superuser:
            agg_data = Mitigation.objects.filter(risk_instance__analysis__auditor=self.request.user).order_by('risk_instance', 'id')
        else:
            agg_data = Mitigation.objects.all().order_by('risk_instance', 'id')
        return agg_data

class RiskAcceptanceListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_riskacceptance'
    template_name = 'back_office/acceptance_list.html'
    context_object_name = 'acceptances'

    ordering = 'id'
    paginate_by = 10
    model = RiskAcceptance

    def get_queryset(self):
        if not self.request.user.is_superuser:
            agg_data = RiskAcceptance.objects.filter(risk_instance__analysis__auditor=self.request.user).order_by('type', 'id')
        else:
            agg_data = RiskAcceptance.objects.all().order_by('type', 'id')
        return agg_data

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

class ProjectsGroupCreateView(PermissionRequiredMixin, CreateView):
    permission_required = 'general.add_projectsgroup'
    model = ProjectsGroup
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = ProjectsGroupUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('pd-list')

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
        context['instances'] = RiskInstance.objects.all()
        context['crumbs'] = ['Analyses']
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
        context['mitigations'] = Mitigation.objects.all()
        context['crumbs'] = ['Risk Scenarios']
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

class ProjectsGroupUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = 'general.change_projectsgroup'
    model = ProjectsGroup
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = ProjectsGroupUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.all()
        crumbs = ['Projects Domains']
        context['crumbs'] = crumbs
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
        context['analyses'] = Analysis.objects.all()
        crumbs = ['Projects']
        context['crumbs'] = crumbs
        return context

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

class ParentRiskListView(PermissionRequiredMixin, ListView):
    permission_required = 'core.view_parentrisk'
    template_name = 'back_office/threat_list.html'
    context_object_name = 'threats'

    ordering = 'id'
    paginate_by = 10
    model = ParentRisk