from typing import Optional
from core.models import Threat
from iam.models import RoleAssignment

from .utils import *
from .forms import *

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView

from core.views import BaseContextMixin
from iam.models import RoleAssignment

from .forms import *
from .utils import *

from core.helpers import get_sorted_requirements_and_groups
from .helpers import preview_library


class LibraryListView(BaseContextMixin, FormView):
    template_name = 'library/library_list.html'
    form_class = UploadFileForm
    success_url = reverse_lazy('library-list')

    def get_queryset(self):
        qs = get_available_libraries()
        for lib in qs:
            lib['requirements'] = len(lib['objects'].get('framework').get('requirements')) if lib['objects'].get('framework').get('requirements') else 0
            lib['threats'] = len(lib['objects'].get('threats')) if lib['objects'].get('threats') else 0
            lib['security_functions'] = len(lib['objects'].get('security_functions')) if lib['objects'].get('security_functions') else 0
            lib['objects'].clear()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['libraries'] = self.get_queryset()
        context['threat_import'] = RoleAssignment.is_access_allowed(self.request.user, Permission.objects.get(codename="add_threat"), Folder.get_root_folder())
        context['securityfunction_import'] = RoleAssignment.is_access_allowed(self.request.user, Permission.objects.get(codename="add_securityfunction"), Folder.get_root_folder())
        context['form'] = UploadFileForm()
        return context

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = request.FILES.getlist('file')
        for f in files:
            try:
                validate_file_extension(f)
                library = yaml.safe_load(f)
                import_library_view(request, library)
                return self.form_valid(form)
            except ValidationError as e:
                messages.error(request, _("Failed to import file: {}. {}").format(f.name, e.message % e.params))
                return self.form_invalid(form)


class LibraryDetailView(BaseContextMixin, TemplateView):
    template_name = 'library/library_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        library = get_library(urn=kwargs['library_urn'])
        preview = preview_library(library)
        context["tree"] = get_sorted_requirements_and_groups(
            preview.get('requirements'),
            preview.get('requirement_groups'))
        context['library'] = library
        context['can_import'] = True # TODO: check if user has permission to import
        context['crumbs'] = {'library-list': _('Libraries')}
        return context


def import_default_library(request, library_urn: str):
    library = get_library(urn=library_urn)
    try:
        import_library_view(request, library)
    except Exception as e:
        raise e
    return redirect("library-list")