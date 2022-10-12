from typing import Optional
from core.models import RiskMatrix, Threat

from .utils import *

from django.views.generic import TemplateView, ListView

class PackageListView(ListView):
    template_name = 'library/package_list.html'
    paginate_by = 10
    context_object_name: Optional[str] = 'packages'

    def get_queryset(self):
        qs = get_available_packages()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class PackageDetailView(TemplateView):
    template_name = 'library/package_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        package = get_package(kwargs['package'])
        context['package'] = package
        return context
