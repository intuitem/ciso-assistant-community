import csv
import random
import time
import json
from datetime import date
from typing import Any, Optional
from uuid import UUID

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import Permission, User
from django.contrib.auth.views import (LoginView, PasswordChangeView,
                                       PasswordResetConfirmView)
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.functions import Concat
from django.db.models.query_utils import Q
from django.forms.models import BaseModelForm, model_to_dict
from django.http import HttpResponse, JsonResponse, FileResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from django.core.files.storage import default_storage

from ciso_assistant.settings import (LICENCE_DEPLOYMENT, LICENCE_EXPIRATION,
                                     LICENCE_SUPPORT, LICENCE_TYPE,
                                     PAGINATE_BY, RECAPTCHA_PUBLIC_KEY)
from core.forms import *
from core.helpers import (get_counters, compile_project_for_composer, get_sorted_requirements_and_groups, get_assessment_stats)
from core.models import *
from core.utils import RoleCodename, UserGroupCodename
from iam.forms import *
from iam.models import *

from .filters import *
from .forms import LoginForm
from .helpers import *

if RECAPTCHA_PUBLIC_KEY:
    from captcha.fields import ReCaptchaField

from datetime import datetime, timedelta
import mimetypes
import zipfile, tempfile, shutil

User = get_user_model()

MAX_USERS = 20

def is_ajax(request):
    """
    Method to know if it's an ajax request or not
    """
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"



# favicon management

@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> HttpResponse:
    file = (settings.BASE_DIR / "static" / "favicon.ico").open("rb")
    return FileResponse(file)

@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon_png(request: HttpRequest) -> HttpResponse:
    file = (settings.BASE_DIR / "static" / "favicon.png").open("rb")
    return FileResponse(file)


def get_pagination_url(request):
    url = request.path

    # Append the current GET parameters to the base URL
    get_params = request.GET.copy()
    if "page" in get_params:
        del get_params["page"]
    if get_params:
        return url + "?" + get_params.urlencode() + "&page="
    else:
        return url + "?page="


class BaseContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["change_usergroup"] = RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_usergroup"),
            folder=Folder.get_root_folder(),
        )
        context["view_user"] = RoleAssignment.has_permission(
            self.request.user, "view_user"
        )
        context["exceeded_users"] = (MAX_USERS - User.objects.all().count()) < 0

        # Set the pagination URL in the context
        context["pagination_url"] = get_pagination_url(self.request)

        return context

class GenericDetailView(BaseContextMixin, DetailView):
    template_name = "generic/detail.html"
    context_object_name = "object"

    exclude = ["id", "is_published", "locale_data"]

    field_order = []

    def get_object_data(self):
        object_data = model_to_dict(self.object)

        # sort fields according to field_order
        # put first fields in field_order, then the rest
        if self.field_order:
            object_data = {
                k: object_data[k] for k in self.field_order if k in object_data
            } | object_data

        for key in list(object_data.keys()):
            if key in self.exclude:
                object_data.pop(key)
                continue
            # replace uuids with their respective objects
            if object_data[key] and isinstance(object_data[key], UUID):
                object_data[key] = getattr(self.object, key)
            # get proper value display for choice fields
            if choices := self.get_object()._meta.get_field(key).choices:
                if key in object_data and object_data[key] in dict(choices):
                    object_data[key] = dict(choices)[object_data[key]]
            # convert all fields to iterables for template rendering
            if not isinstance(object_data[key], list):
                object_data[key] = [object_data[key]]
            # replace field names with their respective verbose names
            object_data[
                self.object._meta.get_field(key).verbose_name
            ] = object_data.pop(key)

        return object_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, self.model
        )
        context["change"] = self.object.id in object_ids_change
        context["delete"] = self.object.id in object_ids_delete
        if self.model is User:
            # NOTE: using has_permission() because get_accessible_objects() doesn't handle this object_type moreover there isn't scope
            context["change"] = RoleAssignment.has_permission(
                self.request.user, "change_user"
            )
            context["delete"] = RoleAssignment.has_permission(
                self.request.user, "delete_user"
            )
        context["data"] = self.get_object_data()
        context["crumbs"] = {
            self.model.__name__.lower()
            + "-list": self.model._meta.verbose_name_plural.capitalize()
        }

        return context


class SecurityMeasureDetailView(GenericDetailView):
    model = SecurityMeasure

    template_name = "core/detail/security_measure_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (
            context["evidence_ids_view"],
            context["evidence_ids_change"],
            context["evidence_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Evidence
        )
        context["crumbs"] = {"securitymeasure-list": _("Security measures")}
        context["evidences"] = Evidence.objects.filter(measure=self.object)
        context["evidence_create_form"] = EvidenceForm(
            initial={"measure": self.object}
        )
        context["requirement_assessments"] = RequirementAssessment.objects.filter(security_measures=self.object)
        return context


class FolderDetailView(GenericDetailView):
    model = Folder
    exclude = [
        "id",
        "content_type",
        "builtin",
        "hide_public_threat",
        "hide_public_security_function",
        "parent_folder",
        "locale_data",
    ]

    template_name = "core/detail/folder_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"folder-list": _("Projects domains")}
        context["projects"] = Project.objects.filter(folder=self.object)
        context["project_create_form"] = ProjectFormInherited(
            initial={"folder": self.object}
        )
        return context


class ProjectDetailView(GenericDetailView):
    model = Project

    template_name = "core/detail/project_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"project-list": _("Projects")}
        context["assessments"] = Assessment.objects.filter(project=self.object)
        context["assessment_create_form"] = AssessmentCreateForm(
            initial={"project": self.object}
        )
        return context


class ThreatDetailView(GenericDetailView):
    model = Threat
    exclude = ["id", "is_published", "folder", "locale_data"]


class SecurityFunctionDetailView(GenericDetailView):
    model = SecurityFunction
    exclude = ["id", "is_published", "folder", "locale_data"]


class UserDetailView(UserPassesTestMixin, GenericDetailView):
    model = User
    exclude = ["id", "password", "first_login"]

    def test_func(self):
        return (
            RoleAssignment.has_permission(user=self.request.user, codename="view_user")
            or self.request.user == self.get_object()
        )


class UserLogin(LoginView):
    template_name = "registration/login.html"
    form_class = LoginForm

    def form_valid(self, form):
        return super().form_valid(form)


