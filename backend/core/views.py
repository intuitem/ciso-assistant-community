import csv
import json
import mimetypes
import re
import os
import uuid
import zipfile
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Tuple
import time
from django.db.models import (
    F,
    Count,
    Q,
    ExpressionWrapper,
    FloatField,
    Value,
)
from django.db.models.functions import Greatest, Coalesce


from collections import defaultdict
import pytz
from uuid import UUID
from itertools import chain, cycle
import django_filters as df
from ciso_assistant.settings import (
    EMAIL_HOST,
    EMAIL_HOST_RESCUE,
)

import shutil
from pathlib import Path
import humanize

from wsgiref.util import FileWrapper

import pandas as pd
import io

import random
from django.db.models.functions import Lower

from docxtpl import DocxTemplate
from .generators import gen_audit_context

from django.utils import timezone
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache


from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.forms import ValidationError
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.middleware import csrf
from django.template.loader import render_to_string
from django.utils.functional import Promise
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from iam.models import Folder, RoleAssignment, UserGroup
from rest_framework import filters, generics, permissions, status, viewsets
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
    renderer_classes,
)
from rest_framework.parsers import (
    FileUploadParser,
)
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.utils.serializer_helpers import ReturnDict
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied


from weasyprint import HTML

from core.helpers import *
from core.models import (
    AppliedControl,
    ComplianceAssessment,
    RequirementMappingSet,
    RiskAssessment,
    AssetClass,
)
from core.serializers import ComplianceAssessmentReadSerializer
from core.utils import (
    RoleCodename,
    UserGroupCodename,
    compare_schema_versions,
    _generate_occurrences,
    _create_task_dict,
)
from dateutil import relativedelta as rd

from ebios_rm.models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    StrategicScenario,
    Stakeholder,
    AttackPath,
)

from tprm.models import Entity

from .models import *
from .serializers import *

from .models import Severity

from serdes.utils import (
    get_domain_export_objects,
    import_export_serializer_class,
    topological_sort,
    build_dependency_graph,
    get_self_referencing_field,
    sort_objects_by_self_reference,
)
from serdes.serializers import ExportSerializer

import structlog

logger = structlog.get_logger(__name__)

User = get_user_model()

SHORT_CACHE_TTL = 2  # mn
MED_CACHE_TTL = 5  # mn
LONG_CACHE_TTL = 60  # mn

SETTINGS_MODULE = __import__(os.environ.get("DJANGO_SETTINGS_MODULE"))
MODULE_PATHS = SETTINGS_MODULE.settings.MODULE_PATHS


class GenericFilterSet(df.FilterSet):
    class Meta:
        model = None  # This will be set dynamically via filterset_factory.
        fields = "__all__"
        filter_overrides = {
            models.CharField: {
                "filter_class": df.MultipleChoiceFilter,
                "extra": lambda f: {
                    "lookup_expr": "icontains",
                    # If your model field defines choices, they will be used:
                    "choices": f.choices if hasattr(f, "choices") else None,
                },
            },
        }


class BaseModelViewSet(viewsets.ModelViewSet):
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering = ["created_at"]
    ordering_fields = "__all__"
    search_fields = ["name", "description"]
    filterset_fields = []
    model = None

    serializers_module = "core.serializers"

    # @property
    # def filterset_class(self):
    #     # If you have defined filterset_fields, build the FilterSet on the fly.
    #     if self.filterset_fields:
    #         return filterset_factory(
    #             model=self.model,
    #             filterset=GenericFilterSet,
    #             fields=self.filterset_fields,
    #         )
    #     return None

    def get_queryset(self) -> models.query.QuerySet:
        """the scope_folder_id query_param allows scoping the objects to retrieve"""
        if not self.model:
            return None
        object_ids_view = None
        if self.request.method == "GET":
            if q := re.match(
                r"/api/[\w-]+/([\w-]+/)?([0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}(,[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})+)",
                self.request.path,
            ):
                """"get_queryset is called by Django even for an individual object via get_object
                https://stackoverflow.com/questions/74048193/why-does-a-retrieve-request-end-up-calling-get-queryset"""
                id = UUID(q.group(1))
                if RoleAssignment.is_object_readable(self.request.user, self.model, id):
                    object_ids_view = [id]
        if not object_ids_view:
            scope_folder_id = self.request.query_params.get("scope_folder_id")
            scope_folder = (
                get_object_or_404(Folder, id=scope_folder_id)
                if scope_folder_id
                else Folder.get_root_folder()
            )
            object_ids_view = RoleAssignment.get_accessible_object_ids(
                scope_folder, self.request.user, self.model
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

    def create(self, request: Request, *args, **kwargs) -> Response:
        self._process_request_data(request)
        if request.data.get("filtering_labels"):
            request.data["filtering_labels"] = self._process_labels(
                request.data["filtering_labels"]
            )
        return super().create(request, *args, **kwargs)

    def update(self, request: Request, *args, **kwargs) -> Response:
        self._process_request_data(request)
        if request.data.get("filtering_labels"):
            request.data["filtering_labels"] = self._process_labels(
                request.data["filtering_labels"]
            )
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


class PerimeterFilter(df.FilterSet):
    folder = df.ModelMultipleChoiceFilter(
        queryset=Folder.objects.all(),
    )
    lc_status = df.MultipleChoiceFilter(
        choices=Perimeter.PRJ_LC_STATUS, lookup_expr="icontains"
    )

    class Meta:
        model = Perimeter
        fields = ["folder", "lc_status"]


class PerimeterViewSet(BaseModelViewSet):
    """
    API endpoint that allows perimeters to be viewed or edited.
    """

    model = Perimeter
    filterset_class = PerimeterFilter
    search_fields = ["name", "ref_id", "description"]

    @action(detail=False, name="Get status choices")
    def lc_status(self, request):
        return Response(dict(Perimeter.PRJ_LC_STATUS))

    @action(detail=False, methods=["get"])
    def names(self, request):
        uuid_list = request.query_params.getlist("id[]", [])
        queryset = Perimeter.objects.filter(id__in=uuid_list)

        return Response({str(perimeter.id): perimeter.name for perimeter in queryset})

    @action(detail=False, methods=["get"])
    def quality_check(self, request):
        """
        Returns the quality check of the perimeters
        """
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(), user=request.user, object_type=Perimeter
        )
        perimeters = Perimeter.objects.filter(id__in=viewable_objects)
        res = {
            str(p.id): {
                "perimeter": PerimeterReadSerializer(p).data,
                "compliance_assessments": {"objects": {}},
                "risk_assessments": {"objects": {}},
            }
            for p in perimeters
        }
        for compliance_assessment in ComplianceAssessment.objects.filter(
            perimeter__in=perimeters
        ):
            res[str(compliance_assessment.perimeter.id)]["compliance_assessments"][
                "objects"
            ][str(compliance_assessment.id)] = {
                "object": ComplianceAssessmentReadSerializer(
                    compliance_assessment
                ).data,
                "quality_check": compliance_assessment.quality_check(),
            }
        for risk_assessment in RiskAssessment.objects.filter(perimeter__in=perimeters):
            res[str(risk_assessment.perimeter.id)]["risk_assessments"]["objects"][
                str(risk_assessment.id)
            ] = {
                "object": RiskAssessmentReadSerializer(risk_assessment).data,
                "quality_check": risk_assessment.quality_check(),
            }
        return Response({"results": res})

    @action(detail=True, methods=["get"], url_path="quality_check")
    def quality_check_detail(self, request, pk):
        """
        Returns the quality check of the perimeter
        """
        (viewable_objects, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(), user=request.user, object_type=Perimeter
        )
        if UUID(pk) in viewable_objects:
            perimeter = self.get_object()
            res = {
                "perimeter": PerimeterReadSerializer(perimeter).data,
                "compliance_assessments": {"objects": {}},
                "risk_assessments": {"objects": {}},
            }
            for compliance_assessment in ComplianceAssessment.objects.filter(
                perimeter=perimeter
            ):
                res["compliance_assessments"]["objects"][
                    str(compliance_assessment.id)
                ] = {
                    "object": ComplianceAssessmentReadSerializer(
                        compliance_assessment
                    ).data,
                    "quality_check": compliance_assessment.quality_check(),
                }
            for risk_assessment in RiskAssessment.objects.filter(perimeter=perimeter):
                res["risk_assessments"]["objects"][str(risk_assessment.id)] = {
                    "object": RiskAssessmentReadSerializer(risk_assessment).data,
                    "quality_check": risk_assessment.quality_check(),
                }
            return Response(res)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    @action(detail=False, methods=["get"])
    def ids(self, request):
        my_map = dict()

        (viewable_items, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Perimeter,
        )
        for item in Perimeter.objects.filter(id__in=viewable_items):
            if my_map.get(item.folder.name) is None:
                my_map[item.folder.name] = {}
            my_map[item.folder.name].update({item.name: item.id})

        return Response(my_map)


class ThreatViewSet(BaseModelViewSet):
    """
    API endpoint that allows threats to be viewed or edited.
    """

    model = Threat
    filterset_fields = ["folder", "provider", "risk_scenarios", "filtering_labels"]
    search_fields = ["name", "provider", "description"]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        providers = set(
            Threat.objects.filter(provider__isnull=False).values_list(
                "provider", flat=True
            )
        )
        return Response({p: p for p in providers})

    @action(detail=False, name="Get threats count")
    def threats_count(self, request):
        folder_id = request.query_params.get("folder", None)
        return Response({"results": threats_count_per_name(request.user, folder_id)})

    @action(detail=False, methods=["get"])
    def ids(self, request):
        my_map = dict()

        (viewable_items, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Threat,
        )
        for item in Threat.objects.filter(id__in=viewable_items):
            if my_map.get(item.folder.name) is None:
                my_map[item.folder.name] = {}
            my_map[item.folder.name].update({item.name: item.id})
        return Response(my_map)


class AssetFilter(df.FilterSet):
    exclude_childrens = df.ModelChoiceFilter(
        queryset=Asset.objects.all(),
        method="filter_exclude_childrens",
        label="Exclude childrens",
    )

    def filter_exclude_childrens(self, queryset, name, value):
        print(value.get_descendants())
        descendants = value.get_descendants()
        return queryset.exclude(id__in=[descendant.id for descendant in descendants])

    class Meta:
        model = Asset
        fields = [
            "folder",
            "type",
            "parent_assets",
            "exclude_childrens",
            "ebios_rm_studies",
            "risk_scenarios",
            "security_exceptions",
            "applied_controls",
            "filtering_labels",
            "asset_class",
        ]


class AssetViewSet(BaseModelViewSet):
    """
    API endpoint that allows assets to be viewed or edited.
    """

    model = Asset
    filterset_class = AssetFilter
    search_fields = ["name", "description", "ref_id"]

    def _perform_write(self, serializer):
        type = serializer.validated_data.get("type")
        if type == Asset.Type.PRIMARY:
            serializer.validated_data["parent_assets"] = []
        serializer.save()

    def perform_create(self, serializer):
        return self._perform_write(serializer)

    def perform_update(self, serializer):
        return self._perform_write(serializer)

    @action(detail=False, name="Get type choices")
    def type(self, request):
        return Response(dict(Asset.Type.choices))

    @action(detail=False, name="Get asset class choices")
    def asset_class(self, request):
        # this is for filters
        return Response(
            [{"id": ac.id, "name": ac.full_path} for ac in AssetClass.objects.all()]
        )

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
            N += 1
        for asset in Asset.objects.filter(id__in=viewable_assets):
            for relationship in asset.parent_assets.all():
                links.append(
                    {
                        "source": nodes_idx[relationship.name],
                        "target": nodes_idx[asset.name],
                        "value": "supported by",
                    }
                )
        meta = {"display_name": "Assets Explorer"}

        return Response(
            {"nodes": nodes, "links": links, "categories": categories, "meta": meta}
        )

    @action(detail=False, methods=["get"])
    def ids(self, request):
        my_map = dict()

        (viewable_items, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Asset,
        )
        for item in Asset.objects.filter(id__in=viewable_items):
            if my_map.get(item.folder.name) is None:
                my_map[item.folder.name] = {}
            my_map[item.folder.name].update({item.name: item.id})
        return Response(my_map)

    @action(detail=False, name="Get security objectives")
    def security_objectives(self, request):
        return Response({"results": Asset.DEFAULT_SECURITY_OBJECTIVES})

    @action(detail=False, name="Get disaster recovery objectives")
    def disaster_recovery_objectives(self, request):
        return Response({"results": Asset.DEFAULT_DISASTER_RECOVERY_OBJECTIVES})

    @action(detail=False, name="Export assets as CSV")
    def export_csv(self, request):
        try:
            (viewable_assets_ids, _, _) = RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), request.user, Asset
            )
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="assets_export.csv"'

            writer = csv.writer(response, delimiter=";")
            columns = [
                "internal_id",
                "name",
                "description",
                "type",
                "security_objectives",
                "disaster_recovery_objectives",
                "link",
                "owners",
                "parent_assets",
                "labels",
            ]
            writer.writerow(columns)

            for asset in Asset.objects.filter(id__in=viewable_assets_ids).iterator():
                row = [
                    asset.id,
                    asset.name,
                    asset.description,
                    asset.type,
                    ",".join(
                        [i["str"] for i in asset.get_security_objectives_display()]
                    ),
                    ",".join(
                        [
                            i["str"]
                            for i in asset.get_disaster_recovery_objectives_display()
                        ]
                    ),
                    asset.reference_link,
                    ",".join([o.email for o in asset.owner.all()]),
                    ",".join([o.name for o in asset.parent_assets.all()]),
                    ",".join([o.label for o in asset.filtering_labels.all()]),
                ]
                writer.writerow(row)

            return response

        except Exception as e:
            logger.error(f"Error exporting assets to CSV: {str(e)}")
            return HttpResponse(
                status=500, content="An error occurred while generating the CSV export."
            )


