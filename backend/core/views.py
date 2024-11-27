import csv
import mimetypes
import re
import tempfile
import uuid
import zipfile
from datetime import date, datetime, timedelta
import time
import pytz
from typing import Any, Tuple
from uuid import UUID
from itertools import cycle
import django_filters as df
from ciso_assistant.settings import BUILD, VERSION, EMAIL_HOST, EMAIL_HOST_RESCUE

import shutil
from pathlib import Path
import humanize

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache

from django.db.models import F, Q

from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models
from django.forms import ValidationError
from django.http import FileResponse, HttpResponse
from django.middleware import csrf
from django.template.loader import render_to_string
from django.utils.functional import Promise
from django_filters.rest_framework import DjangoFilterBackend
from iam.models import Folder, RoleAssignment, UserGroup
from rest_framework import filters, permissions, status, viewsets
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
    renderer_classes,
)
from rest_framework.parsers import FileUploadParser
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from rest_framework.utils.serializer_helpers import ReturnDict
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny


from weasyprint import HTML

from core.helpers import *
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    RequirementMappingSet,
)
from core.serializers import ComplianceAssessmentReadSerializer
from core.utils import RoleCodename, UserGroupCodename

from .models import *
from .serializers import *

import structlog

logger = structlog.get_logger(__name__)

User = get_user_model()

SHORT_CACHE_TTL = 2  # mn
MED_CACHE_TTL = 5  # mn
LONG_CACHE_TTL = 60  # mn

SETTINGS_MODULE = __import__(os.environ.get("DJANGO_SETTINGS_MODULE"))
MODULE_PATHS = SETTINGS_MODULE.settings.MODULE_PATHS


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

    serializers_module = "core.serializers"

    def get_queryset(self):
        if not self.model:
            return None
        object_ids_view = None
        if self.request.method == "GET":
            if q := re.match("/api/[\w-]+/([0-9a-f-]+)", self.request.path):
                """"get_queryset is called by Django even for an individual object via get_object
                https://stackoverflow.com/questions/74048193/why-does-a-retrieve-request-end-up-calling-get-queryset"""
                id = UUID(q.group(1))
                if RoleAssignment.is_object_readable(self.request.user, self.model, id):
                    object_ids_view = [id]
        if not object_ids_view:
            object_ids_view = RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), self.request.user, self.model
            )[0]
        queryset = self.model.objects.filter(id__in=object_ids_view)
        return queryset

    def get_serializer_class(self, **kwargs):
        serializer_factory = SerializerFactory(
            self.serializers_module, MODULE_PATHS.get("serializers", [])
        )
        serializer_class = serializer_factory.get_serializer(
            self.model.__name__, kwargs.get("action", self.action)
        )
        logger.debug(
            "Serializer class",
            serializer_class=serializer_class,
            action=kwargs.get("action", self.action),
            viewset=self,
            module_paths=MODULE_PATHS,
        )

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

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        self._process_request_data(request)
        return super().destroy(request, *args, **kwargs)

    class Meta:
        abstract = True

    @action(detail=True, name="Get write data")
    def object(self, request, pk):
        serializer_class = self.get_serializer_class(action="update")

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

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, name="Get threats count")
    def threats_count(self, request):
        return Response({"results": threats_count_per_name(request.user)})


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

    @action(detail=False, name="Get assets graph")
    def graph(self, request):
        nodes = []
        links = []
        nodes_idx = dict()
        categories = []
        N = 0
        (viewable_folders, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Folder,
        )
        (viewable_assets, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Asset,
        )
        for domain in Folder.objects.filter(id__in=viewable_folders):
            categories.append({"name": domain.name})
            nodes_idx[domain.name] = N
            nodes.append(
                {
                    "name": domain.name,
                    "category": N,
                    "symbol": "roundRect",
                    "symbolSize": 30,
                    "value": "Domain",
                }
            )
            N += 1
        for asset in Asset.objects.filter(id__in=viewable_assets):
            symbol = "circle"
            if asset.type == "PR":
                symbol = "diamond"
            nodes.append(
                {
                    "name": asset.name,
                    "symbol": symbol,
                    "symbolSize": 25,
                    "category": nodes_idx[asset.folder.name],
                    "value": "Primary" if asset.type == "PR" else "Support",
                }
            )
            nodes_idx[asset.name] = N
            links.append(
                {"source": nodes_idx[asset.folder.name], "target": N, "value": "scope"}
            )
            N += 1
        for asset in Asset.objects.filter(id__in=viewable_assets):
            for relationship in asset.parent_assets.all():
                links.append(
                    {
                        "source": nodes_idx[relationship.name],
                        "target": nodes_idx[asset.name],
                        "value": "parent",
                    }
                )
        meta = {"display_name": f"Assets Explorer"}

        return Response(
            {"nodes": nodes, "links": links, "categories": categories, "meta": meta}
        )

    @action(detail=False, name="Get security objectives")
    def security_objectives(self, request):
        return Response({"results": Asset.DEFAULT_SECURITY_OBJECTIVES})

    @action(detail=False, name="Get disaster recovery objectives")
    def disaster_recovery_objectives(self, request):
        return Response({"results": Asset.DEFAULT_DISASTER_RECOVERY_OBJECTIVES})