def password_reset_request(request):
    context = {}
    if request.method == "POST":
        now = datetime.now()
        password_reset_form = ResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data["email"]
            associated_users = User.objects.filter(email=data)
            if associated_users and associated_users.exists():
                associated_user = associated_users[0]
                try:
                    if "last_email_sent" in request.session:
                        last_sent_time = datetime.strptime(
                            request.session["last_email_sent"], "%Y-%m-%d %H:%M:%S"
                        )
                        elapsed_time = now - last_sent_time
                        # Vérifier si 30 secondes se sont écoulées depuis le dernier envoi de mail
                        if elapsed_time < timedelta(seconds=30):
                            # Si oui, retourner une réponse d'erreur
                            messages.error(
                                request,
                                _(
                                    "Please wait before requesting another password reset."
                                ),
                            )
                            context["password_reset_form"] = password_reset_form
                            return render(
                                request=request,
                                template_name="registration/password_reset.html",
                                context=context,
                            )
                    # Si tout est OK, envoyer l'email et enregistrer la date et l'heure actuelle dans la session
                    print("Sending reset mail to", data)
                    associated_user.mailing(
                        email_template_name="registration/password_reset_email.html",
                        subject=_("CISO Assistant: Password Reset"),
                    )
                    request.session["last_email_sent"] = now.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                except Exception as exception:
                    messages.error(
                        request, _("An error has occured, please try later.")
                    )
                    print("Exception:", exception)
                    password_reset_form = ResetForm()
                    context["password_reset_form"] = password_reset_form
                    return render(
                        request=request,
                        template_name="registration/password_reset.html",
                        context=context,
                    )
            else:
                # wrong, but we won't tell the requester for security reasons
                time.sleep(random.random() * 1.5)
                print("wrong email reset:", data)
            return redirect("/password_reset/done/")
        else:
            messages.error(request, _("Invalid email or captcha."))
    password_reset_form = ResetForm()
    context["password_reset_form"] = password_reset_form
    return render(
        request=request,
        template_name="registration/password_reset.html",
        context=context,
    )


class ResetPasswordConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    form_class = ResetConfirmForm


class FirstConnexionPasswordConfirmView(PasswordResetConfirmView):
    template_name = "registration/first_connexion_confirm.html"
    form_class = FirstConnexionConfirmForm


class SecurityMeasurePlanView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = "core/mp.html"
    context_object_name = "context"

    ordering = "-created_at"
    model = SecurityMeasure

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, self.model
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class SearchResults(ListView):
    context_object_name = "results"
    template_name = "core/search_results.html"

    def get_queryset(self):
        query = self.request.GET.get("q")
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, SecurityMeasure
        )
        mtg_list = SecurityMeasure.objects.filter(
            Q(name__icontains=query) | Q(security_function__name__icontains=query)
        ).filter(id__in=object_ids_view)[:10]
        return {"SecurityMeasure": mtg_list}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["change_usergroup"] = RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_usergroup"),
            folder=Folder.get_root_folder(),
        )
        context["view_user"] = RoleAssignment.has_permission(
            self.request.user, "view_user"
        )
        context["exceeded_users"] = (MAX_USERS - User.objects.all().count()) < 0
        return context


@login_required
def global_overview(request):
    template = "core/overview.html"

    (
        object_ids_view,
        object_ids_change,
        object_ids_delete,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), request.user, SecurityMeasure
    )
    viewable_projects = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), request.user, Project)[0]
    
    security_measure_status = {"values": [], "labels": []}
    
    color_map = {"open": "#93c5fd", "in_progress": "#fdba74",
                 "on_hold": "#f87171", "done": "#86efac"}
    for st in SecurityMeasure.MITIGATION_STATUS:
        count = SecurityMeasure.objects.filter(status=st[0]).count()
        v = {
            "value": count,
            "itemStyle": {"color": color_map[st[0]]}
        }
        security_measure_status["values"].append(v)
        security_measure_status["labels"].append(st[1])

    context = {
        "projects": Project.objects.filter(id__in=viewable_projects),
        "counters": get_counters(request.user),
        "today": date.today(),
        "measures_to_review": measures_to_review(request.user),
        "ord_security_measures": SecurityMeasure.objects.filter(id__in=object_ids_view).exclude(status='done').order_by('eta'),
        "viewable_measures": object_ids_view,
        "updatable_measures": object_ids_change,
        "security_measure_status": security_measure_status,
        "view_user": RoleAssignment.has_permission(
            request.user, "view_user"
        ),  # NOTE: Need to factorize with BaseContextMixin
        "exceeded_users": (MAX_USERS - User.objects.all().count()) < 0,
        "change_usergroup": RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="change_usergroup"),
            folder=Folder.get_root_folder(),
        ),
        "change_assessment": RoleAssignment.get_accessible_object_ids(
            user=request.user,
            folder=Folder.get_root_folder(),
            object_type=Assessment
        )[1]
    }

    return render(request, template, context)


def export_mp_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="MP.csv"'

    writer = csv.writer(response, delimiter=";")
    columns = [
        "measure_id",
        "measure_name",
        "measure_desc",
        "type",
        "security_function",
        "eta",
        "effort",
        "link",
        "status",
    ]
    writer.writerow(columns)
    (
        object_ids_view,
        object_ids_change,
        object_ids_delete,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), request.user, SecurityMeasure
    )
    for mtg in SecurityMeasure.objects.filter(id__in=object_ids_view):
        row = [
            mtg.id,
            mtg.name,
            mtg.description,
            mtg.type,
            mtg.security_function,
            mtg.eta,
            mtg.effort,
            mtg.link,
            mtg.status,
        ]
        writer.writerow(row)

    return response


class CreateViewModal(BaseContextMixin, CreateView):
    template_name: str = "core/fallback_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        url_name = self.model.__name__.lower()
        if self.model.__name__.lower() == "folder":
            plural_name = _("Projects domains")
            name = "projects domain"
        elif self.model.__name__.lower() == "securityfunction":
            plural_name = _("Security functions")
            name = "security function"
        else:
            plural_name = self.model._meta.verbose_name_plural
            name = self.model.__name__.replace("Risk", "Risk ").lower()
        context["cancel_url"] = reverse_lazy(f"{url_name}-list")
        context["crumbs"] = {url_name + "-list": plural_name}
        context["object_type"] = _("Add" + " " + name)
        return context

    def get_success_url(self):
        return self.request.POST.get(
            "next", reverse_lazy(f"{self.model.__name__.lower()}-list")
        )


class QuickStartView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = "core/quick_start.html"
    context_object_name = "quick-start"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["projects_domain_create_form"] = FolderUpdateForm
        context["project_create_form"] = ProjectForm
        context["securitymeasure_create_form"] = SecurityMeasureCreateForm
        context["threat_create_form"] = ThreatCreateForm
        context["security_function_create_form"] = SecurityFunctionCreateForm
        return context

    def get_queryset(self):
        return True

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class ProjectListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = "core/project_list.html"
    context_object_name = "projects"

    ordering = "-created_at"
    paginate_by = PAGINATE_BY
    model = Project

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Project
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = ProjectFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProjectFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        context["project_create_form"] = ProjectForm(user=self.request.user)
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Project
        )
        context["add_project"] = RoleAssignment.has_permission(
            self.request.user, "add_project"
        )
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class AssessmentListView(BaseContextMixin, ListView):
    model = Assessment
    template_name = "core/assessment_list.html"
    context_object_name = "assessments"
    ordering = "-created_at"
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Assessment
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = AssessmentFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = AssessmentFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        context["assessment_create_form"] = AssessmentCreateForm
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Assessment
        )
        context["add_assessment"] = RoleAssignment.has_permission(
            self.request.user, "add_assessment"
        )
        return context


