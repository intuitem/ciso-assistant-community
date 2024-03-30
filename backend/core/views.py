import csv
from datetime import datetime
import mimetypes
import tempfile
from uuid import UUID
import zipfile
from django.core.files.storage import default_storage

from django.http import FileResponse, HttpResponse
from rest_framework.parsers import FileUploadParser
from rest_framework.request import Request
from rest_framework.views import APIView
from core.forms import FirstConnexionConfirmForm, ResetConfirmForm
from core.models import AppliedControl

from core.helpers import *
from rest_framework.response import Response

from .models import *
from .serializers import *
from .permissions import IsAdministrator

from ciso_assistant.settings import (
    BUILD,
    VERSION,
)

from django.middleware import csrf
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets, filters
from rest_framework.decorators import (
    api_view,
    permission_classes,
    action,
)

import csv
import importlib
import re
import uuid
from typing import Any
from uuid import UUID

import django_filters as df
from core.models import ComplianceAssessment
from core.serializers import ComplianceAssessmentReadSerializer
from django.contrib.auth.models import Permission
from django.contrib.auth.views import PasswordResetConfirmView
from django.forms import ValidationError
from django.template.loader import render_to_string
from django.utils.functional import Promise
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from rest_framework.utils.serializer_helpers import ReturnDict
from weasyprint import HTML

from core.utils import RoleCodename, UserGroupCodename

from django.db import models

from iam.models import User, RoleAssignment, Folder

User = get_user_model()


class BaseModelViewSet(viewsets.ModelViewSet):
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering = ["created_at"]
    ordering_fields = ordering
    search_fields = ["name", "description"]
    model: models.Model

    def get_queryset(self):
        if not self.model:
            return None
        object_ids_view = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, self.model
        )[0]
        queryset = self.model.objects.filter(id__in=object_ids_view)
        return queryset

    def get_serializer_class(self):
        base_name = self.model.__name__

        if self.action in ["list", "retrieve"]:
            serializer_name = f"{base_name}ReadSerializer"
        elif self.action in ["create", "update", "partial_update"]:
            serializer_name = f"{base_name}WriteSerializer"
        else:
            # Default to the parent class's implementation if action doesn't match
            return super().get_serializer_class()

        # Dynamically import the serializer module and get the serializer class
        serializer_module = importlib.import_module("core.serializers")
        serializer_class = getattr(serializer_module, serializer_name)

        return serializer_class

    COMMA_SEPARATED_UUIDS_REGEX = r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}(,[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})*$"

    def _process_request_data(self, request: Request) -> None:
        """
        Process the request data to split comma-separated UUIDs into a list
        and handle empty list scenarios.
        """
        for field in request.data:
            # NOTE: This is due to sveltekit-superforms not coercing the value into a list when
            # the form's dataType is "form", rather than "json".
            # Typically, dataType is "form" when the form contains a file input (e.g. for evidence attachments).
            # I am not ruling out the possibility that I am doing something wrong in the frontend. (Nassim)
            # TODO: Come back to this once superForms v2 is out of alpha. https://github.com/ciscoheat/sveltekit-superforms/releases
            if isinstance(request.data[field], list) and len(request.data[field]) == 1:
                if isinstance(request.data[field][0], str) and re.match(
                    self.COMMA_SEPARATED_UUIDS_REGEX, request.data[field][0]
                ):
                    request.data[field] = request.data[field][0].split(",")
                elif not request.data[field][0]:
                    request.data[field] = []

    def create(self, request: Request, *args, **kwargs) -> Response:
        self._process_request_data(request)
        return super().create(request, *args, **kwargs)

    def update(self, request: Request, *args, **kwargs) -> Response:
        self._process_request_data(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        self._process_request_data(request)
        return super().partial_update(request, *args, **kwargs)

    class Meta:
        abstract = True

    @action(detail=True, name="Get write data")
    def object(self, request, pk):
        serializer_name = f"{self.model.__name__}WriteSerializer"
        serializer_module = importlib.import_module("core.serializers")
        serializer_class = getattr(serializer_module, serializer_name)

        return Response(serializer_class(super().get_object()).data)


# Risk Assessment


class ProjectViewSet(BaseModelViewSet):
    """
    API endpoint that allows projects to be viewed or edited.
    """

    model = Project
    filterset_fields = ["folder", "lc_status"]
    search_fields = ["name", "internal_reference", "description"]

    @action(detail=False, name="Get status choices")
    def lc_status(self, request):
        return Response(dict(Project.PRJ_LC_STATUS))

    @action(detail=False, methods=["get"])
    def names(self, request):
        uuid_list = request.query_params.getlist("id[]", [])
        queryset = Project.objects.filter(id__in=uuid_list)

        return Response({str(project.id): project.name for project in queryset})

    @action(detail=False, methods=["get"])
    def quality_check(self, request):
        """
        Returns the quality check of the projects
        """
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(), user=request.user, object_type=Project
        )
        projects = Project.objects.filter(id__in=viewable_objects)
        res = {
            str(p.id): {
                "project": ProjectReadSerializer(p).data,
                "compliance_assessments": {"objects": {}},
                "risk_assessments": {"objects": {}},
            }
            for p in projects
        }
        for compliance_assessment in ComplianceAssessment.objects.filter(
            project__in=projects
        ):
            res[str(compliance_assessment.project.id)]["compliance_assessments"][
                "objects"
            ][str(compliance_assessment.id)] = {
                "object": ComplianceAssessmentReadSerializer(
                    compliance_assessment
                ).data,
                "quality_check": compliance_assessment.quality_check(),
            }
        for risk_assessment in RiskAssessment.objects.filter(project__in=projects):
            res[str(risk_assessment.project.id)]["risk_assessments"]["objects"][
                str(risk_assessment.id)
            ] = {
                "object": RiskAssessmentReadSerializer(risk_assessment).data,
                "quality_check": risk_assessment.quality_check(),
            }
        return Response({"results": res})

    @action(detail=True, methods=["get"], url_path="quality_check")
    def quality_check_detail(self, request, pk):
        """
        Returns the quality check of the project
        """
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(), user=request.user, object_type=Project
        )
        if UUID(pk) in viewable_objects:
            project = self.get_object()
            res = {
                "project": ProjectReadSerializer(project).data,
                "compliance_assessments": {"objects": {}},
                "risk_assessments": {"objects": {}},
            }
            for compliance_assessment in ComplianceAssessment.objects.filter(
                project=project
            ):
                res["compliance_assessments"]["objects"][
                    str(compliance_assessment.id)
                ] = {
                    "object": ComplianceAssessmentReadSerializer(
                        compliance_assessment
                    ).data,
                    "quality_check": compliance_assessment.quality_check(),
                }
            for risk_assessment in RiskAssessment.objects.filter(project=project):
                res["risk_assessments"]["objects"][str(risk_assessment.id)] = {
                    "object": RiskAssessmentReadSerializer(risk_assessment).data,
                    "quality_check": risk_assessment.quality_check(),
                }
            return Response(res)
        else:
            return Response(status=HTTP_403_FORBIDDEN)


