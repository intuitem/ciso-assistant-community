
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView
from django.http import HttpResponse
from django.template import loader

from core.models import Analysis, RiskInstance, Mitigation, RiskAcceptance
from .forms import RiskAnalysisUpdateForm, RiskInstanceUpdateForm

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


class RiskAnalysisUpdateView(UpdateView):
    model = Analysis
    template_name = 'back_office/ra_update.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisUpdateForm
    # form_class = RiskAnalysisUpdateForm

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
    