class ReferenceControlViewSet(BaseModelViewSet):
    """
    API endpoint that allows reference controls to be viewed or edited.
    """

    model = ReferenceControl
    filterset_fields = ["folder", "category", "csf_function"]
    search_fields = ["name", "description", "provider"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(ReferenceControl.CATEGORY))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get function choices")
    def csf_function(self, request):
        return Response(dict(ReferenceControl.CSF_FUNCTION))


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
        viewable_matrices = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskMatrix
        )[0]
        viewable_assessments = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskAssessment
        )[0]
        _used_matrices = (
            RiskMatrix.objects.filter(riskassessment__isnull=False)
            .filter(id__in=viewable_matrices)
            .filter(riskassessment__id__in=viewable_assessments)
            .distinct()
        )
        used_matrices = _used_matrices.values("id", "name")
        for i in range(len(used_matrices)):
            used_matrices[i]["risk_assessments_count"] = (
                RiskAssessment.objects.filter(risk_matrix=_used_matrices[i].id)
                .filter(id__in=viewable_assessments)
                .count()
            )
        return Response({"results": used_matrices})


class VulnerabilityViewSet(BaseModelViewSet):
    """
    API endpoint that allows vulnerabilities to be viewed or edited.
    """

    model = Vulnerability
    filterset_fields = ["folder", "status", "severity", "risk_scenarios"]
    search_fields = ["name", "description"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(Vulnerability.Status.choices))

    def _process_labels(self, labels):
        """
        Creates a FilteringLabel and replaces the value with the ID of the newly created label.
        """
        new_labels = []
        for label in labels:
            try:
                uuid.UUID(label, version=4)
                new_labels.append(label)
            except ValueError:
                new_label = FilteringLabel(label=label)
                new_label.full_clean()
                new_label.save()
                new_labels.append(str(new_label.id))
        return new_labels

    def update(self, request: Request, *args, **kwargs) -> Response:
        request.data["filtering_labels"] = self._process_labels(
            request.data["filtering_labels"]
        )
        return super().update(request, *args, **kwargs)

    def create(self, request: Request, *args, **kwargs) -> Response:
        request.data["filtering_labels"] = self._process_labels(
            request.data["filtering_labels"]
        )
        return super().create(request, *args, **kwargs)