class ThreatViewSet(BaseModelViewSet):
    """
    API endpoint that allows threats to be viewed or edited.
    """

    model = Threat
    filterset_fields = ["folder", "risk_scenarios"]
    search_fields = ["name", "provider", "description"]


class AssetViewSet(BaseModelViewSet):
    """
    API endpoint that allows assets to be viewed or edited.
    """

    model = Asset
    filterset_fields = ["folder", "parent_assets", "type", "risk_scenarios"]
    search_fields = ["name", "description", "business_value"]

    @action(detail=False, name="Get type choices")
    def type(self, request):
        return Response(dict(Asset.Type.choices))


class ReferenceControlViewSet(BaseModelViewSet):
    """
    API endpoint that allows reference controls to be viewed or edited.
    """

    model = ReferenceControl
    filterset_fields = ["folder", "category"]
    search_fields = ["name", "description", "provider"]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(ReferenceControl.CATEGORY))


class RiskMatrixViewSet(BaseModelViewSet):
    """
    API endpoint that allows risk matrices to be viewed or edited.
    """

    model = RiskMatrix
    filterset_fields = ["folder", "is_enabled"]

    @action(detail=False)  # Set a name there
    def colors(self, request):
        return Response({"results": get_risk_color_ordered_list(request.user)})

    @action(detail=False, name="Get used risk matrices")
    def used(self, request):
        _used_matrices = RiskMatrix.objects.filter(
            riskassessment__isnull=False
        ).distinct()
        used_matrices = _used_matrices.values("id", "name")
        for i in range(len(used_matrices)):
            used_matrices[i]["risk_assessments_count"] = _used_matrices.get(
                id=used_matrices[i]["id"]
            ).riskassessment_set.count()
        return Response({"results": used_matrices})


class RiskAssessmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows risk assessments to be viewed or edited.
    """

    model = RiskAssessment
    filterset_fields = [
        "project",
        "project__folder",
        "authors",
        "risk_matrix",
        "status",
    ]

    @action(detail=False, name="Risk assessments per status")
    def per_status(self, request):
        data = assessment_per_status(request.user, RiskAssessment)
        return Response({"results": data})

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(RiskAssessment.Status.choices))

    @action(detail=False, name="Get quality check")
    def quality_check(self, request):
        """
        Returns the quality check of the risk assessments
        """
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=RiskAssessment,
        )
        risk_assessments = RiskAssessment.objects.filter(id__in=viewable_objects)
        res = [
            {"id": a.id, "name": a.name, "quality_check": a.quality_check()}
            for a in risk_assessments
        ]
        return Response({"results": res})

    @action(detail=True, methods=["get"], url_path="quality_check")
    def quality_check_detail(self, request, pk):
        """
        Returns the quality check of the risk_assessment
        """
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=RiskAssessment,
        )
        if UUID(pk) in viewable_objects:
            risk_assessment = self.get_object()
            return Response(risk_assessment.quality_check())
        else:
            return Response(status=HTTP_403_FORBIDDEN)

    @action(detail=True, methods=["get"], name="Get treatment plan data")
    def plan(self, request, pk):
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=RiskAssessment,
        )
        if UUID(pk) in viewable_objects:
            risk_assessment_object = self.get_object()
            risk_scenarios_objects = risk_assessment_object.risk_scenarios.all()
            risk_assessment = RiskAssessmentReadSerializer(risk_assessment_object).data
            risk_scenarios = RiskScenarioReadSerializer(
                risk_scenarios_objects, many=True
            ).data
            [
                risk_scenario.update(
                    {
                        "applied_controls": AppliedControlReadSerializer(
                            AppliedControl.objects.filter(
                                risk_scenarios__id=risk_scenario["id"]
                            ),
                            many=True,
                        ).data
                    }
                )
                for risk_scenario in risk_scenarios
            ]
            risk_assessment.update({"risk_scenarios": risk_scenarios})
            return Response(risk_assessment)

        else:
            return Response(status=HTTP_403_FORBIDDEN)

    @action(detail=True, name="Get treatment plan CSV")
    def treatment_plan_csv(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskAssessment
        )
        if UUID(pk) in object_ids_view:
            risk_assessment = self.get_object()

            response = HttpResponse(content_type="text/csv")

            writer = csv.writer(response, delimiter=";")
            columns = [
                "risk_scenarios",
                "measure_id",
                "measure_name",
                "measure_desc",
                "category",
                "reference_control",
                "eta",
                "effort",
                "link",
                "status",
            ]
            writer.writerow(columns)
            (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), request.user, AppliedControl
            )
            for mtg in AppliedControl.objects.filter(id__in=object_ids_view).filter(
                risk_scenarios__risk_assessment=risk_assessment
            ):
                risk_scenarios = ",".join(
                    [
                        f"{scenario.rid}: {scenario.name}"
                        for scenario in mtg.risk_scenarios.all()
                    ]
                )
                row = [
                    risk_scenarios,
                    mtg.id,
                    mtg.name,
                    mtg.description,
                    mtg.get_category_display(),
                    mtg.reference_control,
                    mtg.eta,
                    mtg.effort,
                    mtg.link,
                    mtg.status,
                ]
                writer.writerow(row)

            return response
        else:
            return Response({"error": "Permission denied"}, status=HTTP_403_FORBIDDEN)

    @action(detail=True, name="Get risk assessment CSV")
    def risk_assessment_csv(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskAssessment
        )
        if UUID(pk) in object_ids_view:
            risk_assessment = self.get_object()

            response = HttpResponse(content_type="text/csv")

            writer = csv.writer(response, delimiter=";")
            columns = [
                "rid",
                "threats",
                "name",
                "description",
                "existing_controls",
                "current_level",
                "applied_controls",
                "residual_level",
                "treatment",
            ]
            writer.writerow(columns)

            for scenario in risk_assessment.risk_scenarios.all().order_by("created_at"):
                applied_controls = ",".join(
                    [m.csv_value for m in scenario.applied_controls.all()]
                )
                threats = ",".join([t.name for t in scenario.threats.all()])
                row = [
                    scenario.rid,
                    threats,
                    scenario.name,
                    scenario.description,
                    scenario.existing_controls,
                    scenario.get_current_risk()["name"],
                    applied_controls,
                    scenario.get_residual_risk()["name"],
                    scenario.treatment,
                ]
                writer.writerow(row)

            return response
        else:
            return Response({"error": "Permission denied"}, status=HTTP_403_FORBIDDEN)

    @action(detail=True, name="Get risk assessment PDF")
    def risk_assessment_pdf(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskAssessment
        )
        if UUID(pk) in object_ids_view:
            risk_assessment = self.get_object()
            context = RiskScenario.objects.filter(
                risk_assessment=risk_assessment
            ).order_by("created_at")
            data = {
                "context": context,
                "risk_assessment": risk_assessment,
                "ri_clusters": build_scenario_clusters(risk_assessment),
                "risk_matrix": risk_assessment.risk_matrix,
            }
            html = render_to_string("core/ra_pdf.html", data)
            pdf_file = HTML(string=html).write_pdf()
            response = HttpResponse(pdf_file, content_type="application/pdf")
            return response
        else:
            return Response({"error": "Permission denied"})

    @action(detail=True, name="Get treatment plan PDF")
    def treatment_plan_pdf(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskAssessment
        )
        if UUID(pk) in object_ids_view:
            risk_assessment = self.get_object()
            context = RiskScenario.objects.filter(
                risk_assessment=risk_assessment
            ).order_by("created_at")
            data = {"context": context, "risk_assessment": risk_assessment}
            html = render_to_string("core/mp_pdf.html", data)
            pdf_file = HTML(string=html).write_pdf()
            response = HttpResponse(pdf_file, content_type="application/pdf")
            return response
        else:
            return Response({"error": "Permission denied"})


class AppliedControlViewSet(BaseModelViewSet):
    """
    API endpoint that allows applied controls to be viewed or edited.
    """

    model = AppliedControl
    filterset_fields = [
        "folder",
        "category",
        "status",
        "reference_control",
        "effort",
        "risk_scenarios",
        "requirement_assessments",
        "evidences",
    ]
    search_fields = ["name", "description", "risk_scenarios", "requirement_assessments"]

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(AppliedControl.Status.choices))

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(AppliedControl.CATEGORY))

    @action(detail=False, name="Get effort choices")
    def effort(self, request):
        return Response(dict(AppliedControl.EFFORT))

    @action(detail=False, name="Get updatable measures")
    def updatables(self, request):
        (_, object_ids_change, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, AppliedControl
        )

        return Response({"results": object_ids_change})

    @action(
        detail=False, name="Something"
    )  # Write a good name for the "name" keyword argument
    def per_status(self, request):
        data = applied_control_per_status(request.user)
        return Response({"results": data})

    @action(detail=False, name="Get the ordered todo applied controls")
    def todo(self, request):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, AppliedControl
        )

        measures = sorted(
            AppliedControl.objects.filter(id__in=object_ids_view)
            .exclude(status="done")
            .order_by("eta"),
            key=lambda mtg: mtg.get_ranking_score(),
            reverse=True,
        )

        """measures = [{
            key: getattr(mtg,key)
            for key in [
                "id","folder","reference_control","type","status","effort","name","description","eta","link","created_at","updated_at"
            ]
        } for mtg in measures]
        for i in range(len(measures)) :
            measures[i]["id"] = str(measures[i]["id"])
            measures[i]["folder"] = str(measures[i]["folder"].name)
            for key in ["created_at","updated_at","eta"] :
                measures[i][key] = str(measures[i][key])"""

        ranking_scores = {str(mtg.id): mtg.get_ranking_score() for mtg in measures}

        measures = [AppliedControlReadSerializer(mtg).data for mtg in measures]

        # How to add ranking_score directly in the serializer ?

        for i in range(len(measures)):
            measures[i]["ranking_score"] = ranking_scores[measures[i]["id"]]

        """
        The serializer of AppliedControl isn't applied automatically for this function
        """

        return Response({"results": measures})

    @action(detail=False, name="Get the secuity measures to review")
    def to_review(self, request):
        measures = measures_to_review(request.user)

        """print("ODZFFHZ")
        print(measures[0].get_ranking_score())"""

        measures = [AppliedControlReadSerializer(mtg).data for mtg in measures]

        """
        The serializer of AppliedControl isn't applied automatically for this function
        """

        return Response({"results": measures})


class PolicyViewSet(AppliedControlViewSet):
    model = Policy
    filterset_fields = [
        "folder",
        "status",
        "reference_control",
        "effort",
        "risk_scenarios",
        "requirement_assessments",
        "evidences",
    ]
    search_fields = ["name", "description", "risk_scenarios", "requirement_assessments"]


class RiskScenarioViewSet(BaseModelViewSet):
    """
    API endpoint that allows risk scenarios to be viewed or edited.
    """

    model = RiskScenario
    filterset_fields = [
        "risk_assessment",
        "risk_assessment__project",
        "risk_assessment__project__folder",
        "treatment",
        "threats",
        "assets",
        "applied_controls",
    ]

    @action(detail=False, name="Get treatment choices")
    def treatment(self, request):
        return Response(dict(RiskScenario.TREATMENT_OPTIONS))

    @action(detail=True, name="Get probability choices")
    def probability(self, request, pk):
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in self.get_object().get_matrix()["probability"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)

    @action(detail=True, name="Get impact choices")
    def impact(self, request, pk):
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in self.get_object().get_matrix()["impact"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)

    @action(detail=True, name="Get strength of knowledge choices")
    def strength_of_knowledge(self, request, pk):
        undefined = {-1: RiskScenario.DEFAULT_SOK_OPTIONS[-1]}
        _sok_choices = self.get_object().get_matrix().get("strength_of_knowledge")
        if _sok_choices is not None:
            sok_choices = dict(
                zip(
                    list(range(0, 64)),
                    [
                        {
                            "name": x["name"],
                            "description": x.get("description"),
                            "symbol": x.get("symbol"),
                        }
                        for x in _sok_choices
                    ],
                )
            )
        else:
            sok_choices = RiskScenario.DEFAULT_SOK_OPTIONS
        choices = undefined | sok_choices
        return Response(choices)

    @action(detail=False, name="Get risk count per level")
    def count_per_level(self, request):
        return Response({"results": risks_count_per_level(request.user)})

    @action(detail=False, name="Get risk scenarios count per status")
    def per_status(self, request):
        return Response({"results": risk_per_status(request.user)})


class RiskAcceptanceViewSet(BaseModelViewSet):
    """
    API endpoint that allows risk acceptance to be viewed or edited.
    """

    model = RiskAcceptance
    serializer_class = RiskAcceptanceWriteSerializer
    filterset_fields = ["folder", "state", "approver", "risk_scenarios"]
    search_fields = ["name", "description", "justification"]

    def update(self, request, *args, **kwargs):
        initial_data = self.get_object()
        updated_data = request.data
        if (
            updated_data.get("justification") != initial_data.justification
            and request.user != initial_data.approver
        ):
            _data = {
                "non_field_errors": "The justification can only be edited by the approver"
            }
            return Response(data=_data, status=HTTP_400_BAD_REQUEST)
        else:
            return super().update(request, *args, **kwargs)

    @action(detail=False, name="Get acceptances to review")
    def to_review(self, request):
        acceptances = acceptances_to_review(request.user)

        acceptances = [
            RiskAcceptanceReadSerializer(acceptance).data for acceptance in acceptances
        ]

        """
        The serializer of AppliedControl isn't applied automatically for this function
        """

        return Response({"results": acceptances})

    @action(detail=True, methods=["post"], name="Accept risk acceptance")
    def accept(self, request, pk):
        if request.user == self.get_object().approver:
            self.get_object().set_state("accepted")
        return Response({"results": "state updated to accepted"})

    @action(detail=True, methods=["post"], name="Reject risk acceptance")
    def reject(self, request, pk):
        if request.user == self.get_object().approver:
            self.get_object().set_state("rejected")
        return Response({"results": "state updated to rejected"})

    @action(detail=True, methods=["post"], name="Revoke risk acceptance")
    def revoke(self, request, pk):
        if request.user == self.get_object().approver:
            self.get_object().set_state("revoked")
        return Response({"results": "state updated to revoked"})

    def perform_create(self, serializer):
        risk_acceptance = serializer.validated_data
        submitted = False
        print(risk_acceptance)
        if risk_acceptance.get("approver"):
            submitted = True
        for scenario in risk_acceptance.get("risk_scenarios"):
            if not RoleAssignment.is_access_allowed(
                risk_acceptance.get("approver"),
                Permission.objects.get(codename="approve_riskacceptance"),
                scenario.risk_assessment.project.folder,
            ):
                raise ValidationError(
                    "The approver is not allowed to approve this risk acceptance"
                )
        risk_acceptance = serializer.save()
        if submitted:
            risk_acceptance.set_state("submitted")


class UserFilter(df.FilterSet):
    is_approver = df.BooleanFilter(method="filter_approver", label="Approver")

    def filter_approver(self, queryset, name, value):
        """we don't know yet which folders will be used, so filter on any folder"""
        approvers_id = []
        for candidate in User.objects.all():
            if "approve_riskacceptance" in candidate.permissions:
                approvers_id.append(candidate.id)
        if value:
            return queryset.filter(id__in=approvers_id)
        return queryset.exclude(id__in=approvers_id)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "is_active", "is_approver"]


