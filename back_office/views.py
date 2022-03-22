
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView, CreateView
from django.http import HttpResponse, HttpResponseRedirect, request
from django.template import loader

from core.models import Analysis, RiskInstance, Mitigation, RiskAcceptance
from .forms import *

# Create your views here.
def index(request):
    template = loader.get_template('back_office/index.html')
    context = {
        'hello': 'world',
    }
    return HttpResponse(template.render(context, request))

class RiskAnalysisListView(ListView):
    template_name = 'back_office/analysis_list.html'
    context_object_name = 'analyses'


    ordering = 'id'
    paginate_by = 10
    model = Analysis

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


class RiskAnalysisCreateView(CreateView):
    model = Analysis
    template_name = 'back_office/ra_create.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('ra-list')

class RiskInstanceCreateView(CreateView):
    model = RiskInstance
    template_name = 'back_office/ri_create.html'
    context_object_name = 'instance'
    form_class = RiskInstanceCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('ri-list')

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
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('ra-list')
   
class RiskInstanceUpdateView(UpdateView):
    model = RiskInstance
    template_name = 'back_office/ri_update.html'
    context_object_name = 'instance'
    form_class = RiskInstanceUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('ra-update', kwargs = {'pk': self.object.analysis.id})
    