class FilteringLabelViewSet(BaseModelViewSet):
    """
    API endpoint that allows labels to be viewed or edited.
    """

    model = FilteringLabel
    filterset_fields = ["folder"]
    search_fields = ["label"]
    ordering = ["label"]


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

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
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
                "csf_function",
                "priority",
                "reference_control",
                "eta",
                "effort",
                "cost",
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
                        f"{scenario.ref_id}: {scenario.name}"
                        for scenario in mtg.risk_scenarios.all()
                    ]
                )
                row = [
                    risk_scenarios,
                    mtg.id,
                    mtg.name,
                    mtg.description,
                    mtg.get_category_display(),
                    mtg.get_csf_function_display(),
                    mtg.reference_control,
                    mtg.eta,
                    mtg.effort,
                    mtg.priority,
                    mtg.cost,
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
                "ref_id",
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
                    scenario.ref_id,
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

    @action(
        detail=True,
        name="Duplicate risk assessment",
        methods=["post"],
        serializer_class=RiskAssessmentDuplicateSerializer,
    )
    def duplicate(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskAssessment
        )

        if UUID(pk) in object_ids_view:
            risk_assessment = self.get_object()
            data = request.data

            duplicate_risk_assessment = RiskAssessment.objects.create(
                name=data["name"],
                description=data["description"],
                project=Project.objects.get(id=data["project"]),
                version=data["version"],
                risk_matrix=risk_assessment.risk_matrix,
                eta=risk_assessment.eta,
                due_date=risk_assessment.due_date,
                status=risk_assessment.status,
            )

            duplicate_risk_assessment.authors.set(risk_assessment.authors.all())
            duplicate_risk_assessment.reviewers.set(risk_assessment.reviewers.all())

            for scenario in risk_assessment.risk_scenarios.all():
                duplicate_scenario = RiskScenario.objects.create(
                    risk_assessment=duplicate_risk_assessment,
                    name=scenario.name,
                    description=scenario.description,
                    existing_controls=scenario.existing_controls,
                    treatment=scenario.treatment,
                    qualifications=scenario.qualifications,
                    current_proba=scenario.current_proba,
                    current_impact=scenario.current_impact,
                    residual_proba=scenario.residual_proba,
                    residual_impact=scenario.residual_impact,
                    strength_of_knowledge=scenario.strength_of_knowledge,
                    justification=scenario.justification,
                )

                for field in ["applied_controls", "threats", "assets"]:
                    duplicate_related_objects(
                        scenario,
                        duplicate_scenario,
                        duplicate_risk_assessment.project.folder,
                        field,
                    )

                if (
                    duplicate_risk_assessment.project.folder
                    in [risk_assessment.project.folder]
                    + risk_assessment.project.folder.sub_folders()
                ):
                    duplicate_scenario.owner.set(scenario.owner.all())

                duplicate_scenario.save()

            duplicate_risk_assessment.save()
            return Response({"results": "risk assessment duplicated"})


def convert_date_to_timestamp(date):
    """
    Converts a date object (datetime.date) to a Linux timestamp.
    It creates a datetime object for the date at midnight and makes it timezone-aware.
    """
    if date:
        date_as_datetime = datetime.combine(date, datetime.min.time())
        aware_datetime = pytz.UTC.localize(date_as_datetime)
        return int(time.mktime(aware_datetime.timetuple())) * 1000
    return None


class AppliedControlViewSet(BaseModelViewSet):
    """
    API endpoint that allows applied controls to be viewed or edited.
    """

    model = AppliedControl
    filterset_fields = [
        "folder",
        "category",
        "csf_function",
        "priority",
        "status",
        "reference_control",
        "effort",
        "cost",
        "risk_scenarios",
        "risk_scenarios_e",
        "requirement_assessments",
        "evidences",
    ]
    search_fields = ["name", "description", "risk_scenarios", "requirement_assessments"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(AppliedControl.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(AppliedControl.CATEGORY))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get csf_function choices")
    def csf_function(self, request):
        return Response(dict(AppliedControl.CSF_FUNCTION))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get priority choices")
    def priority(self, request):
        return Response(dict(AppliedControl.PRIORITY))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
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
            .filter(eta__lte=date.today() + timedelta(days=30))
            .exclude(status="active")
            .order_by("eta"),
            key=lambda mtg: mtg.get_ranking_score(),
            reverse=True,
        )

        """measures = [{
            key: getattr(mtg,key)
            for key in [
                "id","folder","reference_control","type","status","effort", "cost", "name","description","eta","link","created_at","updated_at"
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

        measures = [AppliedControlReadSerializer(mtg).data for mtg in measures]

        """
        The serializer of AppliedControl isn't applied automatically for this function
        """

        return Response({"results": measures})

    @action(detail=False, name="Export controls as CSV")
    def export_csv(self, request):
        (viewable_controls_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, AppliedControl
        )
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_export.csv"'

        writer = csv.writer(response, delimiter=";")
        columns = [
            "internal_id",
            "name",
            "description",
            "category",
            "csf_function",
            "status",
            "eta",
            "owner",
        ]
        writer.writerow(columns)

        for control in AppliedControl.objects.filter(id__in=viewable_controls_ids):
            row = [
                control.id,
                control.name,
                control.description,
                control.category,
                control.csf_function,
                control.status,
                control.eta,
            ]
            if len(control.owner.all()) > 0:
                owners = ",".join([o.email for o in control.owner.all()])
                row += [owners]
            writer.writerow(row)
        return response

    @action(detail=False, methods=["get"])
    def get_controls_info(self, request):
        nodes = list()
        links = list()
        for ac in AppliedControl.objects.all():
            related_items_count = 0
            for ca in ComplianceAssessment.objects.filter(
                requirement_assessments__applied_controls=ac
            ).distinct():
                audit_coverage = (
                    RequirementAssessment.objects.filter(compliance_assessment=ca)
                    .filter(applied_controls=ac)
                    .count()
                )
                related_items_count += audit_coverage
                links.append(
                    {
                        "source": ca.id,
                        "target": ac.id,
                        "coverage": audit_coverage,
                    }
                )
            for ra in RiskAssessment.objects.filter(
                risk_scenarios__applied_controls=ac
            ).distinct():
                risk_coverage = (
                    RiskScenario.objects.filter(risk_assessment=ra)
                    .filter(applied_controls=ac)
                    .count()
                )
                related_items_count += risk_coverage
                links.append(
                    {
                        "source": ra.id,
                        "target": ac.id,
                        "coverage": risk_coverage,
                    }
                )
            nodes.append(
                {
                    "id": ac.id,
                    "label": ac.name,
                    "shape": "hexagon",
                    "counter": related_items_count,
                    "color": "#47e845",
                }
            )
        for audit in ComplianceAssessment.objects.all():
            nodes.append(
                {
                    "id": audit.id,
                    "label": audit.name,
                    "shape": "circle",
                    "color": "#5D4595",
                }
            )
        for ra in RiskAssessment.objects.all():
            nodes.append(
                {
                    "id": ra.id,
                    "label": ra.name,
                    "shape": "square",
                    "color": "#E6499F",
                }
            )
        return Response(
            {
                "nodes": nodes,
                "links": links,
            }
        )

    @action(detail=False, methods=["get"])
    def get_timeline_info(self, request):
        entries = []
        COLORS_PALETTE = [
            "#F72585",
            "#7209B7",
            "#3A0CA3",
            "#4361EE",
            "#4CC9F0",
            "#A698DC",
        ]
        colorMap = {}
        (viewable_controls_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, AppliedControl
        )

        applied_controls = AppliedControl.objects.filter(
            id__in=viewable_controls_ids
        ).select_related("folder")

        for ac in applied_controls:
            if ac.eta:
                endDate = convert_date_to_timestamp(ac.eta)
                startDate = (
                    convert_date_to_timestamp(ac.start_date)
                    if ac.start_date
                    else endDate
                )
                entries.append(
                    {
                        "startDate": startDate,
                        "endDate": endDate,
                        "name": ac.name,
                        "description": ac.description
                        if ac.description
                        else "(no description)",
                        "domain": ac.folder.name,
                    }
                )
        color_cycle = cycle(COLORS_PALETTE)
        for domain in Folder.objects.all():
            colorMap[domain.name] = next(color_cycle)
        return Response({"entries": entries, "colorMap": colorMap})


class PolicyViewSet(AppliedControlViewSet):
    model = Policy
    filterset_fields = [
        "folder",
        "csf_function",
        "status",
        "reference_control",
        "effort",
        "risk_scenarios",
        "requirement_assessments",
        "evidences",
    ]
    search_fields = ["name", "description", "risk_scenarios", "requirement_assessments"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get csf_function choices")
    def csf_function(self, request):
        return Response(dict(AppliedControl.CSF_FUNCTION))


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

    def _perform_write(self, serializer):
        if not serializer.validated_data.get("ref_id"):
            risk_assessment = serializer.validated_data["risk_assessment"]
            ref_id = RiskScenario.get_default_ref_id(risk_assessment)
            serializer.validated_data["ref_id"] = ref_id
        serializer.save()

    def perform_create(self, serializer):
        return self._perform_write(serializer)

    def perform_update(self, serializer):
        return self._perform_write(serializer)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get treatment choices")
    def treatment(self, request):
        return Response(dict(RiskScenario.TREATMENT_OPTIONS))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get qualification choices")
    def qualifications(self, request):
        return Response(dict(RiskScenario.QUALIFICATIONS))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get probability choices")
    def probability(self, request, pk):
        undefined = {-1: "--"}
        _choices = {
            i: name
            for i, name in enumerate(
                x["name"] for x in self.get_object().get_matrix()["probability"]
            )
        }
        choices = undefined | _choices
        return Response(choices)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
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

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get strength of knowledge choices")
    def strength_of_knowledge(self, request, pk):
        undefined = {-1: RiskScenario.DEFAULT_SOK_OPTIONS[-1]}
        _sok_choices = self.get_object().get_matrix().get("strength_of_knowledge")
        if _sok_choices is not None:
            sok_choices = dict(
                enumerate(
                    {
                        "name": x["name"],
                        "description": x.get("description"),
                        "symbol": x.get("symbol"),
                    }
                    for x in _sok_choices
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

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def default_ref_id(self, request):
        risk_assessment_id = request.query_params.get("risk_assessment")
        if not risk_assessment_id:
            return Response(
                {"error": "Missing 'risk_assessment' parameter."}, status=400
            )
        try:
            risk_assessment = RiskAssessment.objects.get(pk=risk_assessment_id)

            # Use the class method to compute the default ref_id
            default_ref_id = RiskScenario.get_default_ref_id(risk_assessment)
            return Response({"results": default_ref_id})
        except Exception as e:
            logger.error("Error in default_ref_id: %s", str(e))
            return Response(
                {"error": "Error in default_ref_id has occurred."}, status=400
            )


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

    @action(detail=False, methods=["get"], name="Get waiting risk acceptances")
    def waiting(self, request):
        acceptance_count = RiskAcceptance.objects.filter(
            approver=request.user, state="submitted"
        ).count()
        return Response({"count": acceptance_count})

    def perform_create(self, serializer):
        risk_acceptance = serializer.validated_data
        submitted = False
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
        fields = [
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_approver",
            "is_third_party",
        ]


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

    def update(self, request: Request, *args, **kwargs) -> Response:
        user = self.get_object()
        if user.is_admin():
            number_of_admin_users = User.get_admin_users().count()
            admin_group = UserGroup.objects.get(name="BI-UG-ADM")
            if number_of_admin_users == 1:
                new_user_groups = set(request.data["user_groups"])
                if str(admin_group.pk) not in new_user_groups:
                    return Response(
                        {"error": "attemptToRemoveOnlyAdminUserGroup"},
                        status=HTTP_403_FORBIDDEN,
                    )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.is_admin():
            number_of_admin_users = User.get_admin_users().count()
            if number_of_admin_users == 1:
                return Response(
                    {"error": "attemptToDeleteOnlyAdminAccountError"},
                    status=HTTP_403_FORBIDDEN,
                )

        return super().destroy(request, *args, **kwargs)


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


class FolderFilter(df.FilterSet):
    owned = df.BooleanFilter(method="get_owned_folders", label="owned")
    content_type = df.MultipleChoiceFilter(
        choices=Folder.ContentType, lookup_expr="icontains"
    )

    def get_owned_folders(self, queryset, name, value):
        owned_folders_id = []
        for folder in Folder.objects.all():
            if folder.owner.all().first():
                owned_folders_id.append(folder.id)
        if value:
            return queryset.filter(id__in=owned_folders_id)
        return queryset.exclude(id__in=owned_folders_id)

    class Meta:
        model = Folder
        fields = ["parent_folder", "content_type", "owner", "owned"]


class FolderViewSet(BaseModelViewSet):
    """
    API endpoint that allows folders to be viewed or edited.
    """

    model = Folder
    filterset_class = FolderFilter

    def perform_create(self, serializer):
        """
        Create the default user groups after domain creation
        """
        serializer.save()
        folder = Folder.objects.get(id=serializer.data["id"])
        if folder.content_type == Folder.ContentType.DOMAIN:
            readers = UserGroup.objects.create(
                name=UserGroupCodename.READER, folder=folder, builtin=True
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
                user_group=readers,
                role=Role.objects.get(name=RoleCodename.READER),
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
            # Clear the cache after a new folder is created - purposely clearing everything

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def org_tree(self, request):
        """
        Returns the tree of domains and projects
        """
        tree = {"name": "Global", "children": []}

        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Folder,
        )
        folders_list = list()
        for folder in (
            Folder.objects.exclude(content_type="GL")
            .filter(id__in=viewable_objects, parent_folder=Folder.get_root_folder())
            .distinct()
        ):
            entry = {"name": folder.name, "children": get_folder_content(folder)}
            folders_list.append(entry)
        tree.update({"children": folders_list})

        return Response(tree)

    @action(detail=False, methods=["get"])
    def my_assignments(self, request):
        risk_assessments = RiskAssessment.objects.filter(
            Q(authors=request.user) | Q(reviewers=request.user)
        ).distinct()

        audits = (
            ComplianceAssessment.objects.filter(
                Q(authors=request.user) | Q(reviewers=request.user)
            )
            .order_by(F("eta").asc(nulls_last=True))
            .distinct()
        )

        sum = 0
        avg_progress = 0
        audits_count = audits.count()
        if audits_count > 0:
            for audit in audits:
                sum += audit.progress()
            avg_progress = int(sum / audits.count())

        controls = (
            AppliedControl.objects.filter(owner=request.user)
            .order_by(F("eta").asc(nulls_last=True))
            .distinct()
        )
        non_active_controls = controls.exclude(status="active")
        risk_scenarios = RiskScenario.objects.filter(owner=request.user).distinct()
        controls_progress = 0
        evidences_progress = 0
        tot_ac = controls.count()
        if tot_ac > 0:
            alive_ac = controls.filter(status="active").count()
            controls_progress = int((alive_ac / tot_ac) * 100)

            with_evidences = 0
            for ctl in controls:
                with_evidences += 1 if ctl.has_evidences() else 0

            evidences_progress = int((with_evidences / tot_ac) * 100)

        RA_serializer = RiskAssessmentReadSerializer(risk_assessments[:10], many=True)
        CA_serializer = ComplianceAssessmentReadSerializer(audits[:6], many=True)
        AC_serializer = AppliedControlReadSerializer(
            non_active_controls[:10], many=True
        )
        RS_serializer = RiskScenarioReadSerializer(risk_scenarios[:10], many=True)

        return Response(
            {
                "risk_assessments": RA_serializer.data,
                "audits": CA_serializer.data,
                "controls": AC_serializer.data,
                "risk_scenarios": RS_serializer.data,
                "metrics": {
                    "progress": {
                        "audits": avg_progress,
                        "controls": controls_progress,
                        "evidences": evidences_progress,
                    }
                },
            }
        )


@cache_page(60 * SHORT_CACHE_TTL)
@vary_on_cookie
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_counters_view(request):
    """
    API endpoint that returns the counters
    """
    return Response({"results": get_counters(request.user)})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def get_metrics_view(request):
    """
    API endpoint that returns the counters
    """
    return Response({"results": get_metrics(request.user)})


# TODO: Add all the proper docstrings for the following list of functions


@cache_page(60 * SHORT_CACHE_TTL)
@vary_on_cookie
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

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @method_decorator(vary_on_cookie)
    @action(detail=False, methods=["get"])
    def names(self, request):
        uuid_list = request.query_params.getlist("id[]", [])
        queryset = Framework.objects.filter(id__in=uuid_list)

        return Response(
            {
                str(framework.id): framework.get_name_translated()
                for framework in queryset
            }
        )

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["get"])
    def tree(self, request, pk):
        _framework = Framework.objects.get(id=pk)
        return Response(
            get_sorted_requirement_nodes(
                RequirementNode.objects.filter(framework=_framework).all(),
                None,
                _framework.max_score,
            )
        )

    @action(detail=False, name="Get used frameworks")
    def used(self, request):
        viewable_framework = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, Framework
        )[0]
        viewable_assessments = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, ComplianceAssessment
        )[0]
        _used_frameworks = (
            Framework.objects.filter(complianceassessment__isnull=False)
            .filter(id__in=viewable_framework)
            .filter(complianceassessment__id__in=viewable_assessments)
            .distinct()
        )
        used_frameworks = _used_frameworks.values("id", "name")
        for i in range(len(used_frameworks)):
            used_frameworks[i]["compliance_assessments_count"] = (
                ComplianceAssessment.objects.filter(framework=_used_frameworks[i].id)
                .filter(id__in=viewable_assessments)
                .count()
            )
        return Response({"results": used_frameworks})

    @action(detail=True, methods=["get"], name="Get target frameworks from mappings")
    def mappings(self, request, pk):
        framework = self.get_object()
        available_target_frameworks_objects = [framework]
        mappings = RequirementMappingSet.objects.filter(source_framework=framework)
        for mapping in mappings:
            available_target_frameworks_objects.append(mapping.target_framework)
        available_target_frameworks = FrameworkReadSerializer(
            available_target_frameworks_objects, many=True
        ).data
        return Response({"results": available_target_frameworks})


class RequirementNodeViewSet(BaseModelViewSet):
    """
    API endpoint that allows requirement groups to be viewed or edited.
    """

    model = RequirementNode
    filterset_fields = ["framework", "urn"]
    search_fields = ["name", "description"]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RequirementViewSet(BaseModelViewSet):
    """
    API endpoint that allows requirements to be viewed or edited.
    """

    model = RequirementNode
    filterset_fields = ["framework", "urn"]
    search_fields = ["name"]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class EvidenceViewSet(BaseModelViewSet):
    """
    API endpoint that allows evidences to be viewed or edited.
    """

    model = Evidence
    filterset_fields = ["folder", "applied_controls", "requirement_assessments", "name"]
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
                    headers={
                        "Content-Disposition": f"attachment; filename={evidence.filename()}"
                    },
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
            except Exception:
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

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(ComplianceAssessment.Status.choices))

    @action(detail=True, methods=["get"], name="Get action plan data")
    def action_plan(self, request, pk):
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=ComplianceAssessment,
        )
        if UUID(pk) in viewable_objects:
            response = {
                "none": [],
                "to_do": [],
                "in_progress": [],
                "on_hold": [],
                "active": [],
                "deprecated": [],
            }
            compliance_assessment_object: ComplianceAssessment = self.get_object()
            requirement_assessments_objects = (
                compliance_assessment_object.get_requirement_assessments(
                    include_non_assessable=True
                )
            )
            applied_controls = [
                {
                    "id": applied_control.id,
                    "name": applied_control.name,
                    "description": applied_control.description,
                    "status": applied_control.status,
                    "category": applied_control.category,
                    "csf_function": applied_control.csf_function,
                    "eta": applied_control.eta,
                    "expiry_date": applied_control.expiry_date,
                    "link": applied_control.link,
                    "effort": applied_control.effort,
                    "cost": applied_control.cost,
                    "owners": [
                        {
                            "id": owner.id,
                            "email": owner.email,
                        }
                        for owner in applied_control.owner.all()
                    ],
                }
                for applied_control in AppliedControl.objects.filter(
                    requirement_assessments__in=requirement_assessments_objects
                ).distinct()
            ]

            for applied_control in applied_controls:
                applied_control["requirements_count"] = (
                    RequirementAssessment.objects.filter(
                        compliance_assessment=compliance_assessment_object
                    )
                    .filter(applied_controls=applied_control["id"])
                    .count()
                )
                if applied_control["status"] == "--":
                    response["none"].append(applied_control)
                else:
                    response[applied_control["status"].lower()].append(applied_control)

        return Response(response)

    @action(detail=True, name="Get compliance assessment (audit) CSV")
    def compliance_assessment_csv(self, request, pk):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_export.csv"'

        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, ComplianceAssessment
        )

        if UUID(pk) in viewable_objects:
            writer = csv.writer(response, delimiter=";")
            columns = [
                "ref_id",
                "description",
                "compliance_result",
                "progress",
                "score",
                "observations",
            ]
            writer.writerow(columns)

            for req in RequirementAssessment.objects.filter(compliance_assessment=pk):
                req_node = RequirementNode.objects.get(pk=req.requirement.id)
                req_text = (
                    req_node.get_description_translated
                    if req_node.description
                    else req_node.get_name_translated
                )
                row = [
                    req_node.ref_id,
                    req_text,
                ]
                if req_node.assessable:
                    row += [
                        req.result,
                        req.status,
                        req.score,
                        req.observation,
                    ]
                writer.writerow(row)

            return response
        else:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, name="Get action plan PDF")
    def action_plan_pdf(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, ComplianceAssessment
        )
        if UUID(pk) in object_ids_view:
            context = {
                "to_do": list(),
                "in_progress": list(),
                "on_hold": list(),
                "active": list(),
                "deprecated": list(),
                "--": list(),
            }
            color_map = {
                "to_do": "#FFF8F0",
                "in_progress": "#392F5A",
                "on_hold": "#F4D06F",
                "active": "#9DD9D2",
                "deprecated": "#ff8811",
                "--": "#e5e7eb",
            }
            status = AppliedControl.Status.choices
            compliance_assessment_object: ComplianceAssessment = self.get_object()
            requirement_assessments_objects = (
                compliance_assessment_object.get_requirement_assessments(
                    include_non_assessable=True
                )
            )
            applied_controls = (
                AppliedControl.objects.filter(
                    requirement_assessments__in=requirement_assessments_objects
                )
                .distinct()
                .order_by("eta")
            )
            for applied_control in applied_controls:
                context[applied_control.status].append(
                    applied_control
                ) if applied_control.status else context["no status"].append(
                    applied_control
                )
            data = {
                "status_text": status,
                "color_map": color_map,
                "context": context,
                "compliance_assessment": compliance_assessment_object,
            }
            html = render_to_string("core/action_plan_pdf.html", data)
            pdf_file = HTML(string=html).write_pdf()
            response = HttpResponse(pdf_file, content_type="application/pdf")
            return response
        else:
            return Response({"error": "Permission denied"})

    @action(
        detail=True,
        methods=["post"],
        name="Send compliance assessment by mail to authors",
    )
    def mailing(self, request, pk):
        instance = self.get_object()
        if EMAIL_HOST or EMAIL_HOST_RESCUE:
            for author in instance.authors.all():
                try:
                    author.mailing(
                        email_template_name="tprm/third_party_email.html",
                        subject=_(
                            "CISO Assistant: A questionnaire has been assigned to you"
                        ),
                        object="compliance-assessments",
                        object_id=instance.id,
                    )
                except Exception as primary_exception:
                    logger.error(
                        f"Failed to send email to {author}: {primary_exception}"
                    )
                    raise ValidationError(
                        {"error": ["An error occurred while sending the email"]}
                    )
            return Response({"results": "mail sent"})
        raise ValidationError({"warning": ["noMailerConfigured"]})

    def perform_create(self, serializer):
        """
        Create RequirementAssessment objects for the newly created ComplianceAssessment
        """
        baseline = serializer.validated_data.pop("baseline", None)
        create_applied_controls = serializer.validated_data.pop(
            "create_applied_controls_from_suggestions", False
        )
        instance: ComplianceAssessment = serializer.save()
        instance.create_requirement_assessments(baseline)
        if baseline and baseline.framework != instance.framework:
            mapping_set = RequirementMappingSet.objects.get(
                target_framework=serializer.validated_data["framework"],
                source_framework=baseline.framework,
            )
            for (
                requirement_assessment
            ) in instance.compute_requirement_assessments_results(
                mapping_set, baseline
            ):
                baseline_requirement_assessment = RequirementAssessment.objects.get(
                    id=requirement_assessment.mapping_inference[
                        "source_requirement_assessment"
                    ]["id"]
                )
                requirement_assessment.evidences.add(
                    *[ev.id for ev in baseline_requirement_assessment.evidences.all()]
                )
                requirement_assessment.applied_controls.add(
                    *[
                        ac.id
                        for ac in baseline_requirement_assessment.applied_controls.all()
                    ]
                )
                requirement_assessment.save()
        if create_applied_controls:
            for requirement_assessment in instance.requirement_assessments.all():
                requirement_assessment.create_applied_controls_from_suggestions()

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

    @method_decorator(cache_page(60 * SHORT_CACHE_TTL))
    @method_decorator(vary_on_cookie)
    @action(detail=True, methods=["get"])
    def global_score(self, request, pk):
        """Returns the global score of the compliance assessment"""
        compliance_assessment = self.get_object()
        return Response(
            {
                "score": compliance_assessment.get_global_score(),
                "max_score": compliance_assessment.max_score,
                "min_score": compliance_assessment.min_score,
                "scores_definition": get_referential_translation(
                    compliance_assessment.framework, "scores_definition", get_language()
                ),
            }
        )

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
        tree = get_sorted_requirement_nodes(
            RequirementNode.objects.filter(framework=_framework).all(),
            RequirementAssessment.objects.filter(
                compliance_assessment=self.get_object()
            ).all(),
            _framework.max_score,
        )
        implementation_groups = self.get_object().selected_implementation_groups
        return Response(
            filter_graph_by_implementation_groups(tree, implementation_groups)
        )

    @action(detail=True, methods=["get"])
    def requirements_list(self, request, pk):
        """Returns the list of requirement assessments for the different audit modes"""
        requirement_assessments_objects = self.get_object().get_requirement_assessments(
            include_non_assessable=True
        )
        requirements_objects = RequirementNode.objects.filter(
            framework=self.get_object().framework
        )
        requirement_assessments = RequirementAssessmentReadSerializer(
            requirement_assessments_objects, many=True
        ).data
        requirements = RequirementNodeReadSerializer(
            requirements_objects, many=True
        ).data
        requirements_list = {
            "requirements": requirements,
            "requirement_assessments": requirement_assessments,
        }
        return Response(requirements_list, status=status.HTTP_200_OK)

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

    @method_decorator(cache_page(60 * SHORT_CACHE_TTL))
    @method_decorator(vary_on_cookie)
    @action(detail=True, methods=["get"])
    def donut_data(self, request, pk):
        compliance_assessment = ComplianceAssessment.objects.get(id=pk)
        return Response(compliance_assessment.donut_render())

    @staticmethod
    @api_view(["POST"])
    @renderer_classes([JSONRenderer])
    def create_suggested_applied_controls(request, pk):
        compliance_assessment = ComplianceAssessment.objects.get(id=pk)
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_appliedcontrol"),
            folder=compliance_assessment.folder,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        requirement_assessments = compliance_assessment.requirement_assessments.all()
        for requirement_assessment in requirement_assessments:
            requirement_assessment.create_applied_controls_from_suggestions()
        return Response(status=status.HTTP_200_OK)


class RequirementAssessmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows requirement assessments to be viewed or edited.
    """

    model = RequirementAssessment
    filterset_fields = ["folder", "evidences", "compliance_assessment"]
    search_fields = ["name", "description"]

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        cache.clear()
        return response

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
                "id","folder","reference_control","type","status","effort","cost","name","description","eta","link","created_at","updated_at"
            ]
        } for mtg in measures]
        for i in range(len(measures)) :
            measures[i]["id"] = str(measures[i]["id"])
            measures[i]["folder"] = str(measures[i]["folder"].name)
            for key in ["created_at","updated_at","eta"] :
                measures[i][key] = str(measures[i][key])"""

        ranking_scores = {str(mtg.id): mtg.get_ranking_score() for mtg in measures}

        measures = [AppliedControlReadSerializer(mtg).data for mtg in measures]

        for i in range(len(measures)):
            measures[i]["ranking_score"] = ranking_scores[measures[i]["id"]]

        """
        The serializer of AppliedControl isn't applied automatically for this function
        """

        return Response({"results": measures})

    @action(detail=False, name="Get the secuity measures to review")
    def to_review(self, request):
        measures = measures_to_review(request.user)
        measures = [AppliedControlReadSerializer(mtg).data for mtg in measures]

        """
        The serializer of AppliedControl isn't applied automatically for this function
        """

        return Response({"results": measures})

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(RequirementAssessment.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get result choices")
    def result(self, request):
        return Response(dict(RequirementAssessment.Result.choices))

    @staticmethod
    @api_view(["POST"])
    @renderer_classes([JSONRenderer])
    def create_suggested_applied_controls(request, pk):
        requirement_assessment = RequirementAssessment.objects.get(id=pk)
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_appliedcontrol"),
            folder=requirement_assessment.folder,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        requirement_assessment.create_applied_controls_from_suggestions()
        return Response(status=status.HTTP_200_OK)


class RequirementMappingSetViewSet(BaseModelViewSet):
    model = RequirementMappingSet

    filterset_fields = ["target_framework", "source_framework"]

    @action(detail=True, methods=["get"], url_path="graph_data")
    def graph_data(self, request, pk=None):
        mapping_set_id = pk
        mapping_set = get_object_or_404(RequirementMappingSet, id=mapping_set_id)

        nodes = []
        links = []
        snodes_idx = dict()
        tnodes_idx = dict()
        categories = [
            {
                "name": mapping_set.source_framework.name,
            },
            {
                "name": mapping_set.target_framework.name,
            },
        ]
        N = 0
        for req in RequirementNode.objects.filter(
            framework=mapping_set.source_framework
        ).filter(assessable=True):
            nodes.append(
                {
                    "name": req.ref_id,
                    "category": 0,
                    "value": req.name if req.name else req.description,
                }
            )
            snodes_idx[req.ref_id] = N
            N += 1

        for req in RequirementNode.objects.filter(
            framework=mapping_set.target_framework
        ).filter(assessable=True):
            nodes.append(
                {
                    "name": req.ref_id,
                    "category": 1,
                    "value": req.name if req.name else req.description,
                }
            )
            tnodes_idx[req.ref_id] = N
            N += 1
        req_mappings = RequirementMapping.objects.filter(mapping_set=mapping_set_id)
        for item in req_mappings:
            if (
                item.source_requirement.assessable
                and item.target_requirement.assessable
            ):
                links.append(
                    {
                        "source": snodes_idx[item.source_requirement.ref_id],
                        "target": tnodes_idx[item.target_requirement.ref_id],
                        "value": item.coverage,
                    }
                )

        meta = {
            "display_name": f"{mapping_set.source_framework.name} ➜ {mapping_set.target_framework.name}"
        }

        return Response(
            {"nodes": nodes, "links": links, "categories": categories, "meta": meta}
        )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def get_csrf_token(request):
    """
    API endpoint that returns the CSRF token.
    """
    return Response({"csrfToken": csrf.get_token(request)})


def get_disk_usage():
    try:
        path = Path(settings.BASE_DIR) / "db"
        usage = shutil.disk_usage(path)
        return usage
    except PermissionError:
        logger.error(
            "Permission issue: cannot access the path to retrieve the disk_usage info"
        )
        return None
    except FileNotFoundError:
        logger.error(
            "Path issue: cannot access the path to retrieve the disk_usage info"
        )
        return None


@api_view(["GET"])
def get_build(request):
    """
    API endpoint that returns the build version of the application.
    """
    BUILD = settings.BUILD
    VERSION = settings.VERSION

    disk_info = get_disk_usage()

    if disk_info:
        total, used, free = disk_info
        disk_response = {
            "Disk space": f"{humanize.naturalsize(total)}",
            "Used": f"{humanize.naturalsize(used)} ({int((used/total)*100)} %)",
        }
    else:
        disk_response = {
            "Disk space": "Unable to retrieve disk usage",
        }

    return Response({"version": VERSION, "build": BUILD, **disk_response})


# NOTE: Important functions/classes from old views.py, to be reviewed


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

    implementation_groups = compliance_assessment.selected_implementation_groups
    graph = get_sorted_requirement_nodes(
        list(requirement_nodes),
        list(assessments),
        compliance_assessment.framework.max_score,
    )
    graph = filter_graph_by_implementation_groups(graph, implementation_groups)
    flattened_graph = flatten_dict(graph)

    requirement_nodes = requirement_nodes.filter(urn__in=flattened_graph.values())
    assessments = assessments.filter(requirement__urn__in=flattened_graph.values())

    node_per_urn = {r.urn: r for r in requirement_nodes}
    ancestors = {}
    for a in assessments:
        ancestors[a] = set()
        req = a.requirement
        while req:
            ancestors[a].add(req)
            p = req.parent_urn
            req = None if not (p) else node_per_urn[p]

    def generate_data_rec(requirement_node: RequirementNode):
        selected_evidences = []
        children_nodes = [
            req for req in requirement_nodes if req.parent_urn == requirement_node.urn
        ]

        node_data = {
            "requirement_node": requirement_node,
            "children": [],
            "assessments": None,
            "bar_graph": None,
            "direct_evidences": [],
            "applied_controls": [],
            "result": "",
            "status": "",
            "color_class": "",
        }

        node_data["bar_graph"] = True if children_nodes else False

        if requirement_node.assessable:
            assessment = RequirementAssessment.objects.filter(
                requirement__urn=requirement_node.urn,
                compliance_assessment=compliance_assessment,
            ).first()

            if assessment:
                node_data["assessments"] = assessment
                node_data["result"] = assessment.get_result_display()
                node_data["status"] = assessment.get_status_display()
                node_data["result_color_class"] = color_css_class(assessment.result)
                node_data["status_color_class"] = color_css_class(assessment.status)
                direct_evidences = assessment.evidences.all()
                if direct_evidences:
                    selected_evidences += direct_evidences
                    node_data["direct_evidences"] = direct_evidences

                measures = assessment.applied_controls.all()
                if measures:
                    applied_controls = []
                    for measure in measures:
                        evidences = measure.evidences.all()
                        applied_controls.append(
                            {
                                "measure": measure,
                                "evidences": evidences,
                            }
                        )
                        selected_evidences += evidences
                    node_data["applied_controls"] = applied_controls

        for child_node in children_nodes:
            child_data, child_evidences = generate_data_rec(child_node)
            node_data["children"].append(child_data)
            selected_evidences += child_evidences

        return node_data, selected_evidences

    top_level_nodes = [req for req in requirement_nodes if not req.parent_urn]
    update_translations_in_object(top_level_nodes)
    top_level_nodes_data = []
    for requirement_node in top_level_nodes:
        node_data, node_evidences = generate_data_rec(requirement_node)
        top_level_nodes_data.append(node_data)
        selected_evidences += node_evidences

    data = {
        "compliance_assessment": compliance_assessment,
        "top_level_nodes": top_level_nodes_data,
        "assessments": assessments,
        "ancestors": ancestors,
    }

    return render_to_string("core/audit_report.html", data), list(
        set(selected_evidences)
    )


def export_mp_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="MP.csv"'

    writer = csv.writer(response, delimiter=";")
    columns = [
        "measure_id",
        "measure_name",
        "measure_desc",
        "category",
        "csf_function",
        "reference_control",
        "eta",
        "priority",
        "effort",
        "cost",
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
            mtg.csf_function,
            mtg.priority,
            mtg.reference_control,
            mtg.eta,
            mtg.effort,
            mtg.cost,
            mtg.link,
            mtg.status,
        ]
        writer.writerow(row)

    return response