class AssessmentCreateView(UserPassesTestMixin, CreateView):
    model = Assessment
    template_name = "core/fallback_form.html"
    context_object_name = "assessment"
    form_class = AssessmentCreateForm

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        self.object = form.save()
        assessment = self.object
        self.create_requirement_assessments(assessment)
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return self.request.POST.get("next", reverse_lazy("assessment-list"))

    def test_func(self):
        project = Project.objects.get(id=self.request.POST['project'])
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_assessment"),
            folder=Folder.objects.get(id=project.folder.id)
        )
    
    def create_requirement_assessments(self, assessment: Assessment):
        framework = assessment.framework
        requirements = Requirement.objects.filter(framework=framework)
        for requirement in requirements:
            RequirementAssessment.objects.create(
                assessment=assessment,
                requirement=requirement,
                folder=Folder.objects.get(id=assessment.project.folder.id)
            )


class AssessmentUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Assessment
    template_name = "core/assessment_update.html"
    context_object_name = "assessment"
    form_class = AssessmentUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"assessment-list": _("Assessments")}
        return context

    def get_success_url(self) -> str:
        if self.request.GET.get('next') == "":
            return reverse_lazy("assessment-list")
        else:
            return self.request.GET.get('next')

    def form_valid(self, form):
        project = self.object.project
        folder = project.folder
        if not RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_assessment"),
            folder=folder,
        ):
            raise PermissionDenied()
        return super().form_valid(form)

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_assessment"),
            folder=self.get_object().project.folder,
        )


class AssessmentDeleteView(UserPassesTestMixin, DeleteView):
    model = Assessment
    success_url = reverse_lazy("assessment-list")
    template_name = "core/fallback_form.html"

    def get_success_url(self) -> str:
        return reverse_lazy("assessment-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_assessment"),
            folder=self.get_object().project.folder,
        )


class FrameworkListView(BaseContextMixin, ListView):
    model = Framework
    template_name = "core/framework_list.html"
    context_object_name = "frameworks"
    ordering = "-created_at"
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Framework
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = FrameworkFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = FrameworkFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        context["framework_create_form"] = FrameworkForm
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Framework
        )
        context["add_framework"] = RoleAssignment.has_permission(
            self.request.user, "add_framework"
        )
        return context


class FrameworkDeleteView(UserPassesTestMixin, DeleteView):
    model = Framework
    success_url = reverse_lazy("framework-list")
    template_name = "core/fallback_form.html"

    def get_success_url(self) -> str:
        return reverse_lazy("framework-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_framework"),
            folder=self.get_object().folder,
        )


class RequirementListView(BaseContextMixin, ListView):
    model = Requirement
    template_name = "core/requirement_list.html"
    context_object_name = "requirements"
    ordering = "-created_at"
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Requirement
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = RequirementFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = RequirementFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        context["requirement_create_form"] = RequirementForm
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Requirement
        )
        context["add_requirement"] = RoleAssignment.has_permission(
            self.request.user, "add_requirement"
        )
        return context


class RequirementCreateView(UserPassesTestMixin, CreateView):
    model = Requirement
    template_name = "core/fallback_form.html"
    context_object_name = "requirement"
    form_class = RequirementForm

    def get_success_url(self) -> str:
        return reverse_lazy("requirement-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_requirement"),
            folder=Folder.objects.get(id=self.request.POST["folder"]),
        )


class RequirementUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Requirement
    template_name = "core/requirement_update.html"
    context_object_name = "requirement"
    form_class = RequirementForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"requirement-list": _("Requirements")}
        return context

    def get_success_url(self) -> str:
        if self.request.POST.get("next", "/") == "":
            return reverse_lazy("requirement-list")
        else:
            return self.request.POST.get("next", "/")

    def form_valid(self, form):
        folder = self.object.folder
        if not RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_requirement"),
            folder=folder,
        ):
            raise PermissionDenied()
        return super().form_valid(form)

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_requirement"),
            folder=self.get_object().folder,
        )


class RequirementDeleteView(UserPassesTestMixin, DeleteView):
    model = Requirement
    success_url = reverse_lazy("requirement-list")
    template_name = "core/fallback_form.html"

    def get_success_url(self) -> str:
        return reverse_lazy("requirement-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_requirement"),
            folder=self.get_object().folder,
        )


class EvidenceListView(BaseContextMixin, ListView):
    model = Evidence
    template_name = "core/evidence_list.html"
    context_object_name = "evidences"
    ordering = "-created_at"
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Evidence
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = EvidenceFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = EvidenceFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        context["evidence_create_form"] = EvidenceForm
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Evidence
        )
        context["add_evidence"] = RoleAssignment.has_permission(
            self.request.user, "add_evidence"
        )
        return context


class EvidenceCreateView(UserPassesTestMixin, CreateView):
    model = Evidence
    template_name = "core/fallback_form.html"
    context_object_name = "evidence"
    form_class = EvidenceForm

    def get_success_url(self) -> str:
        return reverse_lazy("evidence-list")

    def test_func(self):
        measure = SecurityMeasure.objects.get(id=self.request.POST["measure"])
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_evidence"),
            folder=Folder.objects.get(id=measure.folder.id),
        )


class EvidenceCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = Evidence
    context_object_name = "evidence"
    form_class = EvidenceForm

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_evidence"),
            folder=Folder.objects.get(id=SecurityMeasure.objects.get(id=self.request.POST["measure"]).folder.id),
        )



class EvidenceUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Evidence
    template_name = "core/evidence_update.html"
    context_object_name = "evidence"
    form_class = EvidenceUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"evidence-list": _("Evidences")}
        return context

    def get_success_url(self) -> str:
        print(self.request.GET.get('next'))
        if self.request.GET.get('next'):
            return self.request.GET.get('next')
        else:
            return reverse_lazy("evidence-list")

    def form_valid(self, form):
        folder = self.object.folder
        if not RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_evidence"),
            folder=folder,
        ):
            raise PermissionDenied()
        return super().form_valid(form)

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_evidence"),
            folder=self.get_object().folder,
        )


class EvidenceDeleteView(UserPassesTestMixin, DeleteView):
    model = Evidence
    success_url = reverse_lazy("evidence-list")
    template_name = "core/fallback_form.html"

    def get_success_url(self) -> str:
        return self.request.GET.get('next', reverse_lazy("evidence-list"))

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_evidence"),
            folder=self.get_object().folder,
        )


