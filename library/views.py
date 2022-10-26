from typing import Optional
from core.models import RiskMatrix, Threat
from iam.models import RoleAssignment

from .utils import *
from .forms import *

from django.views.generic import TemplateView, ListView, FormView
from django.views import View
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

class PackageListView(FormView):
    template_name = 'library/package_list.html'
    form_class = UploadFileForm
    success_url = reverse_lazy('package-list')

    def get_queryset(self):
        qs = get_available_packages()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['packages'] = self.get_queryset()
        context['view_user'] = RoleAssignment.has_permission(self.request.user, "view_user")
        context['form'] = UploadFileForm()
        return context

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('file')
        if form.is_valid():
            for f in files:
                package = json.load(f)
                import_package(request, package)
            return self.form_valid(form)
        else:
            messages.error(request, f'Invalid form.')
            return self.form_invalid(form)


class PackageDetailView(TemplateView):
    template_name = 'library/package_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        package = get_package(kwargs['package'])
        context['package'] = package
        context['types'] = self.get_object_types(package)
        context['matrices'] = self.get_matrices(package)
        context['crumbs'] = {'package-list': _('Packages')}
        return context

    def get_object_types(self, package):
        types = set()
        for obj in package.get('objects'):
            types.add(obj['type'])
        return types

    def get_matrices(self, package):
        matrices = []
        for obj in package.get('objects'):
            if obj['type'] == 'matrix':
                matrices.append(obj)
        return matrices

def import_default_package(request, package_name):
    try:
        package = get_package(package_name)
        import_package(request, package)
    except:
        return redirect("package-list")
    return redirect("package-list")