class AssetClassViewSet(BaseModelViewSet):
    model = AssetClass
    filterset_fields = ["parent"]

    ordering = ["parent", "name"]
    search_fields = ["name", "description"]

    @action(detail=False, name="Get Asset Class Tree")
    def tree(self, request):
        return Response(AssetClass.build_tree())


class ReferenceControlViewSet(BaseModelViewSet):
    """
    API endpoint that allows reference controls to be viewed or edited.
    """

    model = ReferenceControl
    filterset_fields = [
        "folder",
        "category",
        "csf_function",
        "provider",
        "findings",
        "filtering_labels",
    ]
    search_fields = ["name", "description", "provider"]

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        providers = set(
            ReferenceControl.objects.filter(provider__isnull=False).values_list(
                "provider", flat=True
            )
        )
        return Response({p: p for p in providers})

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
    filterset_fields = ["folder", "is_enabled", "provider"]

    @action(detail=False)  # Set a name there
    def colors(self, request):
        return Response({"results": get_risk_color_ordered_list(request.user)})

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        providers = set(
            RiskMatrix.objects.filter(provider__isnull=False).values_list(
                "provider", flat=True
            )
        )
        return Response({p: p for p in providers})

    @action(detail=False, name="Get risk level choices")
    def risk(self, request):
        viewable_matrices: list[RiskMatrix] = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskMatrix
        )[0]
        undefined = {-1: "--"}
        options = []
        for matrix in RiskMatrix.objects.filter(id__in=viewable_matrices):
            _choices = {
                i: name
                for i, name in enumerate(
                    x["name"] for x in matrix.json_definition["risk"]
                )
            }
            choices = undefined | _choices
            options = options | choices.items()
        return Response(
            [{k: v for k, v in zip(("value", "label"), o)} for o in options]
        )

    @action(detail=False, name="Get impact choices")
    def impact(self, request):
        viewable_matrices: list[RiskMatrix] = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskMatrix
        )[0]
        impacts = [
            m.impact for m in RiskMatrix.objects.filter(id__in=viewable_matrices)
        ]
        return Response(chain.from_iterable(impacts))

    @action(detail=False, name="Get probability choices")
    def probability(self, request):
        viewable_matrices: list[RiskMatrix] = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskMatrix
        )[0]
        undefined = {-1: "--"}
        options = []
        for matrix in RiskMatrix.objects.filter(id__in=viewable_matrices):
            _choices = {
                i: name
                for i, name in enumerate(
                    x["name"] for x in matrix.json_definition["probability"]
                )
            }
            choices = undefined | _choices
            options = options | choices.items()
        return Response(
            [{k: v for k, v in zip(("value", "label"), o)} for o in options]
        )

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

    @action(detail=False, methods=["get"])
    def ids(self, request):
        my_map = dict()

        (viewable_items, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=RiskMatrix,
        )
        for item in RiskMatrix.objects.filter(id__in=viewable_items):
            if my_map.get(item.folder.name) is None:
                my_map[item.folder.name] = {}
            my_map[item.folder.name].update({item.name: item.id})

        return Response(my_map)


class VulnerabilityViewSet(BaseModelViewSet):
    """
    API endpoint that allows vulnerabilities to be viewed or edited.
    """

    model = Vulnerability
    filterset_fields = [
        "folder",
        "status",
        "severity",
        "risk_scenarios",
        "applied_controls",
        "security_exceptions",
        "filtering_labels",
        "findings",
    ]
    search_fields = ["name", "description", "ref_id"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(Vulnerability.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get severity choices")
    def severity(self, request):
        return Response(dict(Severity.choices))


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
        "perimeter",
        "folder",
        "authors",
        "risk_matrix",
        "status",
        "ebios_rm_study",
    ]

    def perform_create(self, serializer):
        instance: RiskAssessment = serializer.save()
        if instance.ebios_rm_study:
            instance.risk_matrix = instance.ebios_rm_study.risk_matrix
            ebios_rm_study = EbiosRMStudy.objects.get(id=instance.ebios_rm_study.id)
            for operational_scenario in [
                operational_scenario
                for operational_scenario in ebios_rm_study.operational_scenarios.all()
                if operational_scenario.is_selected
            ]:
                risk_scenario = RiskScenario.objects.create(
                    risk_assessment=instance,
                    name=operational_scenario.name,
                    ref_id=operational_scenario.ref_id
                    if operational_scenario.ref_id
                    else RiskScenario.get_default_ref_id(instance),
                    description="\n\n".join(
                        filter(
                            None,
                            [
                                operational_scenario.attack_path.strategic_scenario.description,
                                operational_scenario.attack_path.description,
                                operational_scenario.operating_modes_description,
                            ],
                        )
                    ),
                    current_proba=operational_scenario.likelihood,
                    current_impact=operational_scenario.gravity,
                )
                risk_scenario.assets.set(operational_scenario.get_assets())
                risk_scenario.threats.set(operational_scenario.threats.all())
                risk_scenario.existing_applied_controls.set(
                    operational_scenario.get_applied_controls()
                )
                risk_scenario.save()
        instance.save()
        return super().perform_create(serializer)

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
            return Response(status=status.HTTP_403_FORBIDDEN)

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
            return Response(status=status.HTTP_403_FORBIDDEN)

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
                "control_impact",
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
                    mtg.control_impact,
                    mtg.priority,
                    mtg.cost,
                    mtg.link,
                    mtg.status,
                ]
                writer.writerow(row)

            return response
        else:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

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
                "assets",
                "threats",
                "name",
                "description",
                "existing_controls",
                "current_impact",
                "current_proba",
                "current_risk",
                "additional_controls",
                "residual_impact",
                "residual_proba",
                "residual_risk",
                "treatment",
            ]
            writer.writerow(columns)

            for scenario in risk_assessment.risk_scenarios.all().order_by("ref_id"):
                additional_controls = ",".join(
                    [m.name for m in scenario.applied_controls.all()]
                )
                existing_controls = ",".join(
                    [m.name for m in scenario.existing_applied_controls.all()]
                )

                threats = ",".join([t.name for t in scenario.threats.all()])
                assets = ",".join([t.name for t in scenario.assets.all()])

                row = [
                    scenario.ref_id,
                    assets,
                    threats,
                    scenario.name,
                    scenario.description,
                    existing_controls,
                    scenario.get_current_impact()["name"],
                    scenario.get_current_proba()["name"],
                    scenario.get_current_risk()["name"],
                    additional_controls,
                    scenario.get_residual_impact()["name"],
                    scenario.get_residual_proba()["name"],
                    scenario.get_residual_risk()["name"],
                    scenario.treatment,
                ]
                writer.writerow(row)

            return response
        else:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, name="Get risk assessment PDF")
    def risk_assessment_pdf(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, RiskAssessment
        )
        if UUID(pk) in object_ids_view:
            risk_assessment = self.get_object()
            context = RiskScenario.objects.filter(
                risk_assessment=risk_assessment
            ).order_by("ref_id")
            general_settings = GlobalSettings.objects.filter(name="general").first()
            swap_axes = general_settings.value.get("risk_matrix_swap_axes", False)
            flip_vertical = general_settings.value.get(
                "risk_matrix_flip_vertical", False
            )
            matrix_settings = {
                "swap_axes": "_swapaxes" if swap_axes else "",
                "flip_vertical": "_vflip" if flip_vertical else "",
            }
            data = {
                "context": context,
                "risk_assessment": risk_assessment,
                "ri_clusters": build_scenario_clusters(risk_assessment),
                "risk_matrix": risk_assessment.risk_matrix,
                "settings": matrix_settings,
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
                perimeter=Perimeter.objects.get(id=data["perimeter"]),
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
                    ref_id=scenario.ref_id,
                )

                for field in ["applied_controls", "threats", "assets"]:
                    duplicate_related_objects(
                        scenario,
                        duplicate_scenario,
                        duplicate_risk_assessment.folder,
                        field,
                    )

                if duplicate_risk_assessment.folder in [risk_assessment.folder] + [
                    folder for folder in risk_assessment.folder.get_sub_folders()
                ]:
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


class AppliedControlFilterSet(df.FilterSet):
    todo = df.BooleanFilter(method="filter_todo")
    to_review = df.BooleanFilter(method="filter_to_review")
    compliance_assessments = df.ModelMultipleChoiceFilter(
        method="filter_compliance_assessments",
        queryset=ComplianceAssessment.objects.all(),
    )
    risk_assessments = df.ModelMultipleChoiceFilter(
        method="filter_risk_assessments",
        queryset=RiskAssessment.objects.all(),
    )
    findings_assessments = df.ModelMultipleChoiceFilter(
        method="filter_findings_assessments",
        queryset=FindingsAssessment.objects.all(),
    )
    status = df.MultipleChoiceFilter(
        choices=AppliedControl.Status.choices, lookup_expr="icontains"
    )

    def filter_findings_assessments(self, queryset, name, value):
        if value:
            findings_assessments = FindingsAssessment.objects.filter(
                id__in=[x.id for x in value]
            )
            if len(findings_assessments) == 0:
                return queryset
            findings = chain.from_iterable(
                [fa.findings.all() for fa in findings_assessments]
            )
            return queryset.filter(findings__in=findings).distinct()
        return queryset

    def filter_risk_assessments(self, queryset, name, value):
        if value:
            risk_assessments = RiskAssessment.objects.filter(
                id__in=[x.id for x in value]
            )
            if len(risk_assessments) == 0:
                return queryset
            risk_scenarios = chain.from_iterable(
                [ra.risk_scenarios.all() for ra in risk_assessments]
            )
            return queryset.filter(risk_scenarios__in=risk_scenarios).distinct()
        return queryset

    def filter_compliance_assessments(self, queryset, name, value):
        if value:
            compliance_assessments = ComplianceAssessment.objects.filter(
                id__in=[x.id for x in value]
            )
            if len(compliance_assessments) == 0:
                return queryset
            requirement_assessments = chain.from_iterable(
                [ca.requirement_assessments.all() for ca in compliance_assessments]
            )
            return queryset.filter(
                requirement_assessments__in=requirement_assessments
            ).distinct()
        return queryset

    def filter_todo(self, queryset, name, value):
        if value:
            return (
                queryset.filter(eta__lte=date.today() + timedelta(days=30))
                .exclude(status="active")
                .order_by("eta")
            )

        return queryset

    def filter_to_review(self, queryset, name, value):
        if value:
            return queryset.filter(
                expiry_date__lte=date.today() + timedelta(days=30)
            ).order_by("expiry_date")
        return queryset

    class Meta:
        model = AppliedControl
        fields = {
            "folder": ["exact"],
            "category": ["exact"],
            "csf_function": ["exact"],
            "priority": ["exact"],
            "reference_control": ["exact"],
            "effort": ["exact"],
            "control_impact": ["exact"],
            "cost": ["exact"],
            "filtering_labels": ["exact"],
            "risk_scenarios": ["exact"],
            "risk_scenarios_e": ["exact"],
            "requirement_assessments": ["exact"],
            "evidences": ["exact"],
            "assets": ["exact"],
            "stakeholders": ["exact"],
            "progress_field": ["exact"],
            "security_exceptions": ["exact"],
            "owner": ["exact"],
            "findings": ["exact"],
            "eta": ["exact", "lte", "gte", "lt", "gt", "month", "year"],
            "ref_id": ["exact"],
        }