class RequirementAssessmentListView(BaseContextMixin, ListView):
    model = RequirementAssessment
    template_name = "core/requirementassessment_list.html"
    context_object_name = "assessments"
    ordering = "-created_at"
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, RequirementAssessment
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = RequirementAssessmentFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = RequirementAssessmentFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        context["requirementassessment_create_form"] = RequirementAssessmentForm
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, RequirementAssessment
        )
        context["add_requirementassessment"] = RoleAssignment.has_permission(
            self.request.user, "add_requirementassessment"
        )
        return context


class RequirementAssessmentCreateView(UserPassesTestMixin, CreateView):
    model = Requirement
    template_name = "core/fallback_form.html"
    context_object_name = "assessment"
    form_class = RequirementAssessmentForm

    def get_success_url(self) -> str:
        if self.request.POST.get("next", "/") == "":
            return reverse_lazy("assessment-list")
        else:
            return self.request.POST.get("next", "/")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_requirementassessment"),
            folder=Folder.objects.get(id=self.request.POST["folder"]),
        )


class RequirementAssessmentUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = RequirementAssessment
    template_name = "core/requirementassessment_update.html"
    context_object_name = "requirementassessment" #TODO: change to requirementassessment probably
    form_class = RequirementAssessmentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ra"] = self.object
        context["crumbs"] = {'assessment-list': _('Assessments'), 'assessment-detail': (self.get_object().assessment, self.get_object().assessment_id)}
        context['security_measures'] = self.get_object().security_measures.all().order_by('name')
        context['measure_create_form'] = SecurityMeasureCreateFormInherited(
            recommended_security_functions = self.get_object().requirement.security_functions.all(),
            initial={'folder': get_object_or_404(Folder, id=self.get_object().assessment.project.folder.id)})
        context['measures_select_form'] = SecurityMeasureSelectForm(
            recommended_security_measures = SecurityMeasure.objects.filter(security_function__in=self.get_object().requirement.security_functions.all()),
            initial={
                'security_measures': self.get_object().security_measures.all()},
        )
        context['evidence_create_form'] = EvidenceFormInherited(
            initial={
                'measure': self.request.session.get('last_created_measure')
            }
        )
        custom_ordering = Case(
                When(id__in=SecurityMeasure.objects.filter(security_function__in=self.get_object().requirement.security_functions.all()), then=Value(0)),
                When(id__in=self.get_object().security_measures.all(), then=Value(1)),
                default=Value(2),
                output_field=IntegerField()
            )
        context['measures_select_form'].fields['security_measures'].queryset = SecurityMeasure.objects.filter(
            Q(folder=self.get_object().assessment.project.folder) | Q(folder=Folder.get_root_folder())).order_by(custom_ordering)
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if 'security_measure_name' in self.request.POST and SecurityMeasure.objects.filter(name=self.request.POST['security_measure_name'], id=self.request.session["last_created_measure"], folder=self.get_object().assessment.project.folder).exists():
            self.get_object().security_measures.add(SecurityMeasure.objects.get(name=self.request.POST['security_measure_name'], id=self.request.session["last_created_measure"], folder=self.get_object().assessment.project.folder))
        if 'security_measures_id' in self.request.POST:
            self.get_object().security_measures.clear()
            for security_measure_id in json.loads(self.request.POST['security_measures_id']):
                self.get_object().security_measures.add(SecurityMeasure.objects.get(id=security_measure_id, folder__in=(self.get_object().assessment.project.folder, Folder.get_root_folder())))
        return response

    def get_success_url(self) -> str:
        if self.request.GET.get('next') == "":
            return reverse_lazy("assessment-list")
        else:
            return self.request.GET.get('next')

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_requirementassessment"),
            folder=self.get_object().folder,
        )
    

class RequirementAssessmentUpdateViewModal(UserPassesTestMixin, UpdateView):
    model = RequirementAssessment
    template_name = 'core/requirementassessment_update_modal.html'
    context_object_name = 'requirementassessment'
    form_class = SecurityMeasureSelectForm

    def get_success_url(self) -> str:
        return reverse_lazy('requirementassessment-update', kwargs={'pk': self.kwargs['pk']})

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_requirementassessment"),
            folder=self.get_object().folder)


class RequirementAssessmentDeleteView(UserPassesTestMixin, DeleteView):
    model = RequirementAssessment
    template_name = "core/fallback_form.html"

    def get_success_url(self) -> str:
        return reverse_lazy("requirementassessment-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_requirementassessment"),
            folder=self.get_object().folder,
        )
class ProjectCreateView(UserPassesTestMixin, CreateView):
    model = Project
    template_name = "core/project_create.html"
    context_object_name = "project"
    form_class = ProjectForm

    def get_success_url(self) -> str:
        return reverse_lazy("project-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_project"),
            folder=Folder.objects.get(id=self.request.POST["folder"]),
        )


class ProjectCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = Project
    context_object_name = "project"
    form_class = ProjectForm

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_project"),
            folder=Folder.objects.get(id=self.request.POST["folder"]),
        )


class ProjectUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Project
    template_name = "core/project_update.html"
    context_object_name = "project"
    form_class = ProjectForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"project-list": _("Projects")}
        context['assessments'] = Assessment.objects.filter(project=self.object)
        context["assessment_create_form"] = AssessmentCreateForm(
            initial={"project": self.object.id}
        )
        return context

    def get_success_url(self) -> str:
        if self.request.POST.get("next", "/") == "":
            return reverse_lazy("project-list")
        else:
            return self.request.POST.get("next", "/")

    def form_valid(self, form):
        folder = form.cleaned_data["folder"]
        if not RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_project"),
            folder=folder,
        ):
            raise PermissionDenied()
        return super().form_valid(form)

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_project"),
            folder=self.get_object().folder,
        )


class ProjectDeleteView(UserPassesTestMixin, DeleteView):
    model = Project
    success_url = reverse_lazy("project-list")
    template_name = "snippets/project_delete_modal.html"

    def get_success_url(self) -> str:
        return reverse_lazy("project-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_project"),
            folder=self.get_object().folder,
        )


class FolderListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = "core/project_domain_list.html"
    context_object_name = "domains"

    ordering = "created_at"
    paginate_by = PAGINATE_BY
    model = Folder

    def get_queryset(self):
        folders_list = RoleAssignment.get_accessible_folders(
            Folder.get_root_folder(),
            self.request.user,
            Folder.ContentType.DOMAIN,
            codename="view_folder",
        )
        qs = self.model.objects.filter(id__in=folders_list).order_by(self.ordering)
        filtered_list = ProjectsDomainFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ProjectsDomainFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        context["projects_domain_create_form"] = FolderUpdateForm
        context["add_folder"] = RoleAssignment.has_permission(
            self.request.user, "add_folder"
        )
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Folder
        )
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class FolderCreateView(UserPassesTestMixin, CreateView):
    model = Folder
    template_name = "core/pd_update.html"
    context_object_name = "domain"
    form_class = FolderUpdateForm

    def get_success_url(self) -> str:
        return reverse_lazy("folder-list")

    def test_func(self):
        # TODO: Change this when we allow picking a folder for role assignments
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_folder"),
            folder=Folder.get_root_folder(),
        )


class FolderCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = Folder
    context_object_name = "domain"
    form_class = FolderUpdateForm

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        self.object = form.save()
        folder = self.object
        auditors = UserGroup.objects.create(
            name=UserGroupCodename.AUDITOR, folder=folder, builtin=True
        )
        analysts = UserGroup.objects.create(
            name=UserGroupCodename.ANALYST, folder=folder, builtin=True
        )
        managers = UserGroup.objects.create(
            name=UserGroupCodename.DOMAIN_MANAGER, folder=folder, builtin=True
        )
        ra1 = RoleAssignment.objects.create(
            user_group=auditors,
            role=Role.objects.get(name=RoleCodename.AUDITOR),
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        ra1.perimeter_folders.add(folder)
        ra3 = RoleAssignment.objects.create(
            user_group=analysts,
            role=Role.objects.get(name=RoleCodename.ANALYST),
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        ra3.perimeter_folders.add(folder)
        ra4 = RoleAssignment.objects.create(
            user_group=managers,
            role=Role.objects.get(name=RoleCodename.DOMAIN_MANAGER),
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        ra4.perimeter_folders.add(folder)
        messages.info(
            self.request,
            _(
                "User groups {} - Auditors, {} - Analysts and {} - Domain Managers were created"
            ).format(folder.name, folder.name, folder.name, folder.name),
        )
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return self.request.POST.get("next", reverse_lazy("folder-list"))

    def test_func(self):
        # TODO: Change this when we allow picking a folder for role assignments
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_folder"),
            folder=Folder.get_root_folder(),
        )


class FolderUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Folder
    template_name = "core/pd_update.html"
    context_object_name = "domain"
    form_class = FolderUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["projects"] = Project.objects.filter(folder=self.get_object())
        context["crumbs"] = {"folder-list": _("Projects domains")}
        context["project_create_form"] = ProjectFormInherited(
            initial={"folder": get_object_or_404(Folder, id=self.kwargs["pk"])}
        )
        return context

    def get_success_url(self) -> str:
        return self.request.POST.get("next", "/")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_folder"),
            folder=self.get_object(),
        )


class FolderDeleteView(UserPassesTestMixin, DeleteView):
    model = Folder
    success_url = reverse_lazy("folder-list")
    template_name = "snippets/projects_domain_delete_modal.html"

    def get_success_url(self) -> str:
        return reverse_lazy("folder-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_folder"),
            folder=self.get_object(),
        )


class ComposerListView(ListView):
    
    def get(self, request, *args, **kwargs):
        v = request.GET.get('project')
        if v:
            request_list = request.GET.getlist('project')[0]
            data = [item for item in request_list.split(',')]
            # debug print(f"got {len(data)} analysis in {data}")
            context = {
                "context": compile_project_for_composer(self.request.user, data),
                "view_user": RoleAssignment.has_permission(request.user, "view_user"), # NOTE: Need to factorize with BaseContextMixin
                "change_usergroup": RoleAssignment.is_access_allowed(user=self.request.user, perm=Permission.objects.get(codename="change_usergroup"), folder=Folder.get_root_folder()),
            }
            return render(request, 'core/composer.html', context)
        else:
            (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), self.request.user, Project)
            context = {'context': Project.objects.filter(
                id__in=object_ids_view)}
            return render(request, 'core/project_select.html', context)


class ReviewView(BaseContextMixin, ListView):
    template_name = "core/review.html"
    context_object_name = "context"
    model = Assessment
    ordering = "id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, self.model
        )
        return Assessment.objects.filter(id__in=object_ids_view)


class SecurityMeasureListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = "core/mtg_list.html"
    context_object_name = "measures"

    ordering = "-created_at"
    paginate_by = PAGINATE_BY
    model = SecurityMeasure

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = SecurityMeasureFilter(
            self.request.GET, queryset=queryset, request=self.request
        )
        context["filter"] = filter
        context["measure_create_form"] = SecurityMeasureCreateForm()
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, SecurityMeasure
        )
        context["add_securitymeasure"] = RoleAssignment.has_permission(
            self.request.user, "add_securitymeasure"
        )
        return context

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, SecurityMeasure
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = SecurityMeasureFilter(
            self.request.GET, request=self.request, queryset=qs
        )
        return filtered_list.qs

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class SecurityMeasureCreateViewModal(CreateViewModal, UserPassesTestMixin):
    permission_required = "core.add_securitymeasure"
    model = SecurityMeasure
    context_object_name = "measure"
    form_class = SecurityMeasureCreateForm

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        self.object = form.save()
        security_measure = self.object
        # save id of created measure in the session context
        # this can be used in the requirement_assessment update form for additional security
        self.request.session["last_created_measure"]=str(security_measure.id)
        return super().form_valid(form)

    def form_invalid(self, form):
        if is_ajax(request=self.request):
            errors = form.errors.as_json()
            return JsonResponse({"success": False, "errors": errors})
        return super().form_invalid(form)

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_securitymeasure"),
            folder=Folder.objects.get(id=self.request.POST["folder"]),
        )


class SecurityMeasureUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = SecurityMeasure
    template_name = "core/mtg_update.html"
    context_object_name = "security_measure"
    form_class = SecurityMeasureUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"securitymeasure-list": _("Security measures")}
        return context

    def get_success_url(self) -> str:
        if self.request.POST.get("next", "/") == "":
            return reverse_lazy("securitymeasure-list")
        else:
            return self.request.POST.get("next", "/")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_securitymeasure"),
            folder=self.get_object().folder,
        )


class SecurityMeasureDeleteView(UserPassesTestMixin, DeleteView):
    model = SecurityMeasure
    success_url = reverse_lazy("securitymeasure-list")
    template_name = "snippets/measure_delete_modal.html"

    def get_success_url(self) -> str:
        return reverse_lazy("securitymeasure-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_securitymeasure"),
            folder=self.get_object().folder,
        )


class SecurityFunctionListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = "core/security_function_list.html"
    context_object_name = "functions"

    ordering = "-created_at"
    paginate_by = PAGINATE_BY
    model = SecurityFunction

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, SecurityFunction
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = SecurityFunctionFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = SecurityFunctionFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        context["security_function_create_form"] = SecurityFunctionCreateForm
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, SecurityFunction
        )
        context["add_securityfunction"] = RoleAssignment.has_permission(
            self.request.user, "add_securityfunction"
        )
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class SecurityFunctionCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = SecurityFunction
    context_object_name = "function"
    form_class = SecurityFunctionCreateForm

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_securityfunction"),
            folder=Folder.get_root_folder(),
        )


class SecurityFunctionUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = SecurityFunction
    template_name = "core/security_function_update.html"
    context_object_name = "function"
    form_class = SecurityFunctionUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"securityfunction-list": _("Security functions")}
        return context

    def get_success_url(self) -> str:
        if self.request.POST.get("next", "/") == "":
            return reverse_lazy("securityfunction-list")
        else:
            return self.request.POST.get("next", "/")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_securityfunction"),
            folder=self.get_object().folder,
        )


class SecurityFunctionDeleteView(UserPassesTestMixin, DeleteView):
    model = SecurityFunction
    success_url = reverse_lazy("securityfunction-list")
    template_name = "snippets/security_function_delete_modal.html"

    def get_success_url(self) -> str:
        return reverse_lazy("securityfunction-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_securityfunction"),
            folder=self.get_object().folder,
        )


class ThreatListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = "core/threat_list.html"
    context_object_name = "threats"

    ordering = "-created_at"
    paginate_by = PAGINATE_BY
    model = Threat

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Threat
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = ThreatFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = ThreatFilter(self.request.GET, request=self.request, queryset=queryset)
        context["filter"] = filter
        context["threat_create_form"] = ThreatCreateForm
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Threat
        )
        context["add_threat"] = RoleAssignment.has_permission(
            self.request.user, "add_threat"
        )
        return context

    def test_func(self):
        """
        The view is always accessible, only its content is filtered by the queryset
        """
        return True


class ThreatCreateViewModal(UserPassesTestMixin, CreateViewModal):
    model = Threat
    context_object_name = "threat"
    form_class = ThreatCreateForm

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_threat"),
            folder=Folder.get_root_folder(),
        )


class ThreatUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    model = Threat
    template_name = "core/threat_update.html"
    context_object_name = "threat"
    form_class = ThreatUpdateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"threat-list": _("Threats")}
        return context

    def get_success_url(self) -> str:
        if self.request.POST.get("next", "/") == "":
            return reverse_lazy("threat-list")
        else:
            return self.request.POST.get("next", "/")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_threat"),
            folder=self.get_object().folder,
        )


class ThreatDeleteView(UserPassesTestMixin, DeleteView):
    model = Threat
    success_url = reverse_lazy("threat-list")
    template_name = "snippets/threat_delete_modal.html"

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_threat"),
            folder=self.get_object().folder,
        )


class MyProfileDetailView(BaseContextMixin, UserPassesTestMixin, DetailView):
    template_name = "core/my_profile_detailed.html"
    context_object_name = "user"

    model = User

    def get_object(
        self, queryset: Optional[models.query.QuerySet[Any]] = ...
    ) -> models.Model:
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not UserGroup.get_user_groups(self.request.user):
            messages.warning(
                self.request,
                _(
                    "Warning! You are not assigned to any group. Without a group you will not have access to any functionality. Please contact you administrator."
                ),
            )
        context["user_groups"] = self.object.user_groups.all()
        keys = [
            _("Last name"),
            _("First name"),
            _("Email"),
            _("Entry date"),
            _("Superuser"),
        ]
        values = []
        for key, value in model_to_dict(
            self.object, fields=["last_name", "first_name", "email", "date_joined"]
        ).items():
            values.append(value)
        context["user_fields"] = dict(zip(keys, values))
        roles = []
        for user_group in self.object.user_groups.all():
            for role_assignment in user_group.roleassignment_set.all():
                roles.append(role_assignment.role.name)
        context["roles"] = roles
        return context

    def test_func(self):
        return self.request.user.is_authenticated


class MyProfileUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    template_name = "core/user_update.html"
    context_object_name = "user"
    form_class = MyProfileUpdateForm

    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = get_object_or_404(User, pk=self.kwargs["pk"])
        print("DEBUG: User =", get_object_or_404(User, pk=self.kwargs["pk"]))
        return kwargs

    def get_success_url(self) -> str:
        if self.request.POST.get("next", "/") == "":
            return reverse_lazy("index")
        else:
            return self.request.POST.get("next", "/")

    def test_func(self):
        return self.request.user == get_object_or_404(User, pk=self.kwargs["pk"])


class UserListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = "core/user_list.html"
    context_object_name = "users"

    ordering = "created_at"
    paginate_by = PAGINATE_BY
    model = User

    def get_queryset(self):
        qs = self.model.objects.all().order_by(
            "-is_active", "-is_superuser", "email", "id"
        )
        filtered_list = UserFilter(self.request.GET, queryset=qs, request=self.request)
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserFilter(self.request.GET, request=self.request, queryset=queryset)
        context["filter"] = filter
        context["users_number"] = User.objects.all().count()
        context["users_number_limit"] = MAX_USERS

        return context

    def test_func(self):
        return RoleAssignment.has_permission(
            user=self.request.user, codename="view_user"
        )


class UserCreateView(BaseContextMixin, UserPassesTestMixin, CreateView):
    template_name = "core/user_create.html"
    context_object_name = "user"
    form_class = UserCreateForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"user-list": _("Users")}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy("user-list")

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            data = form.cleaned_data["email"]
            try:
                User.objects.create_user(email=data)
                messages.success(
                    request, _("User created and email send successfully.")
                )
                return redirect("user-list")
            except Exception as e:
                messages.error(
                    request,
                    "An error has occured during user creation. If he has not received the mail, please use the forgot link on login page.",
                )
                print("Exception:", e)
                return redirect("user-list")
        return render(request, self.template_name, {"form": form})

    def test_func(self):
        return RoleAssignment.has_permission(
            user=self.request.user, codename="add_user"
        )


class UserUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    template_name = "core/user_update.html"
    context_object_name = "user"
    form_class = UserUpdateForm

    model = User

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"user-list": _("Users")}
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = get_object_or_404(User, pk=self.kwargs["pk"])
        print("DEBUG: User =", get_object_or_404(User, pk=self.kwargs["pk"]))
        return kwargs

    def get_success_url(self) -> str:
        if self.request.POST.get("next", "/") == "":
            return reverse_lazy("user-list")
        else:
            return self.request.POST.get("next", "/")

    def test_func(self):
        return RoleAssignment.has_permission(
            user=self.request.user, codename="change_user"
        )


class UserDeleteView(UserPassesTestMixin, DeleteView):
    model = User
    success_url = reverse_lazy("user-list")
    template_name = "snippets/user_delete_modal.html"

    def get_success_url(self) -> str:
        return reverse_lazy("user-list")

    def test_func(self):
        return RoleAssignment.has_permission(
            user=self.request.user, codename="delete_user"
        )


class UserGroupListView(BaseContextMixin, UserPassesTestMixin, ListView):
    template_name = "core/group_list.html"
    context_object_name = "user_groups"

    ordering = "folder"
    paginate_by = PAGINATE_BY
    model = UserGroup

    def get_queryset(self):
        (
            object_ids_view,
            object_ids_change,
            object_ids_delete,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.objects.get(content_type=Folder.ContentType.ROOT),
            self.request.user,
            UserGroup,
        )
        qs = self.model.objects.filter(id__in=object_ids_view).order_by(self.ordering)
        filtered_list = UserGroupFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserGroupFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        (
            context["object_ids_view"],
            context["object_ids_change"],
            context["object_ids_delete"],
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, UserGroup
        )
        context["add_usergroup"] = RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_usergroup"),
            folder=Folder.get_root_folder(),
        )
        return context

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="view_usergroup"),
            folder=Folder.get_root_folder(),
        )