class UserViewSet(BaseModelViewSet):
    """
    API endpoint that allows users to be viewed or edited
    """

    model = User
    ordering = ["-is_active", "-is_superuser", "email", "id"]
    ordering_fields = ordering
    filterset_class = UserFilter
    search_fields = ["email", "first_name", "last_name"]

    def get_queryset(self):
        # TODO: Implement a proper filter for the queryset
        return User.objects.all()


class UserGroupViewSet(BaseModelViewSet):
    """
    API endpoint that allows user groups to be viewed or edited
    """

    model = UserGroup
    ordering = ["builtin", "name"]
    ordering_fields = ordering
    filterset_fields = ["folder"]


class RoleViewSet(BaseModelViewSet):
    """
    API endpoint that allows roles to be viewed or edited
    """

    model = Role
    ordering = ["builtin", "name"]
    ordering_fields = ordering


class RoleAssignmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows role assignments to be viewed or edited.
    """

    model = RoleAssignment
    ordering = ["builtin", "folder"]
    ordering_fields = ordering
    filterset_fields = ["folder"]


class FolderViewSet(BaseModelViewSet):
    """
    API endpoint that allows folders to be viewed or edited.
    """

    model = Folder
    filterset_fields = ["parent_folder", "content_type"]

    def perform_create(self, serializer):
        """
        Create the default user groups after domain creation
        """
        serializer.save()
        folder = Folder.objects.get(id=serializer.data["id"])
        if folder.content_type == Folder.ContentType.DOMAIN:
            auditors = UserGroup.objects.create(
                name=UserGroupCodename.AUDITOR, folder=folder, builtin=True
            )
            approvers = UserGroup.objects.create(
                name=UserGroupCodename.APPROVER, folder=folder, builtin=True
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
                is_recursive=True,
            )
            ra1.perimeter_folders.add(folder)
            ra2 = RoleAssignment.objects.create(
                user_group=approvers,
                role=Role.objects.get(name=RoleCodename.APPROVER),
                builtin=True,
                folder=Folder.get_root_folder(),
                is_recursive=True,
            )
            ra2.perimeter_folders.add(folder)
            ra3 = RoleAssignment.objects.create(
                user_group=analysts,
                role=Role.objects.get(name=RoleCodename.ANALYST),
                builtin=True,
                folder=Folder.get_root_folder(),
                is_recursive=True,
            )
            ra3.perimeter_folders.add(folder)
            ra4 = RoleAssignment.objects.create(
                user_group=managers,
                role=Role.objects.get(name=RoleCodename.DOMAIN_MANAGER),
                builtin=True,
                folder=Folder.get_root_folder(),
                is_recursive=True,
            )
            ra4.perimeter_folders.add(folder)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_counters_view(request):
    """
    API endpoint that returns the counters
    """
    return Response({"results": get_counters(request.user)})


# TODO: Add all the proper docstrings for the following list of functions


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_agg_data(request):
    viewable_risk_assessments = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), request.user, RiskAssessment
    )[0]
    data = risk_status(
        request.user, RiskAssessment.objects.filter(id__in=viewable_risk_assessments)
    )

    return Response({"results": data})


def serialize_nested(data: Any) -> dict:
    if isinstance(data, (list, tuple)):
        return [serialize_nested(i) for i in data]
    elif isinstance(data, dict):
        return {key: serialize_nested(value) for key, value in data.items()}
    elif isinstance(data, set):
        return {serialize_nested(i) for i in data}
    elif isinstance(data, ReturnDict):
        return dict(data)
    elif isinstance(data, models.query.QuerySet):
        return serialize_nested(list(data))
    elif isinstance(data, RiskAssessment):
        return RiskAssessmentReadSerializer(data).data
    elif isinstance(data, RiskScenario):
        return RiskScenarioReadSerializer(data).data
    elif isinstance(data, uuid.UUID):
        return str(data)
    elif isinstance(data, Promise):
        str_attr = {attr for attr in dir(str) if not attr.startswith("_")}
        proxy_attr = {attr for attr in dir(data) if not attr.startswith("_")}
        if len(str_attr - proxy_attr) == 0:
            return str(data)
    return data


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_composer_data(request):
    risk_assessments = request.GET.get("risk_assessment")
    if risk_assessments is None:
        return Response(
            {"error": "This endpoint requires the 'risk_assessment' query parameter"},
            status=400,
        )

    risk_assessments = risk_assessments.split(",")
    if not all(
        re.fullmatch(
            r"([0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12})",  # UUID REGEX
            risk_assessment,
        )
        for risk_assessment in risk_assessments
    ):
        return Response({"error": "Invalid UUID list"}, status=400)

    data = compile_risk_assessment_for_composer(request.user, risk_assessments)
    for _data in data["risk_assessment_objects"]:
        quality_check = serialize_nested(_data["risk_assessment"].quality_check())
        _data["risk_assessment"] = RiskAssessmentReadSerializer(
            _data["risk_assessment"]
        ).data
        _data["risk_assessment"]["quality_check"] = quality_check

    data = serialize_nested(data)
    return Response({"result": data})


# Compliance Assessment


class FrameworkViewSet(BaseModelViewSet):
    """
    API endpoint that allows frameworks to be viewed or edited.
    """

    model = Framework
    filterset_fields = ["folder"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "description"]

    @action(detail=False, methods=["get"])
    def names(self, request):
        uuid_list = request.query_params.getlist("id[]", [])
        queryset = Framework.objects.filter(id__in=uuid_list)

        return Response({str(framework.id): framework.name for framework in queryset})

    @action(detail=True, methods=["get"])
    def tree(self, request, pk):
        _framework = Framework.objects.get(id=pk)
        return Response(
            get_sorted_requirement_nodes(
                RequirementNode.objects.filter(framework=_framework).all(), None
            )
        )

    @action(detail=False, name="Get used frameworks")
    def used(self, request):
        _used_frameworks = Framework.objects.filter(
            complianceassessment__isnull=False
        ).distinct()
        used_frameworks = _used_frameworks.values("id", "name")
        for i in range(len(used_frameworks)):
            used_frameworks[i]["compliance_assessments_count"] = _used_frameworks.get(
                id=used_frameworks[i]["id"]
            ).complianceassessment_set.count()
        return Response({"results": used_frameworks})


class RequirementNodeViewSet(BaseModelViewSet):
    """
    API endpoint that allows requirement groups to be viewed or edited.
    """

    model = RequirementNode
    filterset_fields = ["framework", "urn"]
    search_fields = ["name", "description"]


class RequirementLevelViewSet(BaseModelViewSet):
    """
    API endpoint that allows requirement levels to be viewed or edited.
    """

    model = RequirementLevel
    filterset_fields = ["framework"]
    search_fields = ["name"]


class RequirementViewSet(BaseModelViewSet):
    """
    API endpoint that allows requirements to be viewed or edited.
    """

    model = RequirementNode
    filterset_fields = ["framework", "urn"]
    search_fields = ["name"]


class EvidenceViewSet(BaseModelViewSet):
    """
    API endpoint that allows evidences to be viewed or edited.
    """

    model = Evidence
    filterset_fields = ["folder", "applied_controls", "requirement_assessments"]
    search_fields = ["name"]
    ordering_fields = ["name", "description"]

    @action(methods=["get"], detail=True)
    def attachment(self, request, pk):
        (
            object_ids_view,
            _,
            _,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, Evidence
        )
        response = Response(status=status.HTTP_403_FORBIDDEN)
        if UUID(pk) in object_ids_view:
            evidence = self.get_object()
            if not evidence.attachment:
                return Response(status=status.HTTP_404_NOT_FOUND)
            if request.method == "GET":
                content_type = mimetypes.guess_type(evidence.filename())[0]
                response = HttpResponse(
                    evidence.attachment,
                    content_type=content_type,
                    status=status.HTTP_200_OK,
                )
        return response

    @action(methods=["post"], detail=True)
    def delete_attachment(self, request, pk):
        (
            object_ids_view,
            _,
            _,
        ) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, Evidence
        )
        response = Response(status=status.HTTP_403_FORBIDDEN)
        if UUID(pk) in object_ids_view:
            evidence = self.get_object()
            if evidence.attachment:
                evidence.attachment.delete()
                evidence.save()
                response = Response(status=status.HTTP_200_OK)
        return response


class UploadAttachmentView(APIView):
    parser_classes = (FileUploadParser,)
    serializer_class = AttachmentUploadSerializer

    def post(self, request, *args, **kwargs):
        if request.data:
            try:
                evidence = Evidence.objects.get(id=kwargs["pk"])
                attachment = request.FILES["file"]
                evidence.attachment = attachment
                evidence.save()
                return Response(status=status.HTTP_200_OK)
            except Exception as e:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class ComplianceAssessmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows compliance assessments to be viewed or edited.
    """

    model = ComplianceAssessment
    filterset_fields = ["framework", "project", "status"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "description"]

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(ComplianceAssessment.Status.choices))

    def perform_create(self, serializer):
        """
        Create RequirementAssessment objects for the newly created ComplianceAssessment
        """
        serializer.save()
        instance = ComplianceAssessment.objects.get(id=serializer.data["id"])
        requirements = RequirementNode.objects.filter(framework=instance.framework)
        for requirement in requirements:
            RequirementAssessment.objects.create(
                compliance_assessment=instance,
                requirement=requirement,
                folder=Folder.objects.get(id=instance.project.folder.id),
            )

    @action(detail=False, name="Compliance assessments per status")
    def per_status(self, request):
        data = assessment_per_status(request.user, ComplianceAssessment)
        return Response({"results": data})

    @action(detail=False, methods=["get"])
    def quality_check(self, request):
        """
        Returns the quality check of every compliance assessment
        """
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=ComplianceAssessment,
        )
        compliance_assessments = ComplianceAssessment.objects.filter(
            id__in=viewable_objects
        )
        res = [
            {"id": a.id, "name": a.name, "quality_check": a.quality_check()}
            for a in compliance_assessments
        ]
        return Response({"results": res})

    @action(detail=True, methods=["get"], url_path="quality_check")
    def quality_check_detail(self, request, pk):
        """
        Returns the quality check of a specific assessment
        """
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(), user=request.user, object_type=Assessment
        )
        if UUID(pk) in viewable_objects:
            compliance_assessment = self.get_object()
            return Response(compliance_assessment.quality_check())
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=["get"])
    def tree(self, request, pk):
        _framework = self.get_object().framework
        return Response(
            get_sorted_requirement_nodes(
                RequirementNode.objects.filter(framework=_framework).all(),
                RequirementAssessment.objects.filter(
                    compliance_assessment=self.get_object()
                ).all(),
            )
        )

    @action(detail=True)
    def export(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, ComplianceAssessment
        )
        if UUID(pk) in object_ids_view:
            compliance_assessment = self.get_object()
            (index_content, evidences) = generate_html(compliance_assessment)
            zip_name = f"{compliance_assessment.name.replace('/', '-')}-{compliance_assessment.framework.name.replace('/', '-')}-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.zip"
            with zipfile.ZipFile(zip_name, "w") as zipf:
                for evidence in evidences:
                    if evidence.attachment:
                        with tempfile.NamedTemporaryFile(delete=True) as tmp:
                            # Download the attachment to the temporary file
                            if default_storage.exists(evidence.attachment.name):
                                file = default_storage.open(evidence.attachment.name)
                                tmp.write(file.read())
                                tmp.flush()
                                zipf.write(
                                    tmp.name,
                                    os.path.join(
                                        "evidences",
                                        os.path.basename(evidence.attachment.name),
                                    ),
                                )
                zipf.writestr("index.html", index_content)

            response = FileResponse(open(zip_name, "rb"), as_attachment=True)
            response["Content-Disposition"] = f'attachment; filename="{zip_name}"'
            os.remove(zip_name)
            return response
        else:
            return Response({"error": "Permission denied"})

    @action(detail=True, methods=["get"])
    def donut_data(self, request, pk):
        compliance_assessment = ComplianceAssessment.objects.get(id=pk)
        return Response(compliance_assessment.donut_render())


class RequirementAssessmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows requirement assessments to be viewed or edited.
    """

    model = RequirementAssessment
    filterset_fields = ["folder", "evidences"]
    search_fields = ["name", "description"]

    @action(detail=False, name="Get updatable measures")
    def updatables(self, request):
        (_, object_ids_change, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, AppliedControl
        )

        return Response({"results": object_ids_change})

    @action(
        detail=False, name="Something"
    )  # Write a good name for the "name" keyword argument
    def per_status(self, request):
        data = applied_control_per_status(request.user)
        return Response({"results": data})

    @action(detail=False, name="Get the ordered todo applied controls")
    def todo(self, request):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, AppliedControl
        )

        measures = sorted(
            AppliedControl.objects.filter(id__in=object_ids_view)
            .exclude(status="done")
            .order_by("eta"),
            key=lambda mtg: mtg.get_ranking_score(),
            reverse=True,
        )

        """measures = [{
            key: getattr(mtg,key)
            for key in [
                "id","folder","reference_control","type","status","effort","name","description","eta","link","created_at","updated_at"
            ]
        } for mtg in measures]
        for i in range(len(measures)) :
            measures[i]["id"] = str(measures[i]["id"])
            measures[i]["folder"] = str(measures[i]["folder"].name)
            for key in ["created_at","updated_at","eta"] :
                measures[i][key] = str(measures[i][key])"""

        ranking_scores = {str(mtg.id): mtg.get_ranking_score() for mtg in measures}

        measures = [AppliedControlReadSerializer(mtg).data for mtg in measures]

        # How to add ranking_score directly in the serializer ?

        for i in range(len(measures)):
            measures[i]["ranking_score"] = ranking_scores[measures[i]["id"]]

        """
        The serializer of AppliedControl isn't applied automatically for this function
        """

        return Response({"results": measures})

    @action(detail=False, name="Get the secuity measures to review")
    def to_review(self, request):
        measures = measures_to_review(request.user)

        """print("ODZFFHZ")
        print(measures[0].get_ranking_score())"""

        measures = [AppliedControlReadSerializer(mtg).data for mtg in measures]

        """
        The serializer of AppliedControl isn't applied automatically for this function
        """

        return Response({"results": measures})

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(RequirementAssessment.Status.choices))


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def get_csrf_token(request):
    """
    API endpoint that returns the CSRF token.
    """
    return Response({"csrfToken": csrf.get_token(request)})


@api_view(["GET"])
def get_build(request):
    """
    API endpoint that returns the build version of the application.
    """
    return Response({"version": VERSION, "build": BUILD})


# NOTE: Important functions/classes from old views.py, to be reviewed


class FirstConnexionPasswordConfirmView(PasswordResetConfirmView):
    template_name = "registration/first_connexion_confirm.html"
    form_class = FirstConnexionConfirmForm


def generate_html(
    compliance_assessment: ComplianceAssessment,
) -> Tuple[str, list[Evidence]]:
    selected_evidences = []

    requirement_nodes = RequirementNode.objects.filter(
        framework=compliance_assessment.framework
    )

    assessments = RequirementAssessment.objects.filter(
        compliance_assessment=compliance_assessment,
    ).all()

    node_per_urn = {r.urn: r for r in requirement_nodes}
    ancestors = {}
    for a in assessments:
        ancestors[a] = set()
        req = a.requirement
        while req:
            ancestors[a].add(req)
            p = req.parent_urn
            req = None if not (p) else node_per_urn[p]

    def bar_graph(node: RequirementNode):
        """return bar graph filtered by top node (Null for all)"""
        content = ""
        compliance_assessments_status = []
        candidates = [
            c
            for c in assessments.filter(requirement__assessable=True)
            if not (node) or c == node or node in ancestors[c]
        ]
        total = len(candidates)
        if total > 0:
            for st in RequirementAssessment.Status:
                count = len([c for c in candidates if c.status == st])
                compliance_assessments_status.append((st, round(count * 100 / total)))
        content += (
            '<div class="flex bg-gray-300 rounded-full overflow-hidden h-4 w-2/3">'
        )
        for stat in reversed(compliance_assessments_status):
            if stat[1] > 0:
                content += '<div class="flex flex-col justify-center overflow-hidden text-xs font-semibold text-center '
                if stat[0] == "in_progress":
                    content += "bg-blue-500"
                elif stat[0] == "non_compliant":
                    content += "bg-red-500"
                elif stat[0] == "partially_compliant":
                    content += "bg-yellow-400"
                elif stat[0] == "compliant":
                    content += "bg-green-500"
                elif stat[0] == "not_applicable":
                    content += "bg-black text-white dark:bg-white dark:text-black"
                content += '" style="width:' + str(stat[1]) + '%"> '
                if stat[0] != "to_do":
                    content += str(stat[1]) + "%"

                content += "</div>"
        content += "</div></div>"
        return content

    content = """
    <html lang="en">
    <head>
    <link rel="stylesheet" href="https://unpkg.com/dezui@latest">
    <script src="https://cdn.tailwindcss.com"></script>
    <title>Compliance report</title>
    </head>
    <body class="container container-tablet">
    """
    content += '<hr class="dotted">'
    content += '<div class="flex flex-row space-x-4 justify-center items-center mb-4">'
    content += f"<h1 class='text-3xl'>{compliance_assessment.name}: {compliance_assessment.framework}</h1>"
    content += bar_graph(None)
    content += "</div>"
    table = """
    <thead>
    </thead>
    <tbody>
    """
    content += '<div class="flex flex-row space-x-4 mb-4">'

    content += "<div>"
    content += "<p class='font-semibold'>Authors</p>"
    content += "<ul>"
    for author in compliance_assessment.authors.all():
        content += f"<li>{author}</li>"
    content += "</ul>"
    content += "</div>"

    content += "<div>"
    content += "<p class='font-semibold'>Reviewers</p>"
    content += "<ul>"
    for reviewer in compliance_assessment.reviewers.all():
        content += f"<li>{reviewer}</li>"
    content += "</ul>"
    content += "</div>"

    content += "</div>"

    def generate_html_rec(requirement_node: RequirementNode):
        selected_evidences = []
        table = ""
        children_nodes = [
            req for req in requirement_nodes if req.parent_urn == requirement_node.urn
        ]
        if not requirement_node.assessable:
            _display = requirement_node.display_long
            table += f'<p class="font-semibold">{_display}  </p>'
            if children_nodes:
                table += bar_graph(requirement_node)
        else:
            assessment = RequirementAssessment.objects.filter(
                requirement__urn=requirement_node.urn
            ).first()

            table += "<div>"
            table += "<div class='flex flex-col shadow-md border rounded-lg px-4 py-2 m-2 ml-0 items-center "
            match assessment.status:
                case "compliant":
                    table += "border-t-2 border-t-green-500 border-green-500'>"
                case "to_do":
                    table += "border-t-2 border-t-gray-300 border-gray-300'>"
                case "in_progress":
                    table += "border-t-2 border-t-blue-500 border-blue-500'>"
                case "non_compliant":
                    table += "border-t-2 border-t-red-500 border-red-500'>"
                case "partially_compliant":
                    table += "border-t-2 border-t-yellow-400 border-yellow-400'>"
                case "not_applicable":
                    table += "border-t-2 border-t-black border-black'>"
            table += '<div class="flex flex-row justify-between w-full">'
            table += f"<p class='font-semibold'>{assessment.requirement}</p>"
            table += "<p class='text-white text-center rounded-lg whitespace-nowrap px-2 py-1 "
            match assessment.status:
                case "compliant":
                    table += f"bg-green-500'>{assessment.get_status_display()}</p>"
                case "to_do":
                    table += f"bg-gray-300'>{assessment.get_status_display()}</p>"
                case "in_progress":
                    table += f"bg-blue-500'>{assessment.get_status_display()}</p>"
                case "non_compliant":
                    table += f"bg-red-500'>{assessment.get_status_display()}</p>"
                case "partially_compliant":
                    table += f"bg-yellow-400'>{assessment.get_status_display()}</p>"
                case "not_applicable":
                    table += (
                        f"bg-black tewt-white'>{assessment.get_status_display()}</p>"
                    )
            table += "</div>"
            table += (
                f"<p class='text-left w-full'>{assessment.requirement.description}</p>"
            )
            table += "</div>"
            if children_nodes:
                table += bar_graph(requirement_node)

            direct_evidences = assessment.evidences.all()
            if direct_evidences:
                selected_evidences += direct_evidences
                table += '<div class="flex flex-col px-4 py-2 m-2 ml-0 rounded-lg bg-indigo-200">'
                table += (
                    '<div class="grid grid-cols-2 justify-items-left font-semibold">'
                )
                table += f'<p>{("Associated evidence")}:</p>'
                table += "</div>"
                for direct_evidence in direct_evidences:
                    if direct_evidence.attachment:
                        table += f'<li> <a class="text-indigo-700 hover:text-indigo-500" target="_blank" href="evidences/{direct_evidence.attachment}">{direct_evidence.name}</a></li>'
                    else:
                        table += f"<li> {direct_evidence.name}</li>"
                table += "</div>"

            measures = assessment.applied_controls.all()
            if measures:
                table += '<div class="flex flex-col px-4 py-2 m-2 ml-0 rounded-lg bg-indigo-200">'
                evidences = ""
                table += (
                    '<div class="grid grid-cols-2 justify-items-left font-semibold">'
                )
                table += f'<p>{("Applied applied controls")}:</p>'
                table += f'<p>{("Associated evidence")}:</p>'
                table += "</div>"
                table += '<div class="flex flex-row">'
                table += '<div class="flex flex-col items-left w-1/2">'
                for measure in measures:
                    table += f"<li> {measure.name}: {measure.get_status_display()}</li>"
                    for evidence in measure.evidences.all():
                        selected_evidences.append(evidence)
                        if evidence.attachment:
                            evidences += f'<li> <a class="text-indigo-700 hover:text-indigo-500" target="_blank" href="evidences/{evidence.attachment}">{measure.name}/{evidence.name}</a></li>'
                        else:
                            evidences += f"<li> {evidence.name}</li>"
                table += "</div>"
                table += (
                    f'<div class="flex flex-col items-left w-1/2">{evidences}</div>'
                )
                table += "</div></div>"
            table += "</div>"
        for child_node in children_nodes:
            (table2, selected_evidences2) = generate_html_rec(child_node)
            table += table2
            selected_evidences += selected_evidences2
        return (table, selected_evidences)

    top_level_nodes = [req for req in requirement_nodes if not req.parent_urn]
    for requirement_node in top_level_nodes:
        (table2, selected_evidences2) = generate_html_rec(requirement_node)
        table += table2
        selected_evidences += selected_evidences2
    table += "</tbody><br/>"
    content += table
    content += """
    </body>
    </html>
    """

    return (content, selected_evidences)


def export_mp_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="MP.csv"'

    writer = csv.writer(response, delimiter=";")
    columns = [
        "measure_id",
        "measure_name",
        "measure_desc",
        "category",
        "reference_control",
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
        Folder.get_root_folder(), request.user, AppliedControl
    )
    for mtg in AppliedControl.objects.filter(id__in=object_ids_view):
        row = [
            mtg.id,
            mtg.name,
            mtg.description,
            mtg.category,
            mtg.reference_control,
            mtg.eta,
            mtg.effort,
            mtg.link,
            mtg.status,
        ]
        writer.writerow(row)

    return response