class AppliedControlViewSet(BaseModelViewSet):
    """
    API endpoint that allows applied controls to be viewed or edited.
    """

    model = AppliedControl
    filterset_class = AppliedControlFilterSet
    search_fields = ["name", "description", "ref_id"]

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

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get impact choices")
    def control_impact(self, request):
        return Response(dict(AppliedControl.IMPACT))

    @action(detail=False, name="Get all applied controls owners")
    def owner(self, request):
        return Response(
            UserReadSerializer(
                User.objects.filter(applied_controls__isnull=False).distinct(),
                many=True,
            ).data
        )

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
            "priority",
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
                control.priority,
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

    @action(detail=False, name="Get priority chart data")
    def priority_chart_data(self, request):
        qs = AppliedControl.objects.exclude(status="active")

        data = {
            "--": [],
            "to_do": [],
            "in_progress": [],
            "on_hold": [],
            "deprecated": [],
        }
        angle_offsets = {"4": 0, "3": 90, "1": 180, "2": 270}
        status_offset = {
            "--": 4,
            "to_do": 12,
            "in_progress": 20,
            "on_hold": 28,
            "deprecated": 36,
        }

        not_displayed_cnt = 0

        p_dict = qs.aggregate(
            p1=Count("priority", filter=Q(priority=1)),
            p2=Count("priority", filter=Q(priority=2)),
            p3=Count("priority", filter=Q(priority=3)),
            p4=Count("priority", filter=Q(priority=4)),
        )
        for ac in qs:
            if ac.priority:
                if ac.eta:
                    days_countdown = min(100, ac.days_until_eta)
                    # how many days until the ETA
                else:
                    days_countdown = 100
                impact_factor = 5 + ac.links_count

                # angle = angle_offsets[str(ac.priority)]+ (next(offsets) % 80) + random.randint(1,4)
                angle = (
                    angle_offsets[str(ac.priority)]
                    + status_offset[ac.status]
                    + random.randint(1, 40)
                )
                # angle = angle_offsets[str(ac.priority)] + next(offsets)

                vector = [
                    days_countdown,
                    angle,
                    impact_factor,
                    f"[{ac.priority}] {str(ac)}",
                    ac.status,
                    ac.id,
                ]
                if ac.status:
                    data[ac.status].append(vector)
                else:
                    data["unclassified"].append(vector)
            else:
                print("priority unset - add it to triage lot")
                not_displayed_cnt += 1

        data["not_displayed"] = not_displayed_cnt
        data["priority_cnt"] = p_dict

        return Response(data)

    @action(detail=False, methods=["get"])
    def get_gantt_data(self, request):
        def format_date(input):
            return datetime.strftime(input, "%Y-%m-%d")

        entries = []
        (viewable_controls_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, AppliedControl
        )

        applied_controls = AppliedControl.objects.filter(
            id__in=viewable_controls_ids
        ).select_related("folder")

        for ac in applied_controls:
            if ac.eta:
                endDate = format_date(ac.eta)
                startDate = format_date(ac.start_date) if ac.start_date else endDate
                if ac.start_date:
                    startDate = format_date(ac.start_date)
                else:
                    startDate = format_date(ac.eta - timedelta(days=1))
                entries.append(
                    {
                        "id": ac.id,
                        "start": startDate,
                        "end": endDate,
                        "name": ac.name,
                        "progress": ac.progress_field,
                        "description": ac.description
                        if ac.description
                        else "(no description)",
                        "domain": ac.folder.name,
                    }
                )
        return Response(entries)

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

    @action(
        detail=True,
        name="Duplicate applied control",
        methods=["post"],
        serializer_class=AppliedControlDuplicateSerializer,
    )
    def duplicate(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, AppliedControl
        )
        if UUID(pk) not in object_ids_view:
            return Response(
                {"results": "applied control duplicated"},
                status=status.HTTP_404_NOT_FOUND,
            )

        applied_control = self.get_object()
        data = request.data
        new_folder = Folder.objects.get(id=data["folder"])
        duplicate_applied_control = AppliedControl.objects.create(
            reference_control=applied_control.reference_control,
            name=data["name"],
            description=data["description"],
            folder=new_folder,
            ref_id=applied_control.ref_id,
            category=applied_control.category,
            csf_function=applied_control.csf_function,
            priority=applied_control.priority,
            status=applied_control.status,
            start_date=applied_control.start_date,
            eta=applied_control.eta,
            expiry_date=applied_control.expiry_date,
            link=applied_control.link,
            effort=applied_control.effort,
            cost=applied_control.cost,
            progress_field=applied_control.progress_field,
        )
        duplicate_applied_control.owner.set(applied_control.owner.all())
        if data["duplicate_evidences"]:
            duplicate_related_objects(
                applied_control, duplicate_applied_control, new_folder, "evidences"
            )
            duplicate_applied_control.save()

        return Response(
            {"results": AppliedControlReadSerializer(duplicate_applied_control).data}
        )

    @action(detail=False, methods=["get"])
    def ids(self, request):
        my_map = dict()

        (viewable_items, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=AppliedControl,
        )
        for item in AppliedControl.objects.filter(id__in=viewable_items):
            if my_map.get(item.folder.name) is None:
                my_map[item.folder.name] = {}
            my_map[item.folder.name].update({item.name: item.id})

        return Response(my_map)

    @action(detail=False, name="Generate data for applied controls impact graph")
    def impact_graph(self, request):
        (viewable_controls_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, AppliedControl
        )
        csf_functions_map = dict()
        categories = [{"name": "--"}]
        for i, option in enumerate(ReferenceControl.CSF_FUNCTION, 1):
            csf_functions_map[option[0]] = i
            categories.append({"name": option[1]})
        categories.append({"name": "requirements"})  # 7
        categories.append({"name": "scenarios"})  # 9
        categories.append({"name": "audits"})  # 8
        categories.append({"name": "risk assessments"})

        nodes = list()
        links = list()
        indexes = dict()
        idx_cnt = 0
        for ac in AppliedControl.objects.filter(id__in=viewable_controls_ids):
            nodes.append(
                {
                    "name": ac.name,
                    "value": ac.name,
                    "category": csf_functions_map.get(ac.csf_function, 0),
                }
            )
            indexes[ac.id] = idx_cnt
            idx_cnt += 1
            # attached requirement_assessments
            for req in RequirementAssessment.objects.filter(applied_controls__id=ac.id):
                nodes.append(
                    {
                        "name": req.requirement.ref_id,
                        "value": req.requirement.description,
                        "category": 7,
                        "symbol": "triangle",
                    }
                )
                indexes[req.id] = (
                    idx_cnt  # not good - even if the probability of collision is low
                )
                idx_cnt += 1

                audit = req.compliance_assessment
                if indexes.get(audit.id) is None:
                    nodes.append(
                        {
                            "name": audit.name,
                            "value": audit.framework.name,
                            "category": 9,
                            "symbol": "rect",
                        }
                    )
                    indexes[audit.id] = idx_cnt
                    idx_cnt += 1
                links.append({"source": indexes[audit.id], "target": indexes[req.id]})

                links.append({"source": indexes[ac.id], "target": indexes[req.id]})
            for sc in RiskScenario.objects.filter(applied_controls__id=ac.id):
                nodes.append(
                    {
                        "name": sc.ref_id,
                        "value": sc.name,
                        "category": 8,
                        "symbol": "diamond",
                    }
                )
                indexes[sc.id] = idx_cnt
                idx_cnt += 1

                ra = sc.risk_assessment
                if indexes.get(ra.id) is None:
                    nodes.append(
                        {
                            "name": ra.name,
                            "value": ra.name,
                            "category": 10,
                            "symbol": "rect",
                        }
                    )
                    indexes[ra.id] = idx_cnt
                    idx_cnt += 1
                links.append({"source": indexes[ra.id], "target": indexes[sc.id]})

                links.append({"source": indexes[ac.id], "target": indexes[sc.id]})

        return Response({"nodes": nodes, "categories": categories, "links": links})


class ComplianceAssessmentActionPlanList(generics.ListAPIView):
    filterset_fields = {
        "folder": ["exact"],
        "status": ["exact"],
        "category": ["exact"],
        "csf_function": ["exact"],
        "priority": ["exact"],
        "reference_control": ["exact"],
        "effort": ["exact"],
        "control_impact": ["exact"],
        "cost": ["exact"],
        "filtering_labels": ["exact"],
        "risk_scenarios": ["exact"],
        "risk_scenarios_e": ["exact"],
        "requirement_assessments": ["exact"],
        "evidences": ["exact"],
        "assets": ["exact"],
        "stakeholders": ["exact"],
        "progress_field": ["exact"],
        "security_exceptions": ["exact"],
        "owner": ["exact"],
        "findings": ["exact"],
        "eta": ["exact", "lte", "gte", "lt", "gt"],
    }

    serializer_class = ComplianceAssessmentActionPlanSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering_fields = "__all__"
    ordering = ["eta"]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"pk": self.kwargs["pk"]})
        return context

    def get_queryset(self):
        compliance_assessment: ComplianceAssessment = ComplianceAssessment.objects.get(
            id=self.kwargs["pk"]
        )
        requirement_assessments = compliance_assessment.get_requirement_assessments(
            include_non_assessable=True
        )
        return AppliedControl.objects.filter(
            requirement_assessments__in=requirement_assessments
        ).distinct()


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
    search_fields = ["name", "description", "ref_id"]

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
        "risk_assessment__perimeter",
        "risk_assessment__perimeter__folder",
        "current_impact",
        "current_proba",
        "current_level",
        "residual_impact",
        "residual_proba",
        "residual_level",
        "treatment",
        "threats",
        "assets",
        "applied_controls",
        "security_exceptions",
    ]
    ordering = ["ref_id"]
    search_fields = ["name", "description", "ref_id"]

    def _perform_write(self, serializer):
        if not serializer.validated_data.get(
            "ref_id"
        ) and serializer.validated_data.get("risk_assessment"):
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
        folder_id = request.query_params.get("folder", None)
        return Response(
            {"results": risks_count_per_level(request.user, None, folder_id)}
        )

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


class RiskAcceptanceFilterSet(df.FilterSet):
    to_review = df.BooleanFilter(method="filter_to_review")

    def filter_to_review(self, queryset, name, value):
        if value:
            return (
                queryset.filter(expiry_date__lte=date.today() + timedelta(days=30))
                .filter(state__in=["submitted", "accepted"])
                .order_by("expiry_date")
            )

        return queryset

    class Meta:
        model = RiskAcceptance
        fields = {
            "folder": ["exact"],
            "state": ["exact"],
            "approver": ["exact"],
            "risk_scenarios": ["exact"],
            "expiry_date": ["exact", "lte", "gte", "lt", "gt", "month", "year"],
        }


class RiskAcceptanceViewSet(BaseModelViewSet):
    """
    API endpoint that allows risk acceptance to be viewed or edited.
    """

    permission_overrides = {
        "accept": "approve_riskacceptance",
        "reject": "approve_riskacceptance",
        "revoke": "approve_riskacceptance",
    }

    model = RiskAcceptance
    serializer_class = RiskAcceptanceWriteSerializer
    filterset_class = RiskAcceptanceFilterSet
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
            return Response(data=_data, status=status.HTTP_400_BAD_REQUEST)
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

    @action(detail=True, methods=["post"], name="Submit risk acceptance")
    def submit(self, request, pk):
        if self.get_object().approver:
            self.get_object().set_state("submitted")
            return Response({"results": "state updated to submitted"})
        else:
            return Response(
                {"error": "Missing 'approver' field"}, status=status.HTTP_403_FORBIDDEN
            )

    # This set back risk acceptance to "Created"
    @action(detail=True, methods=["post"], name="Draft risk acceptance")
    def draft(self, request, pk):
        self.get_object().set_state("created")
        return Response({"results": "state updated back to created"})

    @action(detail=True, methods=["post"], name="Accept risk acceptance")
    def accept(self, request, pk):
        if request.user != self.get_object().approver:
            logger.error(
                "Only the approver can accept the risk acceptance",
                user=request.user,
                approver=self.get_object().approver,
            )
            raise PermissionDenied(
                {"error": "Only the approver can accept the risk acceptance"}
            )
        self.get_object().set_state("accepted")
        return Response({"results": "state updated to accepted"})

    @action(detail=True, methods=["post"], name="Reject risk acceptance")
    def reject(self, request, pk):
        if request.user != self.get_object().approver:
            logger.error(
                "Only the approver can reject the risk acceptance",
                user=request.user,
                approver=self.get_object().approver,
            )
            raise PermissionDenied(
                {"error": "Only the approver can reject the risk acceptance"}
            )
        self.get_object().set_state("rejected")
        return Response({"results": "state updated to rejected"})

    @action(detail=True, methods=["post"], name="Revoke risk acceptance")
    def revoke(self, request, pk):
        if request.user != self.get_object().approver:
            logger.error(
                "Only the approver can revoke the risk acceptance",
                user=request.user,
                approver=self.get_object().approver,
            )
            raise PermissionDenied(
                {"error": "Only the approver can revoke the risk acceptance"}
            )
        self.get_object().set_state("revoked")
        return Response({"results": "state updated to revoked"})

    @action(detail=False, methods=["get"], name="Get waiting risk acceptances")
    def waiting(self, request):
        acceptance_count = RiskAcceptance.objects.filter(
            approver=request.user, state="submitted"
        ).count()
        return Response({"count": acceptance_count})

    def perform_update(self, serializer):
        risk_acceptance = serializer.validated_data

        if risk_acceptance.get("approver"):
            for scenario in risk_acceptance.get("risk_scenarios"):
                if not RoleAssignment.is_access_allowed(
                    risk_acceptance.get("approver"),
                    Permission.objects.get(codename="approve_riskacceptance"),
                    scenario.risk_assessment.perimeter.folder,
                ):
                    raise ValidationError(
                        "The approver is not allowed to approve this risk acceptance"
                    )
        risk_acceptance = serializer.save()

    @action(detail=False, name="Get state choices")
    def state(self, request):
        return Response(dict(RiskAcceptance.ACCEPTANCE_STATE))


class UserFilter(df.FilterSet):
    is_approver = df.BooleanFilter(method="filter_approver", label="Approver")
    is_applied_control_owner = df.BooleanFilter(
        method="filter_applied_control_owner", label="Applied control owner"
    )

    def filter_approver(self, queryset, name, value):
        """we don't know yet which folders will be used, so filter on any folder"""
        approvers_id = []
        for candidate in User.objects.all():
            if "approve_riskacceptance" in candidate.permissions:
                approvers_id.append(candidate.id)
        if value:
            return queryset.filter(id__in=approvers_id)
        return queryset.exclude(id__in=approvers_id)

    def filter_applied_control_owner(self, queryset, name, value):
        return queryset.filter(applied_controls__isnull=not value)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "is_active",
            "keep_local_login",
            "is_approver",
            "is_third_party",
        ]


class UserViewSet(BaseModelViewSet):
    """
    API endpoint that allows users to be viewed or edited
    """

    model = User
    ordering = ["-is_active", "-is_superuser", "email", "id"]
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
                        status=status.HTTP_403_FORBIDDEN,
                    )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.is_admin():
            number_of_admin_users = User.get_admin_users().count()
            if number_of_admin_users == 1:
                return Response(
                    {"error": "attemptToDeleteOnlyAdminAccountError"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return super().destroy(request, *args, **kwargs)


class UserGroupOrderingFilter(filters.OrderingFilter):
    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if not ordering:
            return ordering

        # Replace 'localization_dict' with 'folder'
        mapped_ordering = []
        for field in ordering:
            if field.lstrip("-") == "localization_dict":
                is_desc = field.startswith("-")
                mapped_field = "folder"
                if is_desc:
                    mapped_field = "-" + mapped_field
                mapped_ordering.append(mapped_field)
            else:
                mapped_ordering.append(field)

        return mapped_ordering


class UserGroupViewSet(BaseModelViewSet):
    """
    API endpoint that allows user groups to be viewed or edited
    """

    model = UserGroup
    ordering = ["builtin", "name"]
    ordering_fields = ["localization_dict"]
    filterset_fields = ["folder"]
    search_fields = [
        "folder__name"
    ]  # temporary hack, filters only by folder name, not role name
    filter_backends = [
        DjangoFilterBackend,
        UserGroupOrderingFilter,
        filters.SearchFilter,
    ]


class RoleViewSet(BaseModelViewSet):
    """
    API endpoint that allows roles to be viewed or edited
    """

    model = Role
    ordering = ["builtin", "name"]


class RoleAssignmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows role assignments to be viewed or edited.
    """

    model = RoleAssignment
    ordering = ["builtin", "folder"]
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
    search_fields = ["name"]
    batch_size = 100  # Configurable batch size for processing domain import

    def perform_create(self, serializer):
        """
        Create the default user groups after domain creation
        """
        serializer.save()
        folder = Folder.objects.get(id=serializer.data["id"])
        Folder.create_default_ug_and_ra(folder)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def org_tree(self, request):
        """
        Returns the tree of domains and perimeters
        """
        # Get include_perimeters parameter from query params, default to True if not provided
        include_perimeters = request.query_params.get(
            "include_perimeters", "True"
        ).lower() in ["true", "1", "yes"]

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
            entry = {
                "name": folder.name,
                "symbol": "roundRect",
                "uuid": folder.id,
            }
            folder_content = get_folder_content(
                folder, include_perimeters=include_perimeters
            )
            if len(folder_content) > 0:
                entry.update({"children": folder_content})
            folders_list.append(entry)
        tree.update({"children": folders_list})
        return Response(tree)

    @action(detail=False, methods=["get"])
    def ids(self, request):
        my_map = dict()

        (viewable_items, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Folder,
        )
        for item in Folder.objects.filter(id__in=viewable_items):
            my_map[item.name] = item.id
        return Response(my_map)

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
                sum += audit.get_progress()
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

    @action(detail=True, methods=["get"])
    def export(self, request, pk):
        include_attachments = True
        instance = self.get_object()

        logger.info(
            "Starting domain export",
            domain_id=instance.id,
            domain_name=instance.name,
            include_attachments=include_attachments,
            user=request.user.username,
        )

        objects = get_domain_export_objects(instance)

        for model in objects.keys():
            if not RoleAssignment.is_access_allowed(
                user=request.user,
                perm=Permission.objects.get(codename=f"view_{model}"),
                folder=instance,
            ):
                logger.error(
                    "User does not have permission to export object",
                    user=request.user,
                    model=model,
                )
                raise PermissionDenied(
                    {"error": "userDoesNotHavePermissionToExportDomain"}
                )

        logger.debug(
            "Retrieved domain objects for export",
            object_types=list(objects.keys()),
            total_objects=sum(len(queryset) for queryset in objects.values()),
            objects_per_model={
                model: len(queryset) for model, queryset in objects.items()
            },
        )

        # Create in-memory zip file
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            if include_attachments:
                evidences = objects.get("evidence", Evidence.objects.none()).filter(
                    attachment__isnull=False
                )
                logger.info(
                    "Processing evidence attachments",
                    total_evidences=evidences.count(),
                    domain_id=instance.id,
                )

                for evidence in evidences:
                    if evidence.attachment and default_storage.exists(
                        evidence.attachment.name
                    ):
                        # Read file directly into memory
                        with default_storage.open(evidence.attachment.name) as file:
                            file_content = file.read()
                            # Write the file content directly to the zip
                            zipf.writestr(
                                os.path.join(
                                    "attachments",
                                    os.path.basename(evidence.attachment.name),
                                ),
                                file_content,
                            )

            # Add the JSON dump to the zip file
            dumpfile_name = (
                f"ciso-assistant-{slugify(instance.name)}-domain-{timezone.now()}"
            )
            dump_data = ExportSerializer.dump_data(scope=[*objects.values()])

            logger.debug(
                "Adding JSON dump to zip",
                json_size=len(json.dumps(dump_data).encode("utf-8")),
                filename=f"{dumpfile_name}.json",
            )

            zipf.writestr("data.json", json.dumps(dump_data).encode("utf-8"))

        # Reset buffer position to the start
        zip_buffer.seek(0)
        final_size = len(zip_buffer.getvalue())

        # Create the response with the in-memory zip file
        response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{dumpfile_name}.zip"'

        logger.info(
            "Domain export completed successfully",
            domain_id=instance.id,
            domain_name=instance.name,
            zip_size=final_size,
            filename=f"{dumpfile_name}.zip",
        )

        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=(FileUploadParser,),
    )
    def import_domain(self, request):
        """Handle file upload and initiate import process."""
        load_missing_libraries = (
            request.query_params.get("load_missing_libraries", "false").lower()
            == "true"
        )
        try:
            if not RoleAssignment.is_access_allowed(
                user=request.user,
                perm=Permission.objects.get(codename="add_folder"),
                folder=Folder.get_root_folder(),
            ):
                raise PermissionDenied()
            domain_name = request.headers.get(
                "X-CISOAssistantDomainName", str(uuid.uuid4())
            )
            parsed_data = self._process_uploaded_file(request.data["file"])
            result = self._import_objects(
                parsed_data, domain_name, load_missing_libraries, user=request.user
            )
            return Response(result, status=status.HTTP_200_OK)

        except PermissionDenied:
            logger.error(
                "User does not have permission to import domain",
                user=request.user,
                exc_info=True,
            )
            return Response(
                {"error": "userDoesNotHavePermissionToImportDomain"},
                status=status.HTTP_403_FORBIDDEN,
            )

        except KeyError:
            logger.error("No file provided in the request", exc_info=True)
            return Response(
                {"errors": ["No file provided"]}, status=status.HTTP_400_BAD_REQUEST
            )

        except json.JSONDecodeError:
            logger.error("Invalid JSON format in uploaded file", exc_info=True)
            return Response(
                {"errors": ["Invalid JSON format"]}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=["post"],
        url_path="import-dummy",
    )
    def import_dummy_domain(self, request):
        domain_name = "DEMO"
        try:
            dummy_fixture_path = (
                Path(settings.BASE_DIR) / "fixtures" / "dummy-domain.bak"
            )
            if not dummy_fixture_path.exists():
                logger.error("Dummy domain fixture not found", path=dummy_fixture_path)
                return Response(
                    {"error": "dummyDomainFixtureNotFound"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            parsed_data = self._process_uploaded_file(dummy_fixture_path)
            result = self._import_objects(
                parsed_data, domain_name, load_missing_libraries=True, user=request.user
            )
            logger.info("Dummy domain imported successfully", domain_name=domain_name)
            return Response(result, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            logger.error("Invalid JSON format in dummy fixture file")
            return Response(
                {"errors": ["Invalid JSON format"]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            logger.error("Error importing dummy domain")
            return Response(
                {"error": "failedToImportDummyDomain"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _process_uploaded_file(self, dump_file: str | Path) -> Any:
        """Process the uploaded file and return parsed data."""
        if not zipfile.is_zipfile(dump_file):
            logger.error("Invalid ZIP file format")
            raise ValidationError({"file": "invalidZipFileFormat"})

        with zipfile.ZipFile(dump_file, mode="r") as zipf:
            if "data.json" not in zipf.namelist():
                logger.error(
                    "No data.json file found in uploaded file", files=zipf.namelist()
                )
                raise ValidationError({"file": "noDataJsonFileFound"})
            infolist = zipf.infolist()
            directories = list(set([Path(f.filename).parent.name for f in infolist]))
            decompressed_data = zipf.read("data.json")
            # Decode bytes to string if necessary
            if isinstance(decompressed_data, bytes):
                decompressed_data = decompressed_data.decode("utf-8")
            try:
                json_dump = json.loads(decompressed_data)
                import_version = json_dump["meta"]["media_version"]
                schema_version = json_dump["meta"].get("schema_version")
            except json.JSONDecodeError:
                logger.error("Invalid JSON format in uploaded file", exc_info=True)
                raise
            if "objects" not in json_dump:
                raise ValidationError("badly formatted json")

            # Check backup and local version

            try:
                schema_version_int = int(schema_version)
            except (ValueError, TypeError) as e:
                logger.error(
                    "Invalid schema version format",
                    schema_version=schema_version,
                    exc_info=e,
                )
                raise ValidationError({"error": "invalidSchemaVersionFormat"})
            compare_schema_versions(schema_version_int, import_version)

            if "attachments" in directories:
                attachments = {
                    f for f in infolist if Path(f.filename).parent.name == "attachments"
                }
                logger.info(
                    "Attachments found in uploaded file",
                    attachments_count=len(attachments),
                )
                for attachment in attachments:
                    try:
                        content = zipf.read(attachment)
                        current_name = Path(attachment.filename).name
                        new_name = default_storage.save(
                            current_name, io.BytesIO(content)
                        )
                        if new_name != current_name:
                            for x in json_dump["objects"]:
                                if (
                                    x["model"] == "core.evidence"
                                    and x["fields"]["attachment"] == current_name
                                ):
                                    x["fields"]["attachment"] = new_name

                    except Exception:
                        logger.error("Error extracting attachment", exc_info=True)

        return json_dump

    def _get_models_map(self, objects):
        """Build a map of model names to model classes."""
        model_names = {obj["model"] for obj in objects}
        return {name: apps.get_model(name) for name in model_names}

    def _resolve_dependencies(self, all_models):
        """Resolve model dependencies and detect cycles."""
        logger.debug("Resolving model dependencies", all_models=all_models)

        graph = build_dependency_graph(all_models)

        logger.debug("Dependency graph", graph=graph)

        try:
            return topological_sort(graph)
        except ValueError as e:
            logger.error("Cyclic dependency detected", error=str(e))
            raise ValidationError({"error": "Cyclic dependency detected"})

    def _import_objects(
        self, parsed_data: dict, domain_name: str, load_missing_libraries: bool, user
    ):
        """
        Import and validate objects using appropriate serializers.
        Handles both validation and creation in separate phases within a transaction.
        """
        validation_errors = []
        required_libraries = []
        missing_libraries = []
        link_dump_database_ids = {}

        # First check if objects exist
        objects = parsed_data.get("objects")
        if not objects:
            logger.error("No objects found in the dump")
            raise ValidationError({"error": "No objects found in the dump"})

        try:
            # Validate models and check for domain
            models_map = self._get_models_map(objects)
            if Folder in models_map.values():
                logger.error("Dump contains a domain")
                raise ValidationError({"error": "Dump contains a domain"})

            # check that user has permission to create all objects to import
            error_dict = {}
            for model in filter(
                lambda x: x not in [RequirementAssessment], models_map.values()
            ):
                if not RoleAssignment.is_access_allowed(
                    user=user,
                    perm=Permission.objects.get(
                        codename=f"add_{model._meta.model_name}"
                    ),
                    folder=Folder.get_root_folder(),
                ):
                    error_dict[model._meta.model_name] = "permission_denied"
            if error_dict:
                logger.error(
                    "User does not have permission to import objects",
                    error_dict=error_dict,
                )
                raise PermissionDenied()

            # Validation phase (outside transaction since it doesn't modify database)
            creation_order = self._resolve_dependencies(list(models_map.values()))

            logger.debug("Resolved creation order", creation_order=creation_order)
            logger.debug("Starting objects validation", objects_count=len(objects))

            # Validate all objects first
            for model in creation_order:
                self._validate_model_objects(
                    model=model,
                    objects=objects,
                    validation_errors=validation_errors,
                    required_libraries=required_libraries,
                )

            logger.debug("required_libraries", required_libraries=required_libraries)

            # If validation errors exist, raise them immediately
            if validation_errors:
                logger.error(
                    "Failed to validate objects", validation_errors=validation_errors
                )
                raise ValidationError({"validation_errors": validation_errors})

            # Creation phase - wrap in transaction
            with transaction.atomic():
                # Create base folder and store its ID
                base_folder = Folder.objects.create(
                    name=domain_name, content_type=Folder.ContentType.DOMAIN
                )
                link_dump_database_ids["base_folder"] = base_folder
                Folder.create_default_ug_and_ra(base_folder)

                # Check for missing libraries after folder creation
                for library in required_libraries:
                    if not LoadedLibrary.objects.filter(
                        urn=library["urn"], version=library["version"]
                    ).exists():
                        if (
                            StoredLibrary.objects.filter(
                                urn=library["urn"], version__gte=library["version"]
                            ).exists()
                            and load_missing_libraries
                        ):
                            StoredLibrary.objects.get(
                                urn=library["urn"], version__gte=library["version"]
                            ).load()
                        else:
                            missing_libraries.append(library)

                logger.debug("missing_libraries", missing_libraries=missing_libraries)

                # If missing libraries exist, raise specific error
                if missing_libraries:
                    logger.warning(f"Missing libraries: {missing_libraries}")
                    raise ValidationError({"missing_libraries": missing_libraries})

                logger.info(
                    "Starting objects creation",
                    objects_count=len(objects),
                    creation_order=creation_order,
                )

                # Create all objects within the transaction
                for model in creation_order:
                    self._create_model_objects(
                        model=model,
                        objects=objects,
                        link_dump_database_ids=link_dump_database_ids,
                    )

            return {"message": "Import successful"}

        except ValidationError as e:
            logger.error(f"error: {e}")
            raise
        except Exception as e:
            # Handle unexpected errors with a generic message
            logger.exception(f"Failed to import objects: {str(e)}")
            raise ValidationError({"non_field_errors": "errorOccuredDuringImport"})

    def _validate_model_objects(
        self, model, objects, validation_errors, required_libraries
    ):
        """Validate all objects for a model before creation."""
        model_name = f"{model._meta.app_label}.{model._meta.model_name}"
        model_objects = [obj for obj in objects if obj["model"] == model_name]

        if not model_objects:
            return

        # Process validation in batches
        for i in range(0, len(model_objects), self.batch_size):
            batch = model_objects[i : i + self.batch_size]
            self._validate_batch(
                model=model,
                batch=batch,
                validation_errors=validation_errors,
                required_libraries=required_libraries,
            )

    def _validate_batch(self, model, batch, validation_errors, required_libraries):
        """Validate a batch of objects."""
        model_name = f"{model._meta.app_label}.{model._meta.model_name}"

        for obj in batch:
            obj_id = obj.get("id")
            fields = obj.get("fields", {}).copy()

            try:
                # Handle library objects
                if model == LoadedLibrary:
                    required_libraries.append(
                        {"urn": fields["urn"], "version": fields["version"]}
                    )
                    logger.info(
                        "Adding library to required libraries", urn=fields["urn"]
                    )
                    continue
                if fields.get("library"):
                    continue

                # Validate using serializer
                serializer_class = import_export_serializer_class(model)
                serializer = serializer_class(data=fields)

                if not serializer.is_valid():
                    validation_errors.append(
                        {
                            "model": model_name,
                            "id": obj_id,
                            "errors": serializer.errors,
                        }
                    )

            except Exception as e:
                logger.error(
                    f"Error validating object {obj_id} in {model_name}: {str(e)}",
                    exc_info=True,
                )
                validation_errors.append(
                    {
                        "model": model_name,
                        "id": obj_id,
                        "errors": [str(e)],
                    }
                )

    def _create_model_objects(self, model, objects, link_dump_database_ids):
        """Create all objects for a model after validation."""
        logger.debug("Creating objects for model", model=model)

        model_name = f"{model._meta.app_label}.{model._meta.model_name}"
        model_objects = [obj for obj in objects if obj["model"] == model_name]

        logger.debug("Model objects", model=model, count=len(model_objects))

        if not model_objects:
            return

        # Handle self-referencing dependencies
        self_ref_field = get_self_referencing_field(model)
        if self_ref_field:
            try:
                model_objects = sort_objects_by_self_reference(
                    model_objects, self_ref_field
                )
            except ValueError as e:
                logger.error(f"Cyclic dependency detected in {model_name}: {str(e)}")
                raise ValidationError(
                    {"error": f"Cyclic dependency detected in {model_name}"}
                )

        # Process creation in batches
        for i in range(0, len(model_objects), self.batch_size):
            batch = model_objects[i : i + self.batch_size]
            self._create_batch(
                model=model,
                batch=batch,
                link_dump_database_ids=link_dump_database_ids,
            )

    def _create_batch(self, model, batch, link_dump_database_ids):
        """Create a batch of objects with proper relationship handling."""
        # Create all objects in the batch within a single transaction
        with transaction.atomic():
            for obj in batch:
                obj_id = obj.get("id")
                fields = obj.get("fields", {}).copy()

                try:
                    # Handle library objects
                    if fields.get("library") or model == LoadedLibrary:
                        logger.info(f"Skipping creation of library object {obj_id}")
                        link_dump_database_ids[obj_id] = fields.get("urn")
                        continue

                    # Handle folder reference
                    if fields.get("folder"):
                        fields["folder"] = link_dump_database_ids.get("base_folder")

                    # Process model-specific relationships
                    many_to_many_map_ids = {}
                    fields = self._process_model_relationships(
                        model=model,
                        fields=fields,
                        link_dump_database_ids=link_dump_database_ids,
                        many_to_many_map_ids=many_to_many_map_ids,
                    )

                    try:
                        # Run clean to validate unique constraints
                        model(**fields).clean()
                    except ValidationError as e:
                        for field, error in e.error_dict.items():
                            fields[field] = f"{fields[field]} {uuid.uuid4()}"

                    logger.debug("Creating object", fields=fields)

                    # Create the object
                    obj_created = model.objects.create(**fields)
                    link_dump_database_ids[obj_id] = obj_created.id

                    # Handle many-to-many relationships
                    self._set_many_to_many_relations(
                        model=model,
                        obj=obj_created,
                        many_to_many_map_ids=many_to_many_map_ids,
                    )

                except Exception as e:
                    logger.error("Error creating object", obj=obj, exc_info=True)
                    # This will trigger a rollback of the entire batch
                    raise ValidationError(
                        f"Error creating {model._meta.model_name}: {str(e)}"
                    )

    def _process_model_relationships(
        self,
        model,
        fields,
        link_dump_database_ids,
        many_to_many_map_ids,
    ):
        """Process model-specific relationships."""

        def get_mapped_ids(
            ids: List[str], link_dump_database_ids: Dict[str, str]
        ) -> List[str]:
            return [
                link_dump_database_ids[id] for id in ids if id in link_dump_database_ids
            ]

        model_name = model._meta.model_name
        _fields = fields.copy()

        logger.debug(
            "Processing model relationships", model=model_name, _fields=_fields
        )

        match model_name:
            case "asset":
                many_to_many_map_ids["parent_ids"] = get_mapped_ids(
                    _fields.pop("parent_assets", []), link_dump_database_ids
                )

            case "riskassessment":
                _fields["perimeter"] = Perimeter.objects.get(
                    id=link_dump_database_ids.get(_fields["perimeter"])
                )
                _fields["risk_matrix"] = RiskMatrix.objects.get(
                    urn=_fields.get("risk_matrix")
                )
                _fields["ebios_rm_study"] = (
                    EbiosRMStudy.objects.get(
                        id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                    )
                    if _fields.get("ebios_rm_study")
                    else None
                )

            case "complianceassessment":
                _fields["perimeter"] = Perimeter.objects.get(
                    id=link_dump_database_ids.get(_fields["perimeter"])
                )
                _fields["framework"] = Framework.objects.get(urn=_fields["framework"])

            case "appliedcontrol":
                many_to_many_map_ids["evidence_ids"] = get_mapped_ids(
                    _fields.pop("evidences", []), link_dump_database_ids
                )
                ref_control_id = link_dump_database_ids.get(
                    _fields["reference_control"]
                )
                _fields["reference_control"] = ReferenceControl.objects.filter(
                    urn=ref_control_id
                ).first()

            case "evidence":
                _fields.pop("size", None)
                _fields.pop("attachment_hash", None)

            case "requirementassessment":
                logger.debug("Looking for requirement", urn=_fields.get("requirement"))
                _fields["requirement"] = RequirementNode.objects.get(
                    urn=_fields.get("requirement")
                )
                _fields["compliance_assessment"] = ComplianceAssessment.objects.get(
                    id=link_dump_database_ids.get(_fields["compliance_assessment"])
                )
                many_to_many_map_ids.update(
                    {
                        "applied_controls": get_mapped_ids(
                            _fields.pop("applied_controls", []), link_dump_database_ids
                        ),
                        "evidence_ids": get_mapped_ids(
                            _fields.pop("evidences", []), link_dump_database_ids
                        ),
                    }
                )

            case "vulnerability":
                many_to_many_map_ids["applied_controls"] = get_mapped_ids(
                    _fields.pop("applied_controls", []), link_dump_database_ids
                )

            case "riskscenario":
                _fields["risk_assessment"] = RiskAssessment.objects.get(
                    id=link_dump_database_ids.get(_fields["risk_assessment"])
                )
                # Process all related _fields at once
                related__fields = [
                    "threats",
                    "vulnerabilities",
                    "assets",
                    "applied_controls",
                    "existing_applied_controls",
                ]
                for field in related__fields:
                    map_key = (
                        f"{field.rstrip('s')}_ids"
                        if not field.endswith("controls")
                        else f"{field}_ids"
                    )
                    many_to_many_map_ids[map_key] = get_mapped_ids(
                        _fields.pop(field, []), link_dump_database_ids
                    )

            case "entity":
                _fields.pop("owned_folders", None)

            case "ebiosrmstudy":
                _fields.update(
                    {
                        "risk_matrix": RiskMatrix.objects.get(
                            urn=_fields.get("risk_matrix")
                        ),
                        "reference_entity": Entity.objects.get(
                            id=link_dump_database_ids.get(_fields["reference_entity"])
                        ),
                    }
                )
                many_to_many_map_ids.update(
                    {
                        "asset_ids": get_mapped_ids(
                            _fields.pop("assets", []), link_dump_database_ids
                        ),
                        "compliance_assessment_ids": get_mapped_ids(
                            _fields.pop("compliance_assessments", []),
                            link_dump_database_ids,
                        ),
                    }
                )

            case "fearedevent":
                _fields["ebios_rm_study"] = EbiosRMStudy.objects.get(
                    id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                )
                many_to_many_map_ids.update(
                    {
                        "qualifications_urn": get_mapped_ids(
                            _fields.pop("qualifications", []), link_dump_database_ids
                        ),
                        "asset_ids": get_mapped_ids(
                            _fields.pop("assets", []), link_dump_database_ids
                        ),
                    }
                )

            case "roto":
                _fields["ebios_rm_study"] = EbiosRMStudy.objects.get(
                    id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                )
                many_to_many_map_ids["feared_event_ids"] = get_mapped_ids(
                    _fields.pop("feared_events", []), link_dump_database_ids
                )

            case "stakeholder":
                _fields.update(
                    {
                        "ebios_rm_study": EbiosRMStudy.objects.get(
                            id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                        ),
                        "entity": Entity.objects.get(
                            id=link_dump_database_ids.get(_fields["entity"])
                        ),
                    }
                )
                many_to_many_map_ids["applied_controls"] = get_mapped_ids(
                    _fields.pop("applied_controls", []), link_dump_database_ids
                )

            case "strategicscenario":
                _fields.update(
                    {
                        "ebios_rm_study": EbiosRMStudy.objects.get(
                            id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                        ),
                        "ro_to_couple": RoTo.objects.get(
                            id=link_dump_database_ids.get(_fields["ro_to_couple"])
                        ),
                    }
                )

            case "attackpath":
                _fields.update(
                    {
                        "ebios_rm_study": EbiosRMStudy.objects.get(
                            id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                        ),
                        "strategic_scenario": StrategicScenario.objects.get(
                            id=link_dump_database_ids.get(_fields["strategic_scenario"])
                        ),
                    }
                )
                many_to_many_map_ids["stakeholder_ids"] = get_mapped_ids(
                    _fields.pop("stakeholders", []), link_dump_database_ids
                )

            case "operationalscenario":
                _fields.update(
                    {
                        "ebios_rm_study": EbiosRMStudy.objects.get(
                            id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                        ),
                        "attack_path": AttackPath.objects.get(
                            id=link_dump_database_ids.get(_fields["attack_path"])
                        ),
                    }
                )
                many_to_many_map_ids["threat_ids"] = get_mapped_ids(
                    _fields.pop("threats", []), link_dump_database_ids
                )

        return _fields

    def _set_many_to_many_relations(self, model, obj, many_to_many_map_ids):
        """Set many-to-many relationships after object creation."""
        model_name = model._meta.model_name

        match model_name:
            case "asset":
                if parent_ids := many_to_many_map_ids.get("parent_ids"):
                    logger.debug(
                        "Setting parent assets", asset=obj, parent_ids=parent_ids
                    )
                    obj.parent_assets.set(Asset.objects.filter(id__in=parent_ids))

            case "appliedcontrol":
                if evidence_ids := many_to_many_map_ids.get("evidence_ids"):
                    obj.evidences.set(Evidence.objects.filter(id__in=evidence_ids))

            case "requirementassessment":
                if applied_control_ids := many_to_many_map_ids.get("applied_controls"):
                    obj.applied_controls.set(
                        AppliedControl.objects.filter(id__in=applied_control_ids)
                    )
                if evidence_ids := many_to_many_map_ids.get("evidence_ids"):
                    obj.evidences.set(Evidence.objects.filter(id__in=evidence_ids))

            case "vulnerability":
                if applied_control_ids := many_to_many_map_ids.get("applied_controls"):
                    obj.applied_controls.set(
                        AppliedControl.objects.filter(id__in=applied_control_ids)
                    )

            case "riskscenario":
                if threat_ids := many_to_many_map_ids.get("threat_ids"):
                    uuids, urns = self._split_uuids_urns(threat_ids)
                    obj.threats.set(
                        Threat.objects.filter(Q(id__in=uuids) | Q(urn__in=urns))
                    )

                for field, model_class in {
                    "vulnerability_ids": (Vulnerability, "vulnerabilities"),
                    "asset_ids": (Asset, "assets"),
                    "applied_control_ids": (AppliedControl, "applied_controls"),
                    "existing_applied_control_ids": (
                        AppliedControl,
                        "existing_applied_controls",
                    ),
                }.items():
                    if ids := many_to_many_map_ids.get(field):
                        getattr(obj, model_class[1]).set(
                            model_class[0].objects.filter(id__in=ids)
                        )

            case "ebiosrmstudy":
                if asset_ids := many_to_many_map_ids.get("asset_ids"):
                    obj.assets.set(Asset.objects.filter(id__in=asset_ids))
                if compliance_assessment_ids := many_to_many_map_ids.get(
                    "compliance_assessment_ids"
                ):
                    obj.compliance_assessments.set(
                        ComplianceAssessment.objects.filter(
                            id__in=compliance_assessment_ids
                        )
                    )

            case "fearedevent":
                if qualifications_urn := many_to_many_map_ids.get("qualifications_urn"):
                    obj.qualifications.set(
                        Qualification.objects.filter(urn__in=qualifications_urn)
                    )
                if asset_ids := many_to_many_map_ids.get("asset_ids"):
                    obj.assets.set(Asset.objects.filter(id__in=asset_ids))

            case "roto":
                if feared_event_ids := many_to_many_map_ids.get("feared_event_ids"):
                    obj.feared_events.set(
                        FearedEvent.objects.filter(id__in=feared_event_ids)
                    )

            case "stakeholder":
                if applied_control_ids := many_to_many_map_ids.get("applied_controls"):
                    obj.applied_controls.set(
                        AppliedControl.objects.filter(id__in=applied_control_ids)
                    )

            case "attackpath":
                if stakeholder_ids := many_to_many_map_ids.get("stakeholder_ids"):
                    obj.stakeholders.set(
                        Stakeholder.objects.filter(id__in=stakeholder_ids)
                    )

            case "operationalscenario":
                if threat_ids := many_to_many_map_ids.get("threat_ids"):
                    uuids, urns = self._split_uuids_urns(threat_ids)
                    obj.threats.set(
                        Threat.objects.filter(Q(id__in=uuids) | Q(urn__in=urns))
                    )

    def _split_uuids_urns(self, ids: List[str]) -> Tuple[List[str], List[str]]:
        """Split a list of strings into UUIDs and URNs."""
        uuids = []
        urns = []
        for item in ids:
            try:
                uuid = UUID(str(item))
                uuids.append(uuid)
            except ValueError:
                urns.append(item)
        return uuids, urns

    @action(detail=False, methods=["get"])
    def get_accessible_objects(self, request):
        (viewable_folders_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, Folder
        )
        (viewable_perimeters_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, Perimeter
        )
        (viewable_frameworks_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, Framework
        )
        res = {
            "folders": [
                {"name": str(f), "id": f.id}
                for f in Folder.objects.filter(id__in=viewable_folders_ids).order_by(
                    Lower("name")
                )
            ],
            "perimeters": [
                {"name": str(p), "id": p.id}
                for p in Perimeter.objects.filter(
                    id__in=viewable_perimeters_ids
                ).order_by(Lower("name"))
            ],
            "frameworks": [
                {"name": f.name, "id": f.id}
                for f in Framework.objects.filter(
                    id__in=viewable_frameworks_ids
                ).order_by(Lower("name"))
            ],
        }
        return Response(res)


class UserPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request) -> Response:
        return Response(request.user.preferences, status=status.HTTP_200_OK)

    def patch(self, request) -> Response:
        new_language = request.data.get("lang")
        if new_language is None or new_language not in (
            lang[0] for lang in settings.LANGUAGES
        ):
            logger.error(
                f"Error in UserPreferencesView: new_language={new_language} available languages={[lang[0] for lang in settings.LANGUAGES]}"
            )
            return Response(
                {"error": "This language doesn't exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.preferences["lang"] = new_language
        request.user.save()
        return Response({}, status=status.HTTP_200_OK)


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
    folder_id = request.query_params.get("folder", None)
    return Response({"results": get_metrics(request.user, folder_id)})


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
            # UUID REGEX
            r"([0-9a-f]{8}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{4}\-[0-9a-f]{12})",
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


class FrameworkFilter(df.FilterSet):
    baseline = df.ModelChoiceFilter(
        queryset=ComplianceAssessment.objects.all(),
        method="filter_framework",
        label="Baseline",
    )

    def filter_framework(self, queryset, name, value):
        if not value:
            return queryset
        source_framework = value.framework
        target_framework_ids = list(
            RequirementMappingSet.objects.filter(
                source_framework=source_framework
            ).values_list("target_framework__id", flat=True)
        )
        target_framework_ids.append(source_framework.id)
        return queryset.filter(id__in=target_framework_ids)

    class Meta:
        model = Framework
        fields = ["folder", "baseline", "provider"]


class FrameworkViewSet(BaseModelViewSet):
    """
    API endpoint that allows frameworks to be viewed or edited.
    """

    model = Framework
    filterset_class = FrameworkFilter
    search_fields = ["name", "description"]

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

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        providers = set(
            Framework.objects.filter(provider__isnull=False).values_list(
                "provider", flat=True
            )
        )
        return Response({p: p for p in providers})

    @action(detail=True, methods=["get"], name="Framework as an Excel template")
    def excel_template(self, request, pk):
        fwk = Framework.objects.get(id=pk)
        req_nodes = RequirementNode.objects.filter(framework=fwk)
        entries = []
        for rn in req_nodes:
            entry = {
                "urn": rn.urn,
                "assessable": rn.assessable,
                "ref_id": rn.ref_id,
                "name": rn.name,
                "description": rn.description,
                "compliance_result": "",
                "requirement_progress": "",
                "score": "",
                "observations": "",
            }
            entries.append(entry)

        # Create DataFrame from entries
        df = pd.DataFrame(entries)

        # Create BytesIO object
        buffer = io.BytesIO()

        # Create ExcelWriter with openpyxl engine
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

            # Get the worksheet
            worksheet = writer.sheets["Sheet1"]

            # For text wrapping, we need to define which columns need wrapping
            # Assuming 'description' and 'observations' columns need text wrapping
            wrap_columns = ["name", "description", "observations"]

            # Find the indices of the columns that need wrapping
            wrap_indices = [
                df.columns.get_loc(col) + 1 for col in wrap_columns if col in df.columns
            ]

            # Apply text wrapping to those columns
            from openpyxl.styles import Alignment

            for col_idx in wrap_indices:
                for row_idx in range(
                    2, len(df) + 2
                ):  # +2 because of header row and 1-indexing
                    cell = worksheet.cell(row=row_idx, column=col_idx)
                    cell.alignment = Alignment(wrap_text=True)

            # Adjust column widths for better readability
            for idx, col in enumerate(df.columns):
                column_width = 40  # default width
                if col in wrap_columns:
                    column_width = 60  # wider for wrapped text columns
                worksheet.column_dimensions[
                    worksheet.cell(row=1, column=idx + 1).column_letter
                ].width = column_width

        # Get the value of the buffer and return as response
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{fwk.name}_template.xlsx"'
        )

        return response


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

    @action(detail=True, methods=["get"], name="Inspect specific requirements")
    def inspect_requirement(self, request, pk):
        requirement = RequirementNode.objects.get(id=pk)
        requirement_assessments = RequirementAssessment.objects.filter(
            requirement=requirement
        ).prefetch_related("folder", "compliance_assessment__perimeter")
        serialized_requirement_assessments = RequirementAssessmentReadSerializer(
            requirement_assessments, many=True
        ).data

        # Group by Domain and Perimeter
        grouped_data = requirement_assessments.values(
            "folder__name", "compliance_assessment__perimeter__name"
        ).annotate(
            compliant_count=Count(
                "id", filter=Q(result=RequirementAssessment.Result.COMPLIANT)
            ),
            total_count=Count("id"),
            assessed_count=Count(
                "id", filter=~Q(status=RequirementAssessment.Status.TODO)
            ),
            assessment_completion_rate=ExpressionWrapper(
                Count("id", filter=~Q(status=RequirementAssessment.Status.TODO))
                * 100.0
                / Count("id"),
                output_field=FloatField(),
            ),
        )

        # Collect all data by domain for calculations
        domain_data_collector = defaultdict(
            lambda: {
                "compliant_count": 0,
                "total_count": 0,
                "assessed_count": 0,
                "perimeter_data": [],
            }
        )

        for item in grouped_data:
            domain_name = item["folder__name"]
            domain_data_collector[domain_name]["compliant_count"] += item[
                "compliant_count"
            ]
            domain_data_collector[domain_name]["total_count"] += item["total_count"]
            domain_data_collector[domain_name]["assessed_count"] += item[
                "assessed_count"
            ]
            domain_data_collector[domain_name]["perimeter_data"].append(item)

        # Organize data by domain and perimeter using the collected data
        domain_dict = defaultdict(
            lambda: {
                "name": "",
                "compliance_result": {
                    "compliant_count": 0,
                    "total_count": 0,
                    "compliance_percentage": 0,
                },
                "assessment_progress": {
                    "assessed_count": 0,
                    "total_count": 0,
                    "assessment_completion_rate": 0,
                },
                "perimeters": [],
            }
        )

        # Structure the final response
        for domain_name, collector_data in domain_data_collector.items():
            domain_dict[domain_name]["name"] = domain_name

            # Calculate domain-level metrics
            domain_total_count = collector_data["total_count"]
            domain_compliant_count = collector_data["compliant_count"]
            domain_assessed_count = collector_data["assessed_count"]

            # Avoid division by zero
            domain_compliance_percentage = 0
            if domain_total_count > 0:
                domain_compliance_percentage = int(
                    (domain_compliant_count / domain_total_count) * 100
                )

            domain_assessment_completion_rate = 0
            if domain_total_count > 0:
                domain_assessment_completion_rate = int(
                    (domain_assessed_count / domain_total_count) * 100
                )

            # Set domain metrics
            domain_dict[domain_name]["compliance_result"] = {
                "compliant_count": domain_compliant_count,
                "total_count": domain_total_count,
                "compliance_percentage": domain_compliance_percentage,
            }

            domain_dict[domain_name]["assessment_progress"] = {
                "assessed_count": domain_assessed_count,
                "total_count": domain_total_count,
                "assessment_completion_rate": domain_assessment_completion_rate,
            }

            # Process perimeter data
            for item in collector_data["perimeter_data"]:
                perimeter_name = item["compliance_assessment__perimeter__name"]

                perimeter_entry = {
                    "name": perimeter_name,
                    "compliance_assessments": [],
                }

                # Add compliance assessments to the perimeter entry
                compliance_assessments = (
                    requirement_assessments.filter(
                        folder__name=domain_name,
                        compliance_assessment__perimeter__name=perimeter_name,
                    )
                    .select_related("compliance_assessment")
                    .values(
                        "compliance_assessment__id",
                        "compliance_assessment__name",
                        "compliance_assessment__version",
                        "compliance_assessment__show_documentation_score",
                        "compliance_assessment__max_score",
                    )
                    .distinct()
                )

                for ca in compliance_assessments:
                    perimeter_entry["compliance_assessments"].append(
                        {
                            "id": ca["compliance_assessment__id"],
                            "name": ca["compliance_assessment__name"],
                            "version": ca["compliance_assessment__version"],
                            "show_documentation_score": ca[
                                "compliance_assessment__show_documentation_score"
                            ],
                            "max_score": ca["compliance_assessment__max_score"],
                        }
                    )

                domain_dict[domain_name]["perimeters"].append(perimeter_entry)

        # Convert defaultdict to list for the response
        data_by_domain = [
            domain_data for domain_data in domain_dict.values() if domain_data["name"]
        ]

        return Response(
            {
                "requirement_assessments": serialized_requirement_assessments,
                "metrics": data_by_domain,
            }
        )


class EvidenceViewSet(BaseModelViewSet):
    """
    API endpoint that allows evidences to be viewed or edited.
    """

    model = Evidence
    filterset_fields = [
        "folder",
        "applied_controls",
        "requirement_assessments",
        "name",
        "timeline_entries",
        "filtering_labels",
    ]

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
            if not evidence.attachment or not evidence.attachment.storage.exists(
                evidence.attachment.name
            ):
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
                if not evidence.attachment and attachment.name != "undefined":
                    evidence.attachment = attachment
                elif (
                    evidence.attachment and attachment.name != "undefined"
                ) and evidence.attachment != attachment:
                    evidence.attachment.delete()
                    evidence.attachment = attachment
                evidence.save()
                return Response(status=status.HTTP_200_OK)
            except Exception:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class QuickStartView(APIView):
    serializer_class = QuickStartSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)
        try:
            objects = serializer.save()
        except Exception as e:
            logger.error(f"Error in QuickStartView: {e}")
            raise
        else:
            return Response(objects, status=status.HTTP_201_CREATED)


class QualificationViewSet(BaseModelViewSet):
    """
    API endpoint that allows qualifications to be viewed or edited.
    """

    model = Qualification
    search_fields = ["name"]


class ComplianceAssessmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows compliance assessments to be viewed or edited.
    """

    model = ComplianceAssessment
    filterset_fields = [
        "folder",
        "framework",
        "perimeter",
        "status",
        "ebios_rm_studies",
        "assets",
    ]
    search_fields = ["name", "description", "ref_id"]

    def get_queryset(self):
        qs = super().get_queryset()
        ordering = self.request.query_params.get("ordering", "")

        if any(
            field in ordering
            for field in (
                "total_requirements",
                "assessed_requirements",
                "progress",
            )
        ):
            qs = qs.annotate(
                total_requirements=Count(
                    "requirement_assessments",
                    filter=Q(requirement_assessments__requirement__assessable=True),
                    distinct=True,
                ),
                assessed_requirements=Count(
                    "requirement_assessments",
                    filter=Q(
                        ~Q(
                            requirement_assessments__result=RequirementAssessment.Result.NOT_ASSESSED
                        ),
                        requirement_assessments__requirement__assessable=True,
                    ),
                    distinct=True,
                ),
                progress=ExpressionWrapper(
                    F("assessed_requirements")
                    * 1.0
                    / Greatest(Coalesce(F("total_requirements"), Value(0)), Value(1)),
                    output_field=FloatField(),
                ),
            )
        return qs

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(ComplianceAssessment.Status.choices))

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

    @action(detail=True, methods=["get"])
    def word_report(self, request, pk):
        """
        Word report generation (Exec)
        """
        lang = "en"
        if request.user.preferences.get("lang") is not None:
            lang = request.user.preferences.get("lang")
            if lang not in ["fr", "en"]:
                lang = "en"
        template_path = (
            Path(settings.BASE_DIR)
            / "core"
            / "templates"
            / "core"
            / f"audit_report_template_{lang}.docx"
        )
        doc = DocxTemplate(template_path)
        _framework = self.get_object().framework
        tree = get_sorted_requirement_nodes(
            RequirementNode.objects.filter(framework=_framework).all(),
            RequirementAssessment.objects.filter(
                compliance_assessment=self.get_object()
            ).all(),
            _framework.max_score,
        )
        implementation_groups = self.get_object().selected_implementation_groups
        filter_graph_by_implementation_groups(tree, implementation_groups)
        context = gen_audit_context(pk, doc, tree, lang)
        doc.render(context)
        buffer_doc = io.BytesIO()
        doc.save(buffer_doc)
        buffer_doc.seek(0)

        response = StreamingHttpResponse(
            FileWrapper(buffer_doc),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = "attachment; filename=sales_report.docx"

        return response

    @action(detail=True, name="Get action plan CSV")
    def action_plan_csv(self, request, pk):
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, ComplianceAssessment
        )
        if UUID(pk) not in object_ids_view:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )
        compliance_assessment = ComplianceAssessment.objects.get(id=pk)
        requirement_assessments = compliance_assessment.get_requirement_assessments(
            include_non_assessable=False
        )
        queryset = AppliedControl.objects.filter(
            requirement_assessments__in=requirement_assessments
        ).distinct()

        # Use the same serializer to maintain consistency - to review
        serializer = ComplianceAssessmentActionPlanSerializer(
            queryset, many=True, context={"pk": pk}
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="action_plan_{pk}.csv"'

        writer = csv.writer(response)

        writer.writerow(
            [
                "Name",
                "Description",
                "Category",
                "CSF Function",
                "Priority",
                "Status",
                "ETA",
                "Expiry date",
                "Effort",
                "Impact",
                "Cost",
                "Covered requirements",
            ]
        )

        for item in serializer.data:
            writer.writerow(
                [
                    item.get("name"),
                    item.get("description"),
                    item.get("category"),
                    item.get("csf_function"),
                    item.get("priority"),
                    item.get("status"),
                    item.get("eta"),
                    item.get("expiry_date"),
                    item.get("effort"),
                    item.get("impact"),
                    item.get("cost"),
                    "\n".join(
                        [ra.get("str") for ra in item.get("requirement_assessments")]
                    ),
                ]
            )

        return response

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
        with optimized database operations for different scenarios.
        """
        baseline = serializer.validated_data.pop("baseline", None)
        create_applied_controls = serializer.validated_data.pop(
            "create_applied_controls_from_suggestions", False
        )

        with transaction.atomic():
            instance: ComplianceAssessment = serializer.save()
            instance.create_requirement_assessments(baseline)

            if baseline and baseline.framework == instance.framework:
                instance.show_documentation_score = baseline.show_documentation_score
                instance.save()

            # Handle different framework case
            elif baseline and baseline.framework != instance.framework:
                # Fetch mapping set and prefetch related data
                mapping_set = RequirementMappingSet.objects.select_related(
                    "source_framework", "target_framework"
                ).get(
                    target_framework=serializer.validated_data["framework"],
                    source_framework=baseline.framework,
                )

                # Compute results and get all affected requirement assessments
                computed_assessments = instance.compute_requirement_assessments_results(
                    mapping_set, baseline
                )

                # Collect all source requirement assessment IDs
                source_assessment_ids = [
                    assessment.mapping_inference["source_requirement_assessment"]["id"]
                    for assessment in computed_assessments
                ]

                # Fetch all baseline requirement assessments in one query
                baseline_assessments = {
                    str(ra.id): ra
                    for ra in RequirementAssessment.objects.filter(
                        id__in=source_assessment_ids
                    ).prefetch_related("evidences", "applied_controls")
                }

                # Prepare bulk updates
                updates = []
                m2m_operations = []

                for requirement_assessment in computed_assessments:
                    source_id = requirement_assessment.mapping_inference[
                        "source_requirement_assessment"
                    ]["id"]
                    baseline_ra = baseline_assessments[source_id]

                    # Update observation
                    requirement_assessment.observation = baseline_ra.observation
                    updates.append(requirement_assessment)

                    # Store M2M operations for later
                    m2m_operations.append(
                        (
                            requirement_assessment,
                            baseline_ra.evidences.all(),
                            baseline_ra.applied_controls.all(),
                        )
                    )

                # Bulk update observations
                if updates:
                    RequirementAssessment.objects.bulk_update(updates, ["observation"])

                # Handle M2M relationships in bulk
                for assessment, evidences, controls in m2m_operations:
                    assessment.evidences.add(*[ev.id for ev in evidences])
                    assessment.applied_controls.add(*[ac.id for ac in controls])

            # Handle applied controls creation
            if create_applied_controls:
                # Prefetch all requirement assessments with their suggestions
                assessments = instance.requirement_assessments.all().prefetch_related(
                    "requirement__reference_controls"
                )

                # Create applied controls in bulk for each assessment
                for requirement_assessment in assessments:
                    requirement_assessment.create_applied_controls_from_suggestions()

    def perform_update(self, serializer):
        compliance_assessment = serializer.save()
        if compliance_assessment.show_documentation_score:
            ra_null_documentation_score = RequirementAssessment.objects.filter(
                compliance_assessment=compliance_assessment,
                is_scored=True,
                documentation_score__isnull=True,
            )
            ra_null_documentation_score.update(
                documentation_score=compliance_assessment.min_score
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
                "show_documentation_score": compliance_assessment.show_documentation_score,
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
        assessable = self.request.query_params.get("assessable", False)
        requirement_assessments_objects = self.get_object().get_requirement_assessments(
            include_non_assessable=not assessable
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
                        if default_storage.exists(evidence.attachment.name):
                            zipf.writestr(
                                os.path.join(
                                    "evidences",
                                    os.path.basename(evidence.attachment.name),
                                ),
                                default_storage.open(evidence.attachment.name).read(),
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
        controls = []
        for requirement_assessment in requirement_assessments:
            controls.append(
                requirement_assessment.create_applied_controls_from_suggestions()
            )
        return Response(
            AppliedControlReadSerializer(chain.from_iterable(controls), many=True).data,
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="syncToActions",
    )
    def sync_to_applied_controls(self, request, pk):
        dry_run = request.query_params.get("dry_run", True)
        if dry_run == "false":
            dry_run = False
        compliance_assessment = ComplianceAssessment.objects.get(id=pk)

        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="change_requirementassessment"),
            folder=compliance_assessment.folder,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        changes = compliance_assessment.sync_to_applied_controls(dry_run=dry_run)
        return Response({"changes": changes})

    @action(detail=True, methods=["get"], url_path="progress_ts")
    def progress_ts(self, request, pk):
        try:
            raw = (
                HistoricalMetric.objects.filter(
                    model="ComplianceAssessment", object_id=pk
                )
                .annotate(progress=F("data__reqs__progress_perc"))
                .values("date", "progress")
                .order_by("date")
            )

            # Transform the data into the required format
            formatted_data = [
                [entry["date"].isoformat(), entry["progress"]] for entry in raw
            ]

            return Response({"data": formatted_data})

        except HistoricalMetric.DoesNotExist:
            return Response(
                {"error": "No metrics found for this assessment"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["get"])
    def threats_metrics(self, request, pk=None):
        compliance_assessment = self.get_object()

        # is this needed or overlapping with the IAM checks inherited?
        self.check_object_permissions(request, compliance_assessment)

        threat_metrics = compliance_assessment.get_threats_metrics()
        print(threat_metrics)
        if threat_metrics.get("total_unique_threats") == 0:
            return Response(threat_metrics, status=status.HTTP_200_OK)
        children = []
        for th in threat_metrics["threats"]:
            children.append(
                {
                    "name": th["name"],
                    "children": [
                        ra["requirement_name"] for ra in th["requirement_assessments"]
                    ],
                    "value": len(th["requirement_assessments"]),
                }
            )
        tree = {"name": "Threats", "children": children}
        nodes = []
        for th in threat_metrics["threats"]:
            nodes.append(
                {
                    "name": th["name"],
                    "value": len(th["requirement_assessments"]),
                    "items": [
                        f"{ra['requirement_name']} ({ra['result']})"
                        for ra in th["requirement_assessments"]
                    ],
                }
            )
        threat_metrics.update({"tree": tree, "graph": {"nodes": nodes}})

        return Response(threat_metrics, status=status.HTTP_200_OK)


class RequirementAssessmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows requirement assessments to be viewed or edited.
    """

    model = RequirementAssessment
    filterset_fields = [
        "folder",
        "folder__name",
        "evidences",
        "compliance_assessment",
        "applied_controls",
        "security_exceptions",
        "requirement__ref_id",
        "compliance_assessment__ref_id",
        "compliance_assessment__assets__ref_id",
    ]
    search_fields = ["requirement__name", "requirement__description"]

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
        controls = requirement_assessment.create_applied_controls_from_suggestions()
        return Response(
            AppliedControlReadSerializer(controls, many=True).data,
            status=status.HTTP_200_OK,
        )


class RequirementMappingSetViewSet(BaseModelViewSet):
    model = RequirementMappingSet

    filterset_fields = ["target_framework", "source_framework", "library__provider"]

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        providers = set(
            LoadedLibrary.objects.filter(
                provider__isnull=False, requirement_mapping_sets__isnull=False
            ).values_list("provider", flat=True)
        )
        return Response({p: p for p in providers})

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
    default_db_engine = settings.DATABASES["default"]["ENGINE"]
    if "postgresql" in default_db_engine:
        database_type = "P-FS"
    elif "sqlite" in default_db_engine:
        database_type = "S-FS"
    else:
        database_type = "Unknown"

    disk_info = get_disk_usage()

    if disk_info:
        total, used, free = disk_info
        disk_response = {
            "Disk space": f"{humanize.naturalsize(total)}",
            "Used": f"{humanize.naturalsize(used)} ({int((used / total) * 100)} %)",
        }
    else:
        disk_response = {
            "Disk space": "Unable to retrieve disk usage",
        }

    return Response(
        {
            "version": VERSION,
            "build": BUILD,
            **disk_response,
            "infrastructure": database_type,
        }
    )


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
        "impact",
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
            mtg.impact,
            mtg.cost,
            mtg.link,
            mtg.status,
        ]
        writer.writerow(row)

    return response


class SecurityExceptionViewSet(BaseModelViewSet):
    """
    API endpoint that allows security exceptions to be viewed or edited.
    """

    model = SecurityException
    filterset_fields = ["requirement_assessments", "risk_scenarios"]
    search_fields = ["name", "description", "ref_id"]

    @action(detail=False, name="Get severity choices")
    def severity(self, request):
        return Response(dict(Severity.choices))

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(SecurityException.Status.choices))


class FindingsAssessmentViewSet(BaseModelViewSet):
    model = FindingsAssessment
    filterset_fields = [
        "owner",
        "category",
        "perimeter",
        "folder",
        "authors",
        "status",
    ]
    search_fields = ["name", "description", "ref_id"]

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(FindingsAssessment.Status.choices))

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(FindingsAssessment.Category.choices))

    @action(detail=True, name="Get Follow up metrics")
    def metrics(self, request, pk=None):
        assessment = self.get_object()
        raw_metrics = assessment.get_findings_metrics()

        def format_severity_data(metrics):
            severity_colors = {
                "low": "#59BBB2",
                "medium": "#F5C481",
                "high": "#E6686D",
                "critical": "#C71E1D",
                "undefined": "#CCCCCC",
            }

            severity_chart_data = []
            for severity, count in metrics["severity_distribution"].items():
                severity_chart_data.append(
                    {
                        "name": severity.capitalize(),
                        "value": count,
                        "color": severity_colors.get(severity, "#CCCCCC"),
                    }
                )

            return severity_chart_data

        def format_status_data(metrics):
            status_mapping = {
                "identified": {"localName": "identified", "color": "#F5C481"},
                "confirmed": {"localName": "confirmed", "color": "#E6686D"},
                "assigned": {"localName": "assigned", "color": "#fab998"},
                "in_progress": {"localName": "inProgress", "color": "#fac858"},
                "mitigated": {"localName": "mitigated", "color": "#59BBB2"},
                "resolved": {"localName": "resolved", "color": "#59BBB2"},
                "dismissed": {"localName": "dismissed", "color": "#5470c6"},
                "deprecated": {"localName": "deprecated", "color": "#91cc75"},
                "--": {"localName": "undefined", "color": "#CCCCCC"},
            }

            grouped_status_counts = {}

            for status, count in metrics["status_distribution"].items():
                mapping_info = status_mapping.get(
                    status, {"localName": "other", "color": "#CCCCCC"}
                )
                local_name = mapping_info["localName"]
                color = mapping_info["color"]

                if local_name in grouped_status_counts:
                    grouped_status_counts[local_name]["value"] += count
                else:
                    grouped_status_counts[local_name] = {
                        "value": count,
                        "localName": local_name,
                        "itemStyle": {"color": color},
                    }

            status_values = list(grouped_status_counts.values())

            expected_statuses = ["open", "mitigate", "accept", "avoid", "transfer"]
            for status in expected_statuses:
                if not any(item["localName"] == status for item in status_values):
                    status_values.append(
                        {
                            "value": 0,
                            "localName": status,
                            "itemStyle": {"color": "#CCCCCC"},
                        }
                    )

            return {"values": status_values}

        formatted_metrics = {
            "raw_metrics": raw_metrics,
            "severity_chart_data": format_severity_data(raw_metrics),
            "status_chart_data": format_status_data(raw_metrics),
        }

        return Response(formatted_metrics)


class FindingViewSet(BaseModelViewSet):
    model = Finding
    filterset_fields = [
        "owner",
        "folder",
        "status",
        "findings_assessment",
        "filtering_labels",
        "applied_controls",
    ]

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(Finding.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get severity choices")
    def severity(self, request):
        return Response(dict(Severity.choices))


class IncidentViewSet(BaseModelViewSet):
    model = Incident
    search_fields = ["name", "description", "ref_id"]
    filterset_fields = ["folder", "status", "severity", "qualifications"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(Incident.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get severity choices")
    def severity(self, request):
        return Response(dict(Incident.Severity.choices))

    def perform_update(self, serializer):
        previous_instance = self.get_object()
        previous_status = previous_instance.status
        previous_severity = previous_instance.severity

        instance = serializer.save()

        if previous_status != instance.status and previous_status is not None:
            TimelineEntry.objects.create(
                incident=instance,
                entry=f"{previous_instance.get_status_display()}->{instance.get_status_display()}",
                entry_type=TimelineEntry.EntryType.STATUS_CHANGED,
                author=self.request.user,
                timestamp=now(),
            )

        if previous_severity != instance.severity and previous_severity is not None:
            TimelineEntry.objects.create(
                incident=instance,
                entry=f"{previous_instance.get_severity_display()}->{instance.get_severity_display()}",
                entry_type=TimelineEntry.EntryType.SEVERITY_CHANGED,
                author=self.request.user,
                timestamp=now(),
            )

        return super().perform_update(serializer)


class TimelineEntryViewSet(BaseModelViewSet):
    model = TimelineEntry
    filterset_fields = ["incident"]
    search_fields = ["entry", "entry_type"]
    ordering = ["-timestamp"]

    @action(detail=False, name="Get entry type choices")
    def entry_type(self, request):
        return Response(dict(TimelineEntry.EntryType.get_manual_entry_types()))

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        return

    def perform_destroy(self, instance):
        if instance.entry_type in [
            TimelineEntry.EntryType.SEVERITY_CHANGED,
            TimelineEntry.EntryType.STATUS_CHANGED,
        ]:
            raise ValidationError({"error": "cannotDeleteAutoTimelineEntry"})
        return super().perform_destroy(instance)


class TaskTemplateViewSet(BaseModelViewSet):
    model = TaskTemplate

    def task_calendar(self, task_templates, start=None, end=None):
        """Generate calendar of tasks for the given templates."""
        tasks_list = []
        for template in task_templates:
            if not template.is_recurrent:
                tasks_list.append(_create_task_dict(template, template.task_date))
                continue

            start_date_param = start or template.task_date or datetime.now().date()
            end_date_param = end or template.schedule.get("end_date")

            if not end_date_param:
                start_date = datetime.strptime(str(start_date_param), "%Y-%m-%d").date()
                end_date_param = (start_date + rd.relativedelta(months=1)).strftime(
                    "%Y-%m-%d"
                )

            try:
                start_date = datetime.strptime(str(start_date_param), "%Y-%m-%d").date()
                end_date = datetime.strptime(str(end_date_param), "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Invalid date format. Use YYYY-MM-DD"}

            tasks = _generate_occurrences(template, start_date, end_date)
            tasks_list.extend(tasks)

        processed_tasks_identifiers = set()  # Track tasks we've already processed

        # Sort tasks by due date
        sorted_tasks = sorted(tasks_list, key=lambda x: x["due_date"])

        # Process all past tasks and next 10 upcoming tasks
        current_date = datetime.now().date()

        # First separate past and future tasks
        past_tasks = [task for task in sorted_tasks if task["due_date"] <= current_date]
        next_tasks = [task for task in sorted_tasks if task["due_date"] > current_date]

        # Combined list of tasks to process (past and next 10)
        tasks_to_process = past_tasks + next_tasks

        # Directly modify tasks in the original tasks_list
        for i in range(len(tasks_list)):
            task = tasks_list[i]
            task_date = task["due_date"]
            task_template_id = task["task_template"]

            # Create a unique identifier for this task to avoid duplication
            task_identifier = (task_template_id, task_date)

            # Skip if we've already processed this task
            if task_identifier in processed_tasks_identifiers:
                continue

            # Check if this task should be processed (is in past or next 10)
            if task in tasks_to_process:
                processed_tasks_identifiers.add(task_identifier)

                # Get or create the TaskNode
                task_template = TaskTemplate.objects.get(id=task_template_id)
                task_node, created = TaskNode.objects.get_or_create(
                    task_template=task_template,
                    due_date=task_date,
                    defaults={
                        "status": "pending",
                        "folder": task_template.folder,
                    },
                )
                task_node.to_delete = False
                task_node.save(update_fields=["to_delete"])
                # Replace the task dictionary with the actual TaskNode in the original list
                tasks_list[i] = TaskNodeReadSerializer(task_node).data

        return tasks_list

    def _sync_task_nodes(self, task_template: TaskTemplate):
        if task_template.is_recurrent:
            with transaction.atomic():
                # Soft-delete all existing TaskNode instances associated with this TaskTemplate
                TaskNode.objects.filter(task_template=task_template).update(
                    to_delete=True
                )
                # Determine the end date based on the frequency
                start_date = task_template.task_date
                if task_template.is_recurrent:
                    if task_template.schedule["frequency"] == "DAILY":
                        delta = rd.relativedelta(months=2)
                    elif task_template.schedule["frequency"] == "WEEKLY":
                        delta = rd.relativedelta(months=4)
                    elif task_template.schedule["frequency"] == "MONTHLY":
                        delta = rd.relativedelta(years=1)
                    elif task_template.schedule["frequency"] == "YEARLY":
                        delta = rd.relativedelta(years=5)

                    end_date_param = task_template.schedule.get("end_date")
                    if end_date_param:
                        end_date = datetime.strptime(end_date_param, "%Y-%m-%d").date()
                    else:
                        end_date = datetime.now().date() + delta
                    # Ensure end_date is not before the calculated delta
                    if end_date < datetime.now().date() + delta:
                        end_date = datetime.now().date() + delta
                else:
                    end_date = start_date
                # Generate the task nodes
                self.task_calendar(
                    task_templates=TaskTemplate.objects.filter(id=task_template.id),
                    start=start_date,
                    end=end_date,
                )

                # garbage-collect
                TaskNode.objects.filter(to_delete=True).delete()

    @action(
        detail=False,
        name="Get tasks for the calendar",
        url_path="calendar/(?P<start>.+)/(?P<end>.+)",
    )
    def calendar(
        self,
        request,
        start=None,
        end=None,
    ):
        if start is None:
            start = timezone.now().date()
        if end is None:
            end = timezone.now().date() + relativedelta.relativedelta(months=1)
        return Response(
            self.task_calendar(
                task_templates=TaskTemplate.objects.filter(enabled=True),
                start=start,
                end=end,
            )
        )

    def perform_update(self, serializer):
        task_template = serializer.save()
        self._sync_task_nodes(task_template)

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._sync_task_nodes(serializer.instance)

    @action(detail=True, name="Get write data")
    def object(self, request, pk):
        serializer_class = self.get_serializer_class(action="update")
        self._sync_task_nodes(
            self.get_object()
        )  # Synchronize task nodes when fetching a task template
        return Response(serializer_class(super().get_object()).data)

    @action(detail=False, name="Get Task Node status choices")
    def status(srlf, request):
        return Response(dict(TaskNode.TASK_STATUS_CHOICES))


class TaskNodeViewSet(BaseModelViewSet):
    model = TaskNode
    filterset_fields = ["status", "task_template"]
    ordering = ["due_date"]

    @action(detail=False, name="Get Task Node status choices")
    def status(srlf, request):
        return Response(dict(TaskNode.TASK_STATUS_CHOICES))

    def perform_create(self, serializer):
        instance: TaskNode = serializer.save()
        instance.save()
        return super().perform_create(serializer)
