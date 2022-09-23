from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, UpdateView, CreateView, DeleteView
from django.http import HttpResponse
from django.template import loader
from django.utils.translation import gettext_lazy as _
from datetime import date
from iam.models import UserGroup, Role, RoleAssignment
from django.contrib.auth.views import PasswordChangeView
from core.models import Analysis, RiskScenario, SecurityMeasure, RiskAcceptance
from iam.forms import *
from core.forms import *
from .forms import *
from .filters import *

from core.helpers import get_counters, risks_count_per_level, security_measure_per_status, measures_to_review, acceptances_to_review
from django.contrib.auth import get_user_model

User = get_user_model()

def index(request):
    template = loader.get_template('back_office/index.html')

    context = {
        "counters": get_counters(request.user),
        "risks_level": risks_count_per_level(request.user),
        "security_measure_status": security_measure_per_status(request.user),
        "measures_to_review": measures_to_review(request.user),
        "acceptances_to_review": acceptances_to_review(request.user),
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
        context['asset_create_form'] = AssetForm
        return context

    def get_queryset(self):
        return True

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class ProjectListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/project_list.html'
    context_object_name = 'projects'

    ordering = 'id'
    paginate_by = 10
    model = Project

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Project)
        qs = self.model.objects.filter(id__in=object_ids_view)
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
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class ProjectCreateView(UserPassesTestMixin, CreateView):
    model = Project
    template_name = 'back_office/project_create.html'
    context_object_name = 'project'
    form_class = ProjectForm

    def get_success_url(self) -> str:
        return reverse_lazy('project-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename='add_project'))


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
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename='add_project'))


class ProjectUpdateView(UserPassesTestMixin, UpdateView):
    model = Project
    template_name = 'back_office/project_update.html'
    context_object_name = 'project'
    form_class = ProjectForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analyses'] = Analysis.objects.filter(
            project=self.get_object()).order_by('is_draft', 'id')
        context['analysis_create_form'] = RiskAnalysisCreateForm(
            initial={'project': get_object_or_404(Project, id=self.kwargs['pk']), 'auditor': self.request.user})
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
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename='change_project'), folder=self.get_object().folder)


class ProjectDeleteView(UserPassesTestMixin, DeleteView):
    model = Project
    success_url = reverse_lazy('project-list')
    template_name = 'back_office/snippets/project_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('project-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_project"))


class AssetListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/asset_list.html'
    context_object_name = 'assets'

    ordering = 'id'
    paginate_by = 10
    model = Asset

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Asset)
        qs = self.model.objects.filter(id__in=object_ids_view)
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
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class AssetCreateViewModal(UserPassesTestMixin, CreateView):
    model = Asset
    template_name = 'back_office/snippets/asset_create_modal.html'
    context_object_name = 'asset'
    form_class = AssetForm

    def get_success_url(self):
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_asset"))


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
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_asset"))


class AssetDeleteView(UserPassesTestMixin, DeleteView):
    model = Asset
    success_url = reverse_lazy('asset-list')
    template_name = 'back_office/snippets/asset_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('asset-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_asset"))


class FolderListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/project_domain_list.html'
    context_object_name = 'domains'

    ordering = 'id'
    paginate_by = 10
    model = Folder

    def get_queryset(self):
        folders_list = RoleAssignment.get_accessible_folders(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Folder.ContentType.DOMAIN)
        qs = self.model.objects.filter(id__in=folders_list)
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
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class FolderCreateView(UserPassesTestMixin, CreateView):
    model = Folder
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = FolderUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('pd-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_folder"))


class FolderCreateViewModal(UserPassesTestMixin, CreateView):
    model = Folder
    template_name = 'back_office/snippets/projects_domain_create_modal.html'
    context_object_name = 'domain'
    form_class = FolderUpdateForm

    def get_success_url(self) -> str:
        folder = Folder.objects.latest("id")
        auditors = UserGroup.objects.create(
            name="BI-UG-AUD", folder=folder, builtin=True)
        analysts = UserGroup.objects.create(
            name="BI-UG-ANA", folder=folder, builtin=True)
        managers = UserGroup.objects.create(
            name="BI-UG-DMA", folder=folder, builtin=True)
        ra1 = RoleAssignment.objects.create(user_group=auditors, role=Role.objects.get(name="BI-RL-AUD"), builtin=True, folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
        ra1.perimeter_folders.add(folder)
        ra2 = RoleAssignment.objects.create(user_group=analysts, role=Role.objects.get(name="BI-RL-ANA"), builtin=True, folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
        ra2.perimeter_folders.add(folder)
        ra3 = RoleAssignment.objects.create(user_group=managers, role=Role.objects.get(name="BI-RL-DMA"), builtin=True, folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
        ra3.perimeter_folders.add(folder)
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_folder"))


class FolderUpdateView(UserPassesTestMixin, UpdateView):
    model = Folder
    template_name = 'back_office/pd_update.html'
    context_object_name = 'domain'
    form_class = FolderUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(folder=self.get_object())
        context['crumbs'] = {'pd-list': _('Projects domains')}
        context['project_create_form'] = ProjectForm(
            initial={'domain': get_object_or_404(Folder, id=self.kwargs['pk'])})
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('pd-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_folder"), folder=self.get_object())


class FolderDeleteView(UserPassesTestMixin, DeleteView):
    model = Folder
    success_url = reverse_lazy('pd-list')
    template_name = 'back_office/snippets/projects_domain_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('pd-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_folder"))


class RiskAnalysisListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/analysis_list.html'
    context_object_name = 'analyses'

    ordering = 'id'
    paginate_by = 10
    model = Analysis

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Analysis)
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
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
        # self.model._meta.verbose_name # TODO: Find a way to get unlocalized model verbose_name, as localization may break stuff e.g. urls
        context['model'] = 'analysis'
        context['analysis_create_form'] = RiskAnalysisCreateForm
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class RiskAnalysisCreateView(UserPassesTestMixin, CreateView):
    model = Analysis
    template_name = 'back_office/ra_create.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_analysis"))


class RiskAnalysisCreateViewModal(UserPassesTestMixin, CreateView):
    model = Analysis
    template_name = 'back_office/snippets/analysis_create_modal.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_analysis"))


class RiskAnalysisUpdateView(UserPassesTestMixin, UpdateView):
    model = Analysis
    template_name = 'back_office/ra_update.html'
    context_object_name = 'analysis'
    form_class = RiskAnalysisUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['risk_scenario_create_form'] = RiskScenarioCreateForm(
            initial={'analysis': get_object_or_404(Analysis, id=self.kwargs['pk'])})
        context['scenarios'] = RiskScenario.objects.filter(
            analysis=self.get_object()).order_by('id')
        context['suggested_measures'] = SecurityMeasure.objects.all().order_by('id')
        context['crumbs'] = {'ra-list': _('Analyses')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('ra-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_analysis"),
            folder=Folder.get_folder(self.get_object()))


class RiskAnalysisDeleteView(UserPassesTestMixin, DeleteView):
    model = Analysis
    success_url = reverse_lazy('ra-list')
    template_name = 'back_office/snippets/ra_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('ra-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_analysis"))


class RiskScenarioListView(UserPassesTestMixin, ListView):
    permission_required = 'core.view_riskscenario'
    template_name = 'back_office/ri_list.html'
    context_object_name = 'scenarios'

    ordering = 'id'
    paginate_by = 10
    model = RiskScenario

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskScenario)
        qs = self.model.objects.filter(id__in=object_ids_view)
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
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class RiskScenarioCreateView(UserPassesTestMixin, CreateView):
    model = RiskScenario
    template_name = 'back_office/ri_create.html'
    context_object_name = 'scenario'
    form_class = RiskScenarioCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['analysis'] = get_object_or_404(
            Analysis, id=self.kwargs['parent_analysis'])

        return context

    def form_valid(self, form: RiskScenarioCreateForm) -> HttpResponse:
        if form.is_valid():
            form.scenario.analysis = get_object_or_404(
                Analysis, id=self.kwargs['parent_analysis'])
            return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('ra-update', kwargs={'pk': get_object_or_404(Analysis, id=self.kwargs['parent_analysis']).id})

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_riskscenario"))


class RiskScenarioCreateViewModal(UserPassesTestMixin, CreateView):
    model = RiskScenario
    template_name = 'back_office/ri_create_modal.html'
    context_object_name = 'scenario'
    form_class = RiskScenarioCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_riskscenario"))


class RiskScenarioUpdateView(UserPassesTestMixin, UpdateView):
    model = RiskScenario
    template_name = 'back_office/ri_update.html'
    context_object_name = 'scenario'
    form_class = RiskScenarioUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['security_measures'] = self.get_object().security_measures.all()
        context['existing_security_measures'] = SecurityMeasure.objects.filter(project=self.get_object().analysis.project)
        context['crumbs'] = {'ri-list': _('Risk scenarios')}
        context['measure_create_form'] = SecurityMeasureCreateForm(
            initial={'risk_scenario': get_object_or_404(RiskScenario, id=self.kwargs['pk'])})
        return context

    def get_success_url(self) -> str:
        if "select_measures" in self.request.POST:
            return reverse_lazy('ri-update', kwargs={'pk': self.kwargs['pk']})
        else:
            if (self.request.POST.get('next', '/') == ""):
                return reverse_lazy('ri-list')
            else:
                return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_riskscenario"), folder=self.get_object().analysis.project.folder)


class RiskScenarioUpdateViewModal(UserPassesTestMixin, UpdateView):
    model = RiskScenario
    template_name = 'back_office/ri_update_modal.html'
    context_object_name = 'scenario'
    form_class = RiskScenarioModalUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy('ri-update', kwargs={'pk': self.kwargs['pk']})

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_riskscenario"), folder=self.get_object().analysis.project.folder)


class RiskScenarioDeleteView(UserPassesTestMixin, DeleteView):
    model = RiskScenario
    success_url = reverse_lazy('ri-list')
    template_name = 'back_office/snippets/risk_scenario_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('ri-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_riskscenario"))


class SecurityMeasureListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/mtg_list.html'
    context_object_name = 'measures'

    ordering = 'id'
    paginate_by = 10
    model = SecurityMeasure

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = SecurityMeasureFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['measure_create_form'] = SecurityMeasureCreateForm
        return context

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, SecurityMeasure)
        qs = self.model.objects.filter(id__in=object_ids_view)
        filtered_list = SecurityMeasureFilter(self.request.GET, queryset=qs)
        return filtered_list.qs
        # if not self.request.user.is_superuser:
        #     agg_data = SecurityMeasure.objects.filter(risk_scenario__analysis__auditor=self.request.user).order_by('id')
        # else:
        #     agg_data = SecurityMeasure.objects.all().order_by('id')
        # return agg_data

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class SecurityMeasureCreateViewModal(UserPassesTestMixin, CreateView):
    permission_required = 'core.add_securitymeasure'
    model = SecurityMeasure
    template_name = 'back_office/snippets/measure_create_modal.html'
    context_object_name = 'measure'
    form_class = SecurityMeasureCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_securitymeasure"))


class SecurityMeasureUpdateView(UserPassesTestMixin, UpdateView):
    model = SecurityMeasure
    template_name = 'back_office/mtg_update.html'
    context_object_name = 'security_measure'
    form_class = SecurityMeasureUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['risk_scenarios'] = RiskScenario.objects.filter(security_measures=self.get_object())
        context['crumbs'] = {'mtg-list': _('Security measures')}
        return context

    def get_success_url(self) -> str:
        if (self.request.POST.get('next', '/') == ""):
            return reverse_lazy('mtg-list')
        else:
            return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_securitymeasure"), folder=self.get_object().project.folder)


class SecurityMeasureDeleteView(UserPassesTestMixin, DeleteView):
    model = SecurityMeasure
    success_url = reverse_lazy('mtg-list')
    template_name = 'back_office/snippets/measure_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('mtg-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_securitymeasure"))


class SecurityFunctionListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/security_function_list.html'
    context_object_name = 'functions'

    ordering = 'id'
    paginate_by = 10
    model = SecurityFunction

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, SecurityFunction)
        qs = self.model.objects.filter(id__in=object_ids_view)
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
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class SecurityFunctionCreateViewModal(UserPassesTestMixin, CreateView):
    model = SecurityFunction
    template_name = 'back_office/snippets/security_function_create_modal.html'
    context_object_name = 'function'
    form_class = SecurityFunctionCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="add_securityfunction"))