class UserGroupCreateView(UserPassesTestMixin, CreateView):
    template_name = "core/group_create.html"
    context_object_name = "user_group"
    form_class = UserGroupCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy("usergroup-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_usergroup"),
            folder=Folder.objects.get(id=self.request.POST["folder"]),
        )


class UserGroupUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    template_name = "core/group_update.html"
    context_object_name = "user_group"
    form_class = UserGroupUpdateForm

    model = UserGroup

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["users"] = User.objects.exclude(user_groups=self.get_object())
        context["associated_users"] = User.objects.filter(user_groups=self.get_object())
        context["crumbs"] = {"usergroup-list": _("User groups")}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy("usergroup-list")

    def test_func(self):
        user_group = self.get_object()
        return not (user_group.builtin) and RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_usergroup"),
            folder=Folder.get_folder(user_group),
        )


class UserGroupDeleteView(UserPassesTestMixin, DeleteView):
    model = UserGroup
    success_url = reverse_lazy("usergroup-list")
    template_name = "snippets/group_delete_modal.html"

    def get_success_url(self) -> str:
        return reverse_lazy("usergroup-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_usergroup"),
            folder=self.get_object().folder,
        )


class RoleAssignmentListView(BaseContextMixin, UserPassesTestMixin, ListView):
    permission_required = "core.view_roleassignment"
    template_name = "core/role_list.html"
    context_object_name = "assignments"

    ordering = "created_at"
    paginate_by = PAGINATE_BY
    model = RoleAssignment

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        messages.info(
            self.request,
            _(
                "Role assignment editing will be available in a future release. Currently you have to attach users to groups to assign roles."
            ),
        )

    def get_queryset(self):
        qs = self.model.objects.all().order_by("id")
        filtered_list = UserGroupFilter(
            self.request.GET, queryset=qs, request=self.request
        )
        return filtered_list.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        filter = UserGroupFilter(
            self.request.GET, request=self.request, queryset=queryset
        )
        context["filter"] = filter
        context["roles"] = Role.objects.all().order_by("id")
        return context

    def test_func(self):
        return True


class RoleAssignmentCreateView(BaseContextMixin, UserPassesTestMixin, CreateView):
    permission_required = "core.add_roleassignment"
    template_name = "core/role_assignment_create.html"
    context_object_name = "assignment"
    form_class = RoleAssignmentCreateForm

    def get_success_url(self) -> str:
        return reverse_lazy("role-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"role-list": _("Role assignment")}
        return context

    def test_func(self):
        # TODO: Change this when we allow picking a folder for role assignments
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="add_roleassignment"),
            folder=Folder.get_root_folder(),
        )


class RoleAssignmentDeleteView(UserPassesTestMixin, DeleteView):
    permission_required = "core.delete_roleassignment"
    model = RoleAssignment
    success_url = reverse_lazy("role-list")
    template_name = "snippets/role_assignment_delete_modal.html"

    def get_success_url(self) -> str:
        return reverse_lazy("role-list")

    def test_func(self):
        return RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="delete_roleassignment"),
            folder=Folder.get_folder(self.get_object()),
        )


class RoleAssignmentUpdateView(BaseContextMixin, UserPassesTestMixin, UpdateView):
    permission_required = "auth.change_role"
    template_name = "core/role_update.html"
    context_object_name = "role"
    form_class = RoleAssignmentUpdateForm

    model = Role

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"usergroup-list": _("User groups")}
        return context

    def get_success_url(self) -> str:
        return reverse_lazy("role-list")

    def test_func(self):
        ra = get_object_or_404(RoleAssignment, pk=self.kwargs["pk"])
        return not (ra.builtin) and RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="change_roleassignment"),
            folder=Folder.get_folder(ra),
        )


