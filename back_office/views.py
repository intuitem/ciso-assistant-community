
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView, CreateView, DeleteView
from django.http import HttpResponse, HttpResponseRedirect, request
from django.template import loader

from django.contrib.auth.models import User, Group
from core.models import Analysis, RiskInstance, Mitigation, RiskAcceptance
from general.models import Project, ProjectsGroup
from .forms import *

# Create your views here.
def index(request):
    template = loader.get_template('back_office/index.html')
    context = {
        'hello': 'world',
    }
    return HttpResponse(template.render(context, request))

class ProjectTreeView(ListView):
    template_name = 'back_office/project_tree.html'
    context_object_name = 'projects'

    ordering = 'id'
    paginate_by = 10
    model = Project

class ProjectsGroupListView(ListView):
    template_name = 'back_office/project_domain_list.html'
    context_object_name = 'domains'

    ordering = 'id'
    paginate_by = 10
    model = ProjectsGroup

class RiskAnalysisListView(ListView):
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

class RiskInstanceListView(ListView):
    template_name = 'back_office/ri_list.html'
    context_object_name = 'instances'

    ordering = 'id'
    paginate_by = 10
    model = RiskInstance

class MitigationListView(ListView):
    template_name = 'back_office/mtg_list.html'
    context_object_name = 'mitigations'

    ordering = 'id'
    paginate_by = 10
    model = Mitigation

class RiskAcceptanceListView(ListView):
    template_name = 'back_office/acceptance_list.html'
    context_object_name = 'acceptances'

    ordering = 'id'
    paginate_by = 10
    model = RiskAcceptance

class UserListView(ListView):
    template_name = 'back_office/user_list.html'
    context_object_name = 'users'

    ordering = 'id'
    paginate_by = 10
    model = User

class UserCreateView(CreateView):
    template_name = 'back_office/user_create.html'
    context_object_name = 'user'
    form_class = UserCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')

class GroupListView(ListView):
    template_name = 'back_office/group_list.html'
    context_object_name = 'groups'

    ordering = 'id'
    paginate_by = 10
    model = Group

class RiskAnalysisCreateView(CreateView):
    model = Analysis
    template_name = 'back_office/ra_create.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('ra-list')

class ProjectsGroupCreateView(CreateView):
    model = ProjectsGroup
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = ProjectsGroupUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('pd-list')

class RiskInstanceCreateView(CreateView):
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

class RiskInstanceCreateViewModal(CreateView):
    model = RiskInstance
    template_name = 'back_office/ri_create_modal.html'
    context_object_name = 'instance'
    form_class = RiskInstanceCreateForm

class RiskAnalysisUpdateView(UpdateView):
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

class RiskAnalysisDeleteView(DeleteView):
    model = Analysis
    success_url = reverse_lazy('ra-list')
    template_name = 'back_office/snippets/ra_delete_modal.html'
   
class RiskInstanceUpdateView(UpdateView):
    model = RiskInstance
    template_name = 'back_office/ri_update.html'
    context_object_name = 'instance'
    form_class = RiskInstanceUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mitigations'] = Mitigation.objects.all()
        context['crumbs'] = ['Risk Instances']
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('ra-update', kwargs = {'pk': self.object.analysis.id})

class MitigationUpdateView(UpdateView):
    model = Mitigation
    template_name = 'back_office/mtg_update.html'
    context_object_name = 'mitigation'
    form_class = MitigationUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('ri-update', kwargs = {'pk': self.object.risk_instance.id})

class ProjectsGroupUpdateView(UpdateView):
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

class ProjectUpdateView(UpdateView):
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
        return reverse_lazy('project-tree')

class ProjectCreateView(CreateView):
    model = Project
    template_name = 'back_office/project_create.html'
    context_object_name = 'project'
    form_class = ProjectForm

    def get_success_url(self) -> str:
        return reverse_lazy('project-tree')