class SecurityFunctionUpdateView(UserPassesTestMixin, UpdateView):
    model = SecurityFunction
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
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="change_securityfunction"))


class SecurityFunctionDeleteView(UserPassesTestMixin, DeleteView):
    model = SecurityFunction
    success_url = reverse_lazy('security-function-list')
    template_name = 'back_office/snippets/security_function_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('security-function-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user = self.request.user, perm = Permission.objects.get(codename="delete_securityfunction"))


class ThreatListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/threat_list.html'
    context_object_name = 'threats'

    ordering = 'id'
    paginate_by = 10
    model = Threat

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, Threat)
        qs = self.model.objects.filter(id__in=object_ids_view)
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
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class ThreatCreateViewModal(UserPassesTestMixin, CreateView):
    model = Threat
    template_name = 'back_office/snippets/threat_create_modal.html'
    context_object_name = 'threat'
    form_class = ThreatCreateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_threat"))


class ThreatUpdateView(UserPassesTestMixin, UpdateView):
    model = Threat
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
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_threat"))


class ThreatDeleteView(UserPassesTestMixin, DeleteView):
    model = Threat
    success_url = reverse_lazy('threat-list')
    template_name = 'back_office/snippets/threat_delete_modal.html'

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_threat"))


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
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, RiskAcceptance)
        qs = self.model.objects.filter(id__in=object_ids_view)
        filtered_list = RiskAcceptanceFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class RiskAcceptanceCreateViewModal(UserPassesTestMixin, CreateView):
    model = RiskAcceptance
    template_name = 'back_office/snippets/risk_acceptance_create_modal.html'
    context_object_name = 'acceptance'
    form_class = RiskAcceptanceCreateUpdateForm

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_riskacceptance"))


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
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_riskacceptance"), folder=self.get_object().risk_scenario.analysis.project.folder)


class RiskAcceptanceDeleteView(UserPassesTestMixin, DeleteView):
    model = RiskAcceptance
    success_url = reverse_lazy('acceptance-list')
    template_name = 'back_office/snippets/risk_acceptance_delete_modal.html'

    success_url = reverse_lazy('acceptance-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_riskacceptance"))


class MyProfileView(UserPassesTestMixin, UpdateView):
    template_name = 'back_office/user_update.html'
    context_object_name = 'user'
    form_class = MyProfileUpdateForm

    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = get_object_or_404(User, pk=self.kwargs['pk'])
        print('DEBUG: User =', get_object_or_404(User, pk=self.kwargs['pk']))
        return kwargs

    def get_success_url(self) -> str:
        return self.request.POST.get('next', '/')
    
    def test_func(self):
        return self.request.user == get_object_or_404(User, pk=self.kwargs['pk'])

class UserListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/user_list.html'
    context_object_name = 'users'

    ordering = 'id'
    paginate_by = 10
    model = User

    def get_queryset(self):
        qs = self.model.objects.all().order_by(
            '-is_active', '-is_superuser', 'email', 'id')
        filtered_list = UserFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserFilter(self.request.GET, queryset)
        context['filter'] = filter
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="view_user"))


class UserCreateView(UserPassesTestMixin, CreateView):
    template_name = 'back_office/user_create.html'
    context_object_name = 'user'
    form_class = UserCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_user"))


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
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_user"))


class UserDeleteView(UserPassesTestMixin, DeleteView):
    model = User
    success_url = reverse_lazy('user-list')
    template_name = 'back_office/snippets/user_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('user-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_user"))


class UserGroupListView(UserPassesTestMixin, ListView):
    template_name = 'back_office/group_list.html'
    context_object_name = 'user_groups'

    ordering = 'id'
    paginate_by = 10
    model = UserGroup

    def get_queryset(self):
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, UserGroup
        )
        qs = self.model.objects.filter(id__in=object_ids_view)
        filtered_list = UserGroupFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserGroupFilter(self.request.GET, queryset)
        context['filter'] = filter
        (context['object_ids_view'], context['object_ids_change'], context['object_ids_delete']) = RoleAssignment.get_accessible_objects(
            Folder.objects.get(content_type=Folder.ContentType.ROOT), self.request.user, UserGroup
        )
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename='view_usergroup'))


class UserGroupCreateView(UserPassesTestMixin, CreateView):
    template_name = 'back_office/group_create.html'
    context_object_name = 'user_group'
    form_class = UserGroupCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('user_group-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_usergroup"))


class UserGroupUpdateView(UserPassesTestMixin, UpdateView):
    template_name = 'back_office/group_update.html'
    context_object_name = 'user_group'
    form_class = UserGroupUpdateForm

    model = UserGroup

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.exclude(user_groups=self.get_object())
        context["associated_users"] = User.objects.filter(
            user_groups=self.get_object())
        context["crumbs"] = {'user_group-list': _('UserGroups')}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('user_group-list')

    def test_func(self):
        user_group = self.get_object()
        return not (user_group.builtin) and RoleAssignment.is_access_allowed(user=self.request.user,
                                                                        perm=Permission.objects.get(codename="change_usergroup"),
                                                                        folder=Folder.get_folder(user_group))


class UserGroupDeleteView(UserPassesTestMixin, DeleteView):
    model = UserGroup
    success_url = reverse_lazy('user_group-list')
    template_name = 'back_office/snippets/group_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('user_group-list')

    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_usergroup"))


class RoleAssignmentListView(UserPassesTestMixin, ListView):
    permission_required = 'back_office.view_roleassignment'
    template_name = 'back_office/role_list.html'
    context_object_name = 'assignments'

    ordering = 'id'
    paginate_by = 10
    model = RoleAssignment

    def get_queryset(self):
        qs = self.model.objects.all().order_by('id')
        filtered_list = UserGroupFilter(self.request.GET, queryset=qs)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserGroupFilter(self.request.GET, queryset)
        context['filter'] = filter
        context['roles'] = Role.objects.all().order_by('id')
        return context

    def test_func(self):
        return True


class RoleAssignmentCreateView(UserPassesTestMixin, CreateView):
    permission_required = 'back_office.add_roleassignment'
    template_name = 'back_office/role_assignment_create.html'
    context_object_name = 'assignment'
    form_class = RoleAssignmentCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'role-list': _('Role assignment')}
        return context
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="add_roleassignment"))


class RoleAssignmentDeleteView(UserPassesTestMixin, DeleteView):
    permission_required = 'back_office.delete_roleassignment'
    model = RoleAssignment
    success_url = reverse_lazy('role-list')
    template_name = 'back_office/snippets/role_assignment_delete_modal.html'

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')
    
    def test_func(self):
        return RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="delete_roleassignment"))


class RoleAssignmentUpdateView(UserPassesTestMixin, UpdateView):
    permission_required = 'auth.change_role'
    template_name = 'back_office/role_update.html'
    context_object_name = 'role'
    form_class = RoleAssignmentUpdateForm

    model = Role

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {'user_group-list': _('UserGroups')}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy('role-list')

    def test_func(self):
        ra = self.get_object()
        return not (ra.builtin) and RoleAssignment.is_access_allowed(user=self.request.user, 
                perm=Permission.objects.get(codename="change_roleassignment"), folder=Folder.get_folder(ra))


class UserPasswordChangeView(PasswordChangeView):
    """ view to change user password """
    template_name = 'back_office/password_change.html'
    form_class = UserPasswordChangeForm
    model = User

    def get_success_url(self) -> str:
        return reverse_lazy("me-update", kwargs = {'pk': self.request.user.id})

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