class UserPasswordChangeView(BaseContextMixin, UserPassesTestMixin, PasswordChangeView):
    """view to change user password"""

    template_name = "core/password_change.html"
    form_class = UserPasswordChangeForm
    model = User

    def get_success_url(self) -> str:
        self.object = get_object_or_404(User, pk=self.kwargs["pk"])
        if self.object == self.request.user:
            return reverse_lazy("me-update", kwargs={"pk": self.request.user.id})
        return reverse_lazy("user-update", kwargs={"pk": self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["this_user"] = get_object_or_404(User, pk=self.kwargs["pk"])
        context["crumbs"] = {"user-list": _("Users")}
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = get_object_or_404(User, pk=self.kwargs["pk"])
        # print('DEBUG: User =', get_object_or_404(User, pk=self.kwargs['pk']))
        return kwargs

    def test_func(self):
        return RoleAssignment.has_permission(
            user=self.request.user, codename="change_user"
        ) or self.request.user == get_object_or_404(User, pk=self.kwargs["pk"])


def license_overview(request):
    template = "license/overview.html"
    context = {}

    context["change_usergroup"] = RoleAssignment.is_access_allowed(
        user=request.user,
        perm=Permission.objects.get(codename="change_usergroup"),
        folder=Folder.get_root_folder(),
    )
    context["view_user"] = RoleAssignment.has_permission(request.user, "view_user")
    context["exceeded_users"] = (MAX_USERS - User.objects.all().count()) < 0

    context["users_number"] = User.objects.all().count()
    context["users_number_limit"] = MAX_USERS
    context["licence_deployment"] = LICENCE_DEPLOYMENT
    context["licence_expiration"] = LICENCE_EXPIRATION
    context["licence_support"] = LICENCE_SUPPORT
    context["licence_type"] = LICENCE_TYPE

    return render(request, template, context)


class AssessmentDetailView(GenericDetailView):
    model = Assessment
    template_name = "core/detail/assessment_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"assessment-list": _("Assessments")}
        context["tree"] = get_sorted_requirements_and_groups(
            Requirement.objects.filter(framework=self.object.framework),
            RequirementGroup.objects.filter(framework=self.object.framework),
            RequirementAssessment.objects.filter(assessment=self.object))
        context["assessments_status"] = self.get_object().donut_render()
        context["requirement_group_stats"] = get_assessment_stats(self.get_object())
        return context


def generate_html(assessment: Assessment) -> str:
    assessments_status = []
    requirement_groups = RequirementGroup.objects.filter(framework=assessment.framework)
    for st in RequirementAssessment.Status:
        count = RequirementAssessment.objects.filter(status=st).filter(
            assessment=assessment).count()
        total = RequirementAssessment.objects.filter(assessment=assessment).count()
        assessments_status.append((st, round(count*100/total)))
    content = '''
    <html lang="en">
    <head>
    <link rel="stylesheet" href="https://unpkg.com/dezui@latest">
    <script src="https://cdn.tailwindcss.com"></script>
    <title>CSF report</title>
    </head>
    <body class="container container-tablet">
    '''
    content += '<hr class="dotted">'
    content += '<div class="flex flex-row space-x-4 flex justify-center items-center mb-4">'
    content += f"<h1 class='text-3xl'>{assessment.name}: {assessment.framework}</h1>"
    content += '<div class="flex bg-gray-300 rounded-full overflow-hidden h-4 w-2/3">'
    for stat in reversed(assessments_status):
        if stat[1] > 0:
            content += '<div class="flex flex-col justify-center overflow-hidden text-xs font-semibold text-center '
            if stat[0] == 'in_progress':
                content += 'bg-blue-500'
            elif stat[0] == 'non_compliant':
                content += 'bg-red-500'
            elif stat[0] == 'partially_compliant':
                content += 'bg-yellow-400'
            elif stat[0] == 'compliant':
                content += 'bg-green-500'
            elif stat[0] == 'not_applicable':
                content += 'bg-black text-white dark:bg-white dark:text-black'
            content += '" style="width:' + str(stat[1]) + '%"> ' + str(stat[1]) + '%</div>'
    content += '</div></div>'
    table = '''
    <thead>
    </thead>
    <tbody>
    '''
    for requirement_group in requirement_groups:
        table += f'<p class="font-semibold">{requirement_group} {requirement_group.description}</p>'
        for subcategory in RequirementAssessment.objects.filter(requirement__parent_urn=requirement_group.urn).order_by('created_at'):
            table += '<div>'
            table += "<div class='flex flex-col shadow-md border rounded-lg px-4 py-2 m-2 ml-0 items-center "
            match subcategory.status:
                case 'compliant':
                    table += "border-t-2 border-t-green-500 border-green-500'>"
                case 'to_do':
                    table += "border-t-2 border-t-gray-300 border-gray-300'>"
                case 'in_progress':
                    table += "border-t-2 border-t-blue-500 border-blue-500'>"
                case 'non_compliant':
                    table += "border-t-2 border-t-red-500 border-red-500'>"
                case 'partially_compliant':
                    table += "border-t-2 border-t-yellow-400 border-yellow-400'>"
                case 'not_applicable':
                    table += "border-t-2 border-t-black border-black'>"
            table += '<div class="flex flex-row justify-between w-full">'
            table += f"<p class='font-semibold'>{subcategory.requirement}</p>"
            table += "<p class='text-white text-center rounded-lg whitespace-nowrap px-2 py-1 "
            match subcategory.status:
                case 'compliant':
                    table += f"bg-green-500'>{subcategory.get_status_display()}</p>"
                case 'to_do':
                    table += f"bg-gray-300'>{subcategory.get_status_display()}</p>"
                case 'in_progress':
                    table += f"bg-blue-500'>{subcategory.get_status_display()}</p>"
                case 'non_compliant':
                    table += f"bg-red-500'>{subcategory.get_status_display()}</p>"
                case 'partially_compliant':
                    table += f"bg-yellow-400'>{subcategory.get_status_display()}</p>"
                case 'not_applicable':
                    table += f"bg-black tewt-white'>{subcategory.get_status_display()}</p>"
            table += "</div>"
            table += f"<p class='text-left w-full'>{subcategory.requirement.description}</p>"
            table += "</div>"
            if subcategory.security_measures.all():
                table += '<div class="flex flex-col px-4 py-2 m-2 ml-0 rounded-lg bg-indigo-200">'
                evidences = ''
                table += '<div class="grid grid-cols-2 justify-items-center font-semibold">'
                table += f'<p>{_("Applied security measures")}:</p>'
                table += f'<p>{_("Associated evidence")}:</p>'
                table += '</div>'
                table += '<div class="flex flex-row">'
                table += '<div class="flex flex-col items-center w-1/2">'
                for measure in subcategory.security_measures.all():
                    
                    table += f"<li> {measure.name}: {measure.get_status_display()}</li>"

                    
                    for evidence in measure.evidence_set.all():
                        if evidence.attachment:
                            evidences += f'<li> <a class="text-indigo-700 hover:text-indigo-500" target="_blank" href="evidences/{evidence.attachment}">{measure.name}/{evidence.name}</a></li>'
                        else:
                            evidences += f'<li> {evidence.name}</li>'
                table += "</div>"
                table += f'<div class="flex flex-col items-center w-1/2">{evidences}</div>'
                table += '</div></div>'
            table += '</div>'
    table += "</tbody><br/>"
    content += table
    content += '''
    </body>
    </html>
    '''

    return content 

def export(request, assessment: Assessment):
    # this will export a zip file with all the evidences and a html file with the report
    assessment = Assessment.objects.get(id=assessment)
    index_content = generate_html(assessment)
    zip_name = f"{assessment.name}-{assessment.framework.name.replace('/', '-')}-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.zip"
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for evidence in Evidence.objects.all():
            if evidence.attachment:
                with tempfile.NamedTemporaryFile(delete=True) as tmp:
                    # Download the attachment to the temporary file
                    if default_storage.exists(evidence.attachment.name):
                        file = default_storage.open(evidence.attachment.name)
                        tmp.write(file.read())
                        tmp.flush()
                        zipf.write(tmp.name, os.path.join('evidences', os.path.basename(evidence.attachment.name)))
        zipf.writestr("index.html", index_content)

    response = FileResponse(open(zip_name, 'rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{zip_name}"'
    os.remove(zip_name)
    return response


class FrameworkDetailView(GenericDetailView):
    model = Framework

    template_name = "core/detail/framework_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["crumbs"] = {"framework-list": _("Frameworks")}
        context["tree"] = get_sorted_requirements_and_groups(
            Requirement.objects.filter(framework=self.object), 
            RequirementGroup.objects.filter(framework=self.object))
        return context


class RequirementDetailView(GenericDetailView):
    model = Requirement


class RequirementAssessmentDetailView(GenericDetailView):
    model = RequirementAssessment


class EvidenceDetailView(GenericDetailView):
    model = Evidence

    template_name = "core/detail/evidence_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['evidence'] = self.object
        return context


def evidence_attachment_download(request, evidence_id):
    evidence = Evidence.objects.get(id=evidence_id)
    content_type = mimetypes.guess_type(evidence.filename())[0]
    response = HttpResponse(evidence.attachment, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{evidence.filename()}"'
    return response

def evidence_attachment_preview(request, evidence_id):
    evidence = Evidence.objects.get(id=evidence_id)
    content_type = mimetypes.guess_type(evidence.filename())[0]
    response = HttpResponse(evidence.attachment, content_type=content_type)
    return response


class HomeView(AssessmentListView):
    template_name = "core/index.html"