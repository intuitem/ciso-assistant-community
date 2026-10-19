from collections import deque
import io
import re
import uuid

from django.db import IntegrityError
from django.db.models import Prefetch
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment

from core.permissions import FeatureFlagRequired
from core.views import (
    BATCH_SIZE_LIMIT,
    BaseModelViewSet as AbstractBaseModelViewSet,
    ExportMixin,
    escape_excel_formula,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from core.serializers import RiskMatrixReadSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from iam.models import RoleAssignment, Folder, Permission
from core.models import AppliedControl, Asset
from .models import (
    BusinessImpactAnalysis,
    AssetAssessment,
    EscalationThreshold,
    DoraIncidentReport,
)
from .serializers import AssetAssessmentWriteSerializer

SHORT_CACHE_TTL = 2  # mn
MED_CACHE_TTL = 5  # mn
LONG_CACHE_TTL = 60  # mn


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "resilience.serializers"


def asset_dependency_graph(user, assessments):
    roots = {aa.asset_id for aa in assessments}
    extra = {(d.id, aa.asset_id) for aa in assessments for d in aa.dependencies.all()}
    starts = list(Asset.objects.filter(id__in=roots | {d for d, _ in extra}))
    tree = Asset._prefetch_graph_data(starts)["parent_to_children"]
    reachable = {d for d, _ in extra} | {
        d.id for a in starts for d in Asset._get_all_descendants(a, tree)
    }
    ids = (roots | reachable) & set(RoleAssignment.get_viewable_object_ids(user, Asset))
    kids = {}
    for parent, children in tree.items():
        kids.setdefault(parent.id, set()).update(c.id for c in children)
    for child, parent in extra:
        kids.setdefault(parent, set()).add(child)
    depth = dict.fromkeys(roots, 0)
    queue = deque(roots)
    while queue:
        current = queue.popleft()
        step = depth[current] + 1
        for child in kids.get(current, ()):
            if depth.get(child, -1) < step <= len(reachable):
                depth[child] = step
                queue.append(child)
    roots &= ids
    graph = Asset._prefetch_graph_data(list(Asset.objects.filter(id__in=ids)))
    c2p, p2c = graph["child_to_parents"], graph["parent_to_children"]
    linked = {x.id for m in graph.values() for k, v in m.items() for x in (k, *v)}
    by_id = {
        a.id: a
        for a in Asset.objects.filter(id__in=ids | linked)
        .select_related("folder")
        .prefetch_related("overridden_children_capabilities")
    }

    def evaluate(a):
        if a.is_primary:
            supporting = {
                by_id[x.id]
                for x in Asset._get_all_descendants(a, p2c)
                if not x.is_primary
            }
            so = a.security_objectives.get("objectives", {})
            ro = a.disaster_recovery_objectives.get("objectives", {})
            sc = Asset._aggregate_security_capabilities(
                supporting, parent_to_children=p2c
            )
            rc = Asset._aggregate_recovery_capabilities(
                supporting, parent_to_children=p2c
            )
        else:
            primaries = {x for x in Asset._get_all_ancestors(a, c2p) if x.is_primary}
            so = Asset._aggregate_security_objectives(primaries)
            ro = Asset._aggregate_dro_objectives(primaries)
            sc = a.security_capabilities.get("objectives", {})
            rc = a.recovery_capabilities.get("objectives", {})
        comparisons = [
            (c, so, sc)
            for c in a.get_security_objectives_comparison(
                {"objectives": so}, {"objectives": sc}
            )
        ] + [
            (c, ro, rc)
            for c in a.get_recovery_objectives_comparison(
                {"objectives": ro}, {"objectives": rc}, [], []
            )
        ]
        gaps = [
            {
                "objective": c["objective"],
                "expected": exp[c["objective"]]["value"],
                "actual": act[c["objective"]]["value"],
            }
            for c, exp, act in comparisons
            if c["verdict"] is False
        ]
        return gaps, any(c["verdict"] is not None for c, _, _ in comparisons)

    assets = [by_id[i] for i in ids]
    results = {a.id: evaluate(a) for a in assets}
    causes = {a.id for a in assets if not a.is_primary and results[a.id][0]}

    regular = {
        (child.id, parent.id)
        for parent, children in p2c.items()
        if parent.id in ids
        for child in children
        if child.id in ids
    }
    extra = {(c, p) for c, p in extra if c in ids and p in ids} - regular

    nodes = []
    for a in assets:
        gaps, checked = results[a.id]
        below = (
            []
            if a.is_primary and not gaps
            else sorted(
                str(d.id) for d in Asset._get_all_descendants(a, p2c) if d.id in causes
            )
        )
        if a.id in causes:
            state = "cause"
        elif (a.is_primary and gaps) or (not a.is_primary and below):
            state = "impacted"
        else:
            state = "ok" if checked else "none"
        nodes.append(
            {
                "id": str(a.id),
                "label": a.name,
                "type": a.type,
                "domain": str(a.folder_id),
                "domain_name": a.folder.name,
                "depth": depth.get(a.id, 0),
                "status": state,
                "gaps": gaps,
                "causes": below,
            }
        )

    links = [
        {"source": str(c), "target": str(p), "extra": (c, p) in extra}
        for c, p in regular | extra
    ]
    return {"roots": [str(r) for r in roots], "nodes": nodes, "links": links}


class BusinessImpactAnalysisViewSet(BaseModelViewSet, ExportMixin):
    model = BusinessImpactAnalysis
    filterset_fields = [
        "folder",
        "perimeter",
        "perimeter__folder",
        "authors",
        "risk_matrix",
        "status",
    ]

    export_config = {
        "fields": {
            "internal_id": {
                "source": "id",
                "label": "internal_id",
                "format": lambda v: str(v),
            },
            "name": {"source": "name", "label": "name", "escape": True},
            "description": {
                "source": "description",
                "label": "description",
                "escape": True,
            },
            "perimeter": {
                "source": "perimeter.name",
                "label": "perimeter",
                "escape": True,
            },
            "perimeter_ref_id": {
                "source": "perimeter.ref_id",
                "label": "perimeter_ref_id",
                "escape": True,
            },
            "risk_matrix": {
                "source": "risk_matrix.name",
                "label": "risk_matrix",
                "escape": True,
            },
            "risk_matrix_ref_id": {
                "source": "risk_matrix.ref_id",
                "label": "risk_matrix_ref_id",
                "escape": True,
            },
            "folder": {
                "source": "folder.name",
                "label": "folder",
                "escape": True,
            },
            "version": {
                "source": "version",
                "label": "version",
            },
            "status": {
                "source": "get_status_display",
                "label": "status",
            },
            "eta": {
                "source": "eta",
                "label": "eta",
            },
            "due_date": {
                "source": "due_date",
                "label": "due_date",
            },
            "observation": {
                "source": "observation",
                "label": "observation",
                "escape": True,
            },
            "authors": {
                "source": "authors",
                "label": "authors",
                "format": lambda qs: ",".join(
                    escape_excel_formula(str(a)) for a in qs.all()
                ),
            },
            "reviewers": {
                "source": "reviewers",
                "label": "reviewers",
                "format": lambda qs: ",".join(
                    escape_excel_formula(str(r)) for r in qs.all()
                ),
            },
        },
        "asset_assessment_fields": {
            "bia_name": {
                "source": "bia.name",
                "label": "bia_name",
                "escape": True,
            },
            "asset": {
                "source": "asset.name",
                "label": "asset",
                "escape": True,
            },
            "asset_ref_id": {
                "source": "asset.ref_id",
                "label": "asset_ref_id",
                "escape": True,
            },
            "recovery_documented": {
                "source": "recovery_documented",
                "label": "recovery_documented",
            },
            "recovery_tested": {
                "source": "recovery_tested",
                "label": "recovery_tested",
            },
            "recovery_targets_met": {
                "source": "recovery_targets_met",
                "label": "recovery_targets_met",
            },
            "dependencies": {
                "source": "dependencies",
                "label": "dependencies",
                "format": lambda qs: ",".join(
                    escape_excel_formula(o.name) for o in qs.all()
                ),
            },
            "associated_controls": {
                "source": "associated_controls",
                "label": "associated_controls",
                "format": lambda qs: ",".join(
                    escape_excel_formula(o.name) for o in qs.all()
                ),
            },
            "evidences": {
                "source": "evidences",
                "label": "evidences",
                "format": lambda qs: ",".join(
                    escape_excel_formula(o.name) for o in qs.all()
                ),
            },
            "observation": {
                "source": "observation",
                "label": "observation",
                "escape": True,
            },
        },
        "threshold_fields": {
            "bia_name": {
                "source": "asset_assessment.bia.name",
                "label": "bia_name",
                "escape": True,
            },
            "asset": {
                "source": "asset_assessment.asset.name",
                "label": "asset",
                "escape": True,
            },
            "asset_ref_id": {
                "source": "asset_assessment.asset.ref_id",
                "label": "asset_ref_id",
                "escape": True,
            },
            "point_in_time": {
                "source": "point_in_time",
                "label": "point_in_time",
            },
            "quali_impact": {
                "source": "quali_impact",
                "label": "quali_impact",
            },
            "quanti_impact": {
                "source": "quanti_impact",
                "label": "quanti_impact",
            },
            "quanti_impact_unit": {
                "source": "quanti_impact_unit",
                "label": "quanti_impact_unit",
            },
            "qualifications": {
                "source": "qualifications",
                "label": "qualifications",
                "format": lambda qs: ",".join(
                    escape_excel_formula(o.name) for o in qs.all()
                ),
            },
            "justification": {
                "source": "justification",
                "label": "justification",
                "escape": True,
            },
        },
        "wrap_columns": ["name", "description", "observation"],
        "filename": "business_impact_analysis_export",
        "select_related": ["folder", "perimeter", "risk_matrix"],
        "prefetch_related": ["authors", "reviewers"],
    }

    def _build_bia_workbook(self, queryset) -> Workbook:
        wb = Workbook()
        wb.remove(wb.active)

        summary_ws = wb.create_sheet(title="Summary")
        main_fields = self.export_config["fields"]
        main_headers = [f.get("label", name) for name, f in main_fields.items()]
        summary_ws.append(main_headers)

        wrap_alignment = Alignment(wrap_text=True, vertical="top")
        wrap_columns = self.export_config.get("wrap_columns", ["name", "description"])

        used_sheet_names = {"Summary"}
        assessment_fields = self.export_config.get("asset_assessment_fields", {})
        threshold_fields = self.export_config.get("threshold_fields", {})

        def _make_sheet_name(base_name: str, suffix: str = "") -> str:
            invalid_chars = r"[\\/\?\*\[\]:]"
            base_name = re.sub(invalid_chars, "", base_name)
            max_len = max(1, 31 - len(suffix))
            sheet_name = f"{base_name[:max_len]}{suffix}"[:31]
            counter = 1
            while sheet_name in used_sheet_names:
                counter_suffix = f" ({counter})"
                max_len = max(1, 31 - len(suffix) - len(counter_suffix))
                sheet_name = (f"{base_name[:max_len]}{suffix}{counter_suffix}")[:31]
                counter += 1
            used_sheet_names.add(sheet_name)
            return sheet_name

        for bia in queryset:
            row = [
                self._resolve_field_value(bia, field_config)
                for field_config in main_fields.values()
            ]
            summary_ws.append(row)

            asset_assessments = (
                AssetAssessment.objects.filter(bia=bia)
                .select_related("asset", "asset__folder", "folder", "bia")
                .prefetch_related("dependencies", "associated_controls", "evidences")
                .order_by("asset__name")
            )

            if asset_assessments.exists():
                base_name = bia.name or f"BIA_{bia.pk}"
                assessment_sheet_name = _make_sheet_name(base_name)

                assessment_ws = wb.create_sheet(title=assessment_sheet_name)
                assessment_headers = [
                    f.get("label", name) for name, f in assessment_fields.items()
                ]
                assessment_ws.append(assessment_headers)

                for assessment in asset_assessments:
                    assessment_row = [
                        self._resolve_field_value(assessment, field_config)
                        for field_config in assessment_fields.values()
                    ]
                    assessment_ws.append(assessment_row)

                for col_idx, header in enumerate(assessment_headers, 1):
                    if header.lower() in wrap_columns:
                        for row_idx in range(1, assessment_ws.max_row + 1):
                            assessment_ws.cell(
                                row=row_idx, column=col_idx
                            ).alignment = wrap_alignment

            thresholds = (
                EscalationThreshold.objects.filter(asset_assessment__bia=bia)
                .select_related(
                    "asset_assessment",
                    "asset_assessment__asset",
                    "asset_assessment__bia",
                )
                .prefetch_related("qualifications")
                .order_by("asset_assessment__asset__name", "point_in_time")
            )

            if thresholds.exists():
                base_name = bia.name or f"BIA_{bia.pk}"
                threshold_sheet_name = _make_sheet_name(base_name, " - thresholds")

                threshold_ws = wb.create_sheet(title=threshold_sheet_name)
                threshold_headers = [
                    f.get("label", name) for name, f in threshold_fields.items()
                ]
                threshold_ws.append(threshold_headers)

                for threshold in thresholds:
                    threshold_row = [
                        self._resolve_field_value(threshold, field_config)
                        for field_config in threshold_fields.values()
                    ]
                    threshold_ws.append(threshold_row)

                for col_idx, header in enumerate(threshold_headers, 1):
                    if header.lower() in wrap_columns:
                        for row_idx in range(1, threshold_ws.max_row + 1):
                            threshold_ws.cell(
                                row=row_idx, column=col_idx
                            ).alignment = wrap_alignment

        for col_idx, header in enumerate(main_headers, 1):
            if header.lower() in wrap_columns:
                for row_idx in range(1, summary_ws.max_row + 1):
                    summary_ws.cell(
                        row=row_idx, column=col_idx
                    ).alignment = wrap_alignment

        return wb

    @action(detail=False, name="Export BIAs with assessments and thresholds")
    def export_xlsx(self, request):
        if not self.export_config:
            return HttpResponse(
                status=501, content="Export not configured for this model"
            )

        wb = self._build_bia_workbook(self._get_export_queryset())

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"{self.export_config.get('filename', 'export')}_multi_sheet.xlsx"
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["get"], name="Export BIA as Excel")
    def xlsx(self, request, pk):
        if not self.export_config:
            return HttpResponse(
                status=501, content="Export not configured for this model"
            )

        bia = self.get_object()
        wb = self._build_bia_workbook(BusinessImpactAnalysis.objects.filter(pk=bia.pk))

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"bia-{pk}.xlsx"
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, name="Get dependency graph", url_path="dependency-graph")
    def dependency_graph(self, request, pk):
        assessments = AssetAssessment.objects.filter(
            bia=self.get_object(),
            id__in=RoleAssignment.get_viewable_object_ids(
                request.user, AssetAssessment
            ),
        ).prefetch_related("dependencies")
        return Response(asset_dependency_graph(request.user, list(assessments)))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(BusinessImpactAnalysis.Status.choices))

    @action(detail=True, name="Get the BIA metrics")
    def metrics(self, request, pk):
        bia = self.get_object()
        return Response(bia.metrics())

    @action(detail=True, name="Build qualitative table", url_path="build-table")
    def impact_table(self, request, pk):
        bia = self.get_object()
        table = bia.build_table()
        return Response(table)


class AssetAssessmentViewSet(BaseModelViewSet):
    model = AssetAssessment
    filterset_fields = ["bia", "asset"]
    search_fields = ["bia__name", "asset__name"]
    ordering = ["asset"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("bia", "asset", "asset__folder")
            .prefetch_related(
                "dependencies",
                "evidences",
                # Serialized with its folder: join it in the prefetch query.
                Prefetch(
                    "associated_controls",
                    queryset=AppliedControl.objects.select_related("folder"),
                ),
            )
        )

    @action(detail=False, methods=["post"], url_path="batch-create")
    def batch_create(self, request):
        bia_id = request.data.get("bia")
        asset_ids = request.data.get("assets", [])
        if not bia_id:
            return Response(
                {"error": "bia is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not isinstance(asset_ids, list) or not asset_ids:
            return Response(
                {"error": "assets is required and must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(asset_ids) > BATCH_SIZE_LIMIT:
            return Response(
                {"error": "too many assets", "max": BATCH_SIZE_LIMIT},
                status=status.HTTP_400_BAD_REQUEST,
            )

        viewable_bias = RoleAssignment.get_viewable_object_ids(
            request.user, BusinessImpactAnalysis
        )
        try:
            bia = BusinessImpactAnalysis.objects.filter(id__in=viewable_bias).get(
                id=uuid.UUID(str(bia_id))
            )
        except ValueError, AttributeError, BusinessImpactAnalysis.DoesNotExist:
            return Response(
                {"error": "BIA not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if bia.is_locked:
            return Response(
                {"error": "lockedAssessment"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_assetassessment"),
            folder=bia.folder,
        ):
            return Response(
                {"error": "permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        viewable_assets = RoleAssignment.get_viewable_object_ids(request.user, Asset)
        viewable_asset_ids = {str(a) for a in viewable_assets}

        existing_assets = {
            str(a)
            for a in AssetAssessment.objects.filter(bia=bia).values_list(
                "asset_id", flat=True
            )
        }
        created = 0
        skipped = 0
        errors = []
        for asset_id in dict.fromkeys(str(a) for a in asset_ids):
            if asset_id in existing_assets:
                skipped += 1
                continue
            if asset_id not in viewable_asset_ids:
                errors.append({"asset": asset_id, "error": "asset not found"})
                continue
            serializer = AssetAssessmentWriteSerializer(
                data={"asset": asset_id, "bia": str(bia.id)},
                context={"request": request},
            )
            if not serializer.is_valid():
                errors.append({"asset": asset_id, "errors": serializer.errors})
                continue
            try:
                serializer.save()
            except IntegrityError:
                skipped += 1
                continue
            except PermissionDenied:
                errors.append({"asset": asset_id, "error": "permission denied"})
                continue
            created += 1

        return Response(
            {
                "success": created > 0 or skipped > 0,
                "created": created,
                "skipped": skipped,
                "errors": errors,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, name="Get risk matrix", url_path="risk-matrix")
    def risk_matrix(self, request, pk=None):
        aa = self.get_object()
        return Response(RiskMatrixReadSerializer(aa.bia.risk_matrix).data)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get impact choices")
    def quali_impact(self, request, pk):
        aa = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in aa.bia.parsed_matrix["impact"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)

    @action(detail=True, name="Get the asset assessment details")
    def metrics(self, request, pk):
        res = self.get_object().metrics()
        return Response(res)

    @action(detail=True, name="Get dependency graph", url_path="dependency-graph")
    def dependency_graph(self, request, pk):
        return Response(asset_dependency_graph(request.user, [self.get_object()]))


class EscalationThresholdViewSet(BaseModelViewSet):
    model = EscalationThreshold
    filterset_fields = ["asset_assessment", "quali_impact"]
    ordering = ["point_in_time"]

    @action(detail=True, name="Get risk matrix", url_path="risk-matrix")
    def risk_matrix(self, request, pk=None):
        et = self.get_object()
        return Response(RiskMatrixReadSerializer(et.risk_matrix).data)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get quantification units")
    def quant_unit(self, request):
        return Response(dict(EscalationThreshold.QUANT_IMPACT_UNIT))

    @action(detail=True, name="Get impact choices")
    def quali_impact(self, request, pk):
        escalation_threshold = self.get_object()
        undefined_choice = {-1: "--"}
        impact_choices = dict(
            enumerate(
                impact["name"]
                for impact in escalation_threshold.parsed_matrix["impact"]
            )
        )
        choices = undefined_choice | impact_choices
        return Response(choices)


class DoraIncidentReportViewSet(BaseModelViewSet):
    model = DoraIncidentReport
    feature_flag = "dora"
    permission_classes = BaseModelViewSet.permission_classes + [FeatureFlagRequired]
    filterset_fields = ["incident", "incident_submission", "folder"]
    search_fields = ["incident__name", "incident_description"]

    @action(detail=False, name="Get main entity data for pre-fill")
    def main_entity(self, request):
        from tprm.models import Entity

        entity = Entity.get_main_entity()
        if not entity:
            return Response({})
        return Response(
            {
                "id": str(entity.id),
                "name": entity.name,
                "currency": entity.currency,
                "dora_competent_authority": entity.dora_competent_authority,
                "dora_entity_type": entity.dora_entity_type,
                "legal_identifiers": entity.legal_identifiers or {},
            }
        )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get submission type choices")
    def incident_submission(self, request):
        return Response(dict(DoraIncidentReport.SubmissionType.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get incident discovery choices")
    def incident_discovery(self, request):
        from core.dora import DORA_IR_INCIDENT_DISCOVERY_CHOICES

        return Response(dict(DORA_IR_INCIDENT_DISCOVERY_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get report currency choices")
    def report_currency(self, request):
        from core.dora import DORA_IR_CURRENCY_CHOICES

        return Response(dict(DORA_IR_CURRENCY_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get classification criterion choices")
    def classification_criterion(self, request):
        from core.dora import DORA_IR_CLASSIFICATION_CRITERION_CHOICES

        return Response(dict(DORA_IR_CLASSIFICATION_CRITERION_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get incident classification choices")
    def incident_classification(self, request):
        from core.dora import DORA_IR_INCIDENT_CLASSIFICATION_CHOICES

        return Response(dict(DORA_IR_INCIDENT_CLASSIFICATION_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get threat techniques choices")
    def threat_techniques(self, request):
        from core.dora import DORA_IR_THREAT_TECHNIQUES_CHOICES

        return Response(dict(DORA_IR_THREAT_TECHNIQUES_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get root cause high-level choices")
    def root_cause_hl(self, request):
        from core.dora import DORA_IR_ROOT_CAUSE_HL_CHOICES

        return Response(dict(DORA_IR_ROOT_CAUSE_HL_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get root cause detailed choices")
    def root_cause_detailed(self, request):
        from core.dora import DORA_IR_ROOT_CAUSE_DETAILED_CHOICES

        return Response(dict(DORA_IR_ROOT_CAUSE_DETAILED_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get root cause additional choices")
    def root_cause_additional(self, request):
        from core.dora import DORA_IR_ROOT_CAUSE_ADDITIONAL_CHOICES

        return Response(dict(DORA_IR_ROOT_CAUSE_ADDITIONAL_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get reporting authority choices")
    def reporting_authority(self, request):
        from core.dora import DORA_IR_REPORTING_AUTHORITY_CHOICES

        return Response(dict(DORA_IR_REPORTING_AUTHORITY_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get downtime info actual/estimate choices")
    def info_duration_service_downtime_actual_or_estimate(self, request):
        choices = [
            ("actual_figures", "Actual figures"),
            ("estimates", "Estimates"),
            ("actual_figures_and_estimates", "Actual figures and estimates"),
            ("no_information_available", "No information available"),
        ]
        return Response(dict(choices))

    @action(detail=True, methods=["get"], name="Export DORA IR JSON")
    def export_json(self, request, pk):
        from resilience.dora_ir_export import build_dora_ir_json

        report = self.get_object()
        data = build_dora_ir_json(report)
        from django.http import JsonResponse
        from django.utils.text import slugify

        response = JsonResponse(data, json_dumps_params={"indent": 2})
        safe_name = slugify(report.incident.name) or "dora-ir"
        response["Content-Disposition"] = (
            f'attachment; filename="{safe_name}_dora_ir.json"'
        )
        return response

    @action(detail=True, methods=["get"], name="Validate DORA IR")
    def validate_report(self, request, pk):
        from resilience.dora_ir_export import build_dora_ir_json, validate_dora_ir

        report = self.get_object()
        data = build_dora_ir_json(report)
        errors = validate_dora_ir(data)
        return Response({"valid": len(errors) == 0, "errors": errors})
