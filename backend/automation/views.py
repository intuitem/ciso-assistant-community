import csv
import io
import json
import re
import uuid
from collections import Counter
from uuid import UUID

from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Min, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from core.models import Asset, Finding, RequirementNode
from core.views import (
    BaseModelViewSet as AbstractBaseModelViewSet,
    escape_excel_formula,
)
from iam.models import Folder, RoleAssignment

from .importers import ImportError_, analyze_csv, parse_file, parse_mapped_csv
from .models import PostureAssessment, PostureResult, PostureRun

LONG_CACHE_TTL = 60  # mn
MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "automation.serializers"


class PostureAssessmentViewSet(BaseModelViewSet):
    model = PostureAssessment
    filterset_fields = [
        "name",
        "ref_id",
        "perimeter",
        "folder",
        "authors",
        "status",
        "framework",
        "assets",
    ]
    search_fields = ["name", "description", "ref_id"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("folder", "perimeter", "framework")
            .prefetch_related("assets", "authors")
        )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(PostureAssessment.Status.choices))

    def _viewable_asset_ids(self):
        (ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, Asset
        )
        return ids

    @staticmethod
    def _locked(assessment):
        if assessment.is_locked:
            return Response(
                {"error": "assessment is locked"}, status=status.HTTP_400_BAD_REQUEST
            )
        return None

    @staticmethod
    def _row_payload(row):
        return {
            "id": str(row["id"]),
            "requirement": {
                "id": str(row["requirement_id"]),
                "ref_id": row["requirement__ref_id"],
                "name": row["requirement__name"],
            },
            "asset": {
                "id": str(row["asset_id"]),
                "str": f"{row['asset__folder__name']}/{row['asset__name']}",
            },
            "result": row["result"],
            "timestamp": row["timestamp"],
            "run_id": str(row["run_id"]),
            "tool": row["run__tool"],
            "actual": row["actual"],
            "expected": row["expected"],
            "message": row["message"],
        }

    @action(detail=True, methods=["get"])
    def posture(self, request, pk=None):
        assessment = self.get_object()
        rows = assessment.current_posture(asset_ids=self._viewable_asset_ids())
        counts = Counter(row["result"] for row in rows)
        applicable = counts["pass"] + counts["fail"]
        score = round(100 * counts["pass"] / applicable, 1) if applicable else None
        selected_ids = assessment.selected_requirement_ids()
        if selected_ids is not None:
            total_checks = (
                RequirementNode.objects.filter(id__in=selected_ids)
                .exclude(ref_id="")
                .exclude(ref_id=None)
                .count()
            )
        else:
            total_checks = (
                RequirementNode.objects.filter(
                    framework=assessment.framework, assessable=True
                )
                .exclude(ref_id="")
                .exclude(ref_id=None)
                .count()
            )
        return Response(
            {
                "score": score,
                "total_checks": total_checks,
                "results": [self._row_payload(row) for row in rows],
            }
        )

    @staticmethod
    def _asset_param(request):
        asset_id = request.query_params.get("asset")
        if not asset_id:
            return None, None
        try:
            return UUID(str(asset_id)), None
        except ValueError:
            return None, Response(
                {"error": "asset must be a valid UUID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def tree(self, request, pk=None):
        assessment = self.get_object()
        asset_id, error = self._asset_param(request)
        if error:
            return error

        rows = assessment.current_posture(
            asset_id=asset_id, asset_ids=self._viewable_asset_ids()
        )
        counts_by_requirement = {}
        row_by_requirement = {}
        for r in rows:
            counts_by_requirement.setdefault(r["requirement_id"], Counter())[
                r["result"]
            ] += 1
            if asset_id:
                row_by_requirement[r["requirement_id"]] = r

        nodes = list(RequirementNode.objects.filter(framework=assessment.framework))
        children = {}
        for node in nodes:
            children.setdefault(node.parent_urn, []).append(node)
        for siblings in children.values():
            siblings.sort(
                key=lambda n: (
                    n.order_id is None,
                    n.order_id if n.order_id is not None else n.created_at,
                )
            )

        ig_active = bool(assessment.selected_implementation_groups)

        def serialize(node):
            entry = {
                "id": str(node.id),
                "urn": node.urn,
                "ref_id": node.ref_id,
                "name": node.name,
                "description": node.description,
                "assessable": node.assessable,
                "counts": dict(counts_by_requirement.get(node.id, {})),
                "children": [
                    child
                    for child in (serialize(c) for c in children.get(node.urn, []))
                    if child is not None
                ],
            }
            if ig_active:
                own_match = (
                    node.assessable
                    and assessment.requirement_matches_selected_groups(
                        node.implementation_groups
                    )
                )
                if not own_match and not entry["children"]:
                    return None
            for child in entry["children"]:
                for result, count in child["counts"].items():
                    entry["counts"][result] = entry["counts"].get(result, 0) + count
            row = row_by_requirement.get(node.id)
            if row:
                entry["current"] = {
                    "result": row["result"],
                    "timestamp": row["timestamp"],
                    "run_id": str(row["run_id"]),
                    "actual": row["actual"],
                    "expected": row["expected"],
                    "message": row["message"],
                }
            return entry

        return Response(
            {
                "tree": [
                    entry
                    for entry in (serialize(n) for n in children.get(None, []))
                    if entry is not None
                ],
                "assets": [
                    {"id": str(a.id), "str": f"{a.folder.name}/{a.name}"}
                    for a in assessment.assets.filter(id__in=self._viewable_asset_ids())
                    .select_related("folder")
                    .order_by("folder__name", "name")
                ],
            }
        )

    @action(detail=True, methods=["get"])
    def runs(self, request, pk=None):
        assessment = self.get_object()
        asset_id, error = self._asset_param(request)
        if error:
            return error
        qs = assessment.results.filter(asset_id__in=self._viewable_asset_ids())
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        runs = (
            qs.values("run_id", "run__started_at", "run__tool")
            .annotate(
                timestamp=Min("timestamp"),
                source=Max("source"),
                checks=Count("id"),
                passed=Count("id", filter=Q(result="pass")),
                failed=Count("id", filter=Q(result="fail")),
                errors=Count("id", filter=Q(result="error")),
                assets=Count("asset_id", distinct=True),
            )
            .order_by("run__started_at")
        )
        return Response(
            {
                "runs": [
                    {
                        "run_id": str(run["run_id"]),
                        "started_at": run["run__started_at"],
                        "tool": run["run__tool"],
                        "timestamp": run["timestamp"],
                        "source": run["source"],
                        "checks": run["checks"],
                        "passed": run["passed"],
                        "failed": run["failed"],
                        "errors": run["errors"],
                        "assets": run["assets"],
                    }
                    for run in runs
                ]
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path=r"runs/(?P<run_id>[0-9a-f-]{36})",
    )
    def run_detail(self, request, pk=None, run_id=None):
        assessment = self.get_object()
        run = PostureRun.objects.filter(
            id=run_id, posture_assessment=assessment
        ).first()
        if run is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        rows = list(
            run.results.filter(asset_id__in=self._viewable_asset_ids())
            .values(
                "id",
                "requirement_id",
                "asset_id",
                "result",
                "timestamp",
                "run_id",
                "run__tool",
                "source",
                "actual",
                "expected",
                "message",
                "requirement__ref_id",
                "requirement__name",
                "asset__name",
                "asset__folder__name",
            )
            .order_by("asset__folder__name", "asset__name", "requirement__ref_id")
        )
        counts = Counter(row["result"] for row in rows)
        return Response(
            {
                "run": {
                    "run_id": str(run.id),
                    "started_at": run.started_at,
                    "tool": run.tool,
                    "source": rows[0]["source"] if rows else "",
                    "checks": len(rows),
                    "passed": counts["pass"],
                    "failed": counts["fail"],
                    "errors": counts["error"],
                    "assets": len({row["asset_id"] for row in rows}),
                },
                "results": [
                    {**self._row_payload(row), "source": row["source"]} for row in rows
                ],
            }
        )

    @action(detail=True, methods=["get"])
    def trend(self, request, pk=None):
        assessment = self.get_object()
        asset_id, error = self._asset_param(request)
        if error:
            return error
        qs = assessment.results.filter(asset_id__in=self._viewable_asset_ids())
        if asset_id:
            qs = qs.filter(asset_id=asset_id)
        selected_ids = assessment.selected_requirement_ids()
        if selected_ids is not None:
            qs = qs.filter(requirement_id__in=selected_ids)
        rows = qs.order_by("timestamp", "created_at").values(
            "asset_id", "requirement_id", "result", "run_id", "timestamp", "run__tool"
        )
        latest = {}
        points = []
        current_run = None
        current_ts = None
        current_tool = ""

        def snapshot():
            counts = Counter(latest.values())
            applicable = counts["pass"] + counts["fail"]
            score = round(100 * counts["pass"] / applicable, 1) if applicable else None
            return {
                "run_id": str(current_run),
                "timestamp": current_ts,
                "tool": current_tool,
                "score": score,
                "counts": dict(counts),
            }

        for row in rows:
            if current_run is not None and row["run_id"] != current_run:
                points.append(snapshot())
            current_run = row["run_id"]
            current_ts = row["timestamp"]
            current_tool = row["run__tool"]
            latest[(row["asset_id"], row["requirement_id"])] = row["result"]
        if current_run is not None:
            points.append(snapshot())
        return Response({"points": points})

    @action(detail=True, methods=["post"], url_path="upload-results")
    def upload_results(self, request, pk=None):
        assessment = self.get_object()
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="change_postureassessment"),
            folder=assessment.folder,
        ):
            raise PermissionDenied()
        locked = self._locked(assessment)
        if locked:
            return locked
        return self._ingest(
            request,
            assessment,
            asset_id=request.data.get("asset"),
            entries=request.data.get("results"),
            run_id=request.data.get("run_id"),
            source=request.data.get("source", PostureResult.Source.API),
            tool=request.data.get("tool", ""),
        )

    def _ingest(self, request, assessment, *, asset_id, entries, run_id, source, tool):
        if not asset_id or not isinstance(entries, list) or not entries:
            return Response(
                {"error": "asset and a non-empty results list are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not all(isinstance(e, dict) for e in entries):
            return Response(
                {"error": "results entries must be objects"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            asset_id = UUID(str(asset_id))
        except TypeError, ValueError:
            return Response(
                {"error": "asset must be a valid UUID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset = assessment.assets.filter(id=asset_id).first()
        enrolled = False
        if asset is None:
            asset = Asset.objects.filter(id=asset_id).first()
            if asset is None or not RoleAssignment.is_access_allowed(
                user=request.user,
                perm=Permission.objects.get(codename="view_asset"),
                folder=asset.folder if asset else assessment.folder,
            ):
                return Response(
                    {"error": "unknown asset", "asset": asset_id},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            assessment.assets.add(asset)
            enrolled = True

        valid_results = set(PostureResult.Result.values)
        invalid = [
            e.get("ref_id") for e in entries if e.get("result") not in valid_results
        ]
        if invalid:
            return Response(
                {"error": "invalid result values", "ref_ids": invalid},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if run_id:
            try:
                run_id = UUID(str(run_id))
            except ValueError:
                return Response(
                    {"error": "run_id must be a valid UUID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if (
                PostureRun.objects.filter(id=run_id)
                .exclude(posture_assessment=assessment)
                .exists()
            ):
                return Response(
                    {"error": "run_id belongs to another assessment"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if source not in PostureResult.Source.values:
            return Response(
                {"error": "invalid source"}, status=status.HTTP_400_BAD_REQUEST
            )

        timestamp = timezone.now()

        nodes = {
            node.ref_id: node
            for node in RequirementNode.objects.filter(
                framework=assessment.framework, assessable=True
            )
            if node.ref_id
        }

        def match(ref_id):
            node = nodes.get(ref_id)
            if node is None and ref_id:
                node = nodes.get(re.sub(r"^[^0-9]+", "", str(ref_id)))
            return node

        unknown_refs = [
            e.get("ref_id") for e in entries if match(e.get("ref_id")) is None
        ]

        matched = {}
        for entry in entries:
            node = match(entry.get("ref_id"))
            if node is not None:
                matched[node.id] = entry

        update_fields = [
            "result",
            "timestamp",
            "actual",
            "expected",
            "message",
            "source",
            "imported_by",
        ]
        try:
            with transaction.atomic():
                run, run_created = PostureRun.objects.get_or_create(
                    id=run_id or uuid.uuid4(),
                    posture_assessment=assessment,
                    defaults={"started_at": timestamp, "tool": tool},
                )
                existing = {
                    r.requirement_id: r
                    for r in run.results.filter(asset=asset, requirement_id__in=matched)
                }
                to_create, to_update = [], []
                for node_id, entry in matched.items():
                    fields = {
                        "result": entry["result"],
                        "timestamp": timestamp,
                        "actual": str(entry.get("actual") or "")[:255],
                        "expected": str(entry.get("expected") or "")[:255],
                        "message": str(entry.get("message") or ""),
                        "source": source,
                        "imported_by": request.user,
                    }
                    obj = existing.get(node_id)
                    if obj is None:
                        to_create.append(
                            PostureResult(
                                run=run, asset=asset, requirement_id=node_id, **fields
                            )
                        )
                    else:
                        for key, value in fields.items():
                            setattr(obj, key, value)
                        to_update.append(obj)
                PostureResult.objects.bulk_create(to_create, batch_size=500)
                if to_update:
                    PostureResult.objects.bulk_update(
                        to_update, update_fields, batch_size=500
                    )
                if matched:
                    assessment.prune_history(
                        {(asset.id, node_id) for node_id in matched}
                    )
                elif run_created:
                    run.delete()
        except IntegrityError:
            return Response(
                {"error": "run_id belongs to another assessment"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "run_id": str(run.id),
                "created": len(to_create),
                "updated": len(to_update),
                "unknown_ref_ids": unknown_refs,
                "enrolled_asset": enrolled,
            }
        )

    EXPORT_COLUMNS = [
        "asset",
        "ref_id",
        "requirement",
        "result",
        "timestamp",
        "tool",
        "source",
        "actual",
        "expected",
        "message",
    ]

    @staticmethod
    def _export_row(row):
        return [
            f"{row['asset__folder__name']}/{row['asset__name']}",
            row["requirement__ref_id"],
            row["requirement__name"],
            row["result"],
            row["timestamp"].isoformat() if row["timestamp"] else "",
            row["run__tool"],
            row["source"],
            row["actual"],
            row["expected"],
            row["message"],
        ]

    @action(detail=True, methods=["get"], url_path="export-results")
    def export_results(self, request, pk=None):
        assessment = self.get_object()
        asset_id, error = self._asset_param(request)
        if error:
            return error
        export_format = request.query_params.get("file_format", "csv")
        rows = sorted(
            assessment.current_posture(
                asset_id=asset_id, asset_ids=self._viewable_asset_ids()
            ),
            key=lambda r: (r["asset__name"] or "", r["requirement__ref_id"] or ""),
        )
        filename = f"posture-{slugify(assessment.name)}"
        if asset_id and rows:
            filename += f"-{slugify(rows[0]['asset__name'])}"

        if export_format == "xlsx":
            from openpyxl import Workbook

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Posture"
            sheet.append(self.EXPORT_COLUMNS)
            for row in rows:
                sheet.append(
                    [escape_excel_formula(value) for value in self._export_row(row)]
                )
            buffer = io.BytesIO()
            workbook.save(buffer)
            response = HttpResponse(
                buffer.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
            return response

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
        writer = csv.writer(response)
        writer.writerow(self.EXPORT_COLUMNS)
        for row in rows:
            writer.writerow(
                [escape_excel_formula(value) for value in self._export_row(row)]
            )
        return response

    @action(
        detail=True,
        methods=["post"],
        url_path="analyze-import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def analyze_import(self, request, pk=None):
        assessment = self.get_object()
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="change_postureassessment"),
            folder=assessment.folder,
        ):
            raise PermissionDenied()
        file = request.FILES.get("file")
        if file is None:
            return Response(
                {"error": "file is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if file.size > MAX_IMPORT_FILE_SIZE:
            return Response(
                {"error": "file too large (max 10 MB)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (file.name or "").lower().endswith(".csv"):
            return Response(
                {"error": "analysis supports .csv files only"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(
                analyze_csv(file, delimiter=request.data.get("delimiter") or None)
            )
        except ImportError_ as e:
            return Response({"error": e.message}, status=status.HTTP_400_BAD_REQUEST)

    @staticmethod
    def _target_asset_ids(request):
        """Explicit targets: `assets` (JSON list of uuids) or legacy single `asset`."""
        raw = request.data.get("assets")
        if raw:
            try:
                ids = json.loads(raw)
                if not isinstance(ids, list) or not ids:
                    raise ValueError
                return [UUID(str(i)) for i in ids], None
            except json.JSONDecodeError, ValueError, TypeError:
                return None, Response(
                    {"error": "assets must be a JSON list of asset UUIDs"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        single = request.data.get("asset")
        if single:
            try:
                return [UUID(str(single))], None
            except ValueError:
                return None, Response(
                    {"error": "asset must be a valid UUID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return None, Response(
            {"error": "asset or assets is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _run_import_plan(self, request, assessment, plan, tool):
        """One shared run over [(label, asset_id|None, entries)]; None = unresolved."""
        run_id = uuid.uuid4()
        combined = {
            "run_id": str(run_id),
            "created": 0,
            "updated": 0,
            "unknown_ref_ids": [],
            "assets_imported": 0,
            "enrolled_assets": [],
            "skipped_assets": [],
        }
        for label, asset_id, entries in plan:
            if asset_id is None:
                combined["skipped_assets"].append(label or "(empty)")
                continue
            response = self._ingest(
                request,
                assessment,
                asset_id=asset_id,
                entries=entries,
                run_id=run_id,
                source=PostureResult.Source.IMPORT,
                tool=tool,
            )
            if response.status_code != 200:
                combined["skipped_assets"].append(label)
                continue
            combined["assets_imported"] += 1
            combined["created"] += response.data["created"]
            combined["updated"] += response.data["updated"]
            for ref in response.data["unknown_ref_ids"]:
                if ref not in combined["unknown_ref_ids"]:
                    combined["unknown_ref_ids"].append(ref)
            if response.data["enrolled_asset"]:
                combined["enrolled_assets"].append(label)
        if not combined["assets_imported"]:
            return Response(
                {
                    "error": "no rows could be applied to an asset",
                    "skipped_assets": combined["skipped_assets"][:20],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(combined)

    def _import_mapped(self, request, assessment, file, mapping):
        try:
            groups, extras = parse_mapped_csv(file, mapping)
        except ImportError_ as e:
            return Response({"error": e.message}, status=status.HTTP_400_BAD_REQUEST)
        tool = (file.name or "")[:100]

        if (mapping.get("columns") or {}).get("asset"):
            by_name = {}
            for row in Asset.objects.filter(
                name__in=groups.keys(), id__in=self._viewable_asset_ids()
            ).values("id", "name"):
                by_name.setdefault(row["name"], []).append(row["id"])
            plan = []
            for asset_value, entries in groups.items():
                ids = by_name.get(asset_value, [])
                plan.append((asset_value, ids[0] if len(ids) == 1 else None, entries))
        else:
            targets, error = self._target_asset_ids(request)
            if error:
                return error
            entries = groups.get("", [])
            plan = [(str(asset_id), asset_id, entries) for asset_id in targets]

        response = self._run_import_plan(request, assessment, plan, tool)
        if response.status_code == 200:
            response.data.update(extras)
        return response

    @action(
        detail=True,
        methods=["post"],
        url_path="import-results",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_results(self, request, pk=None):
        assessment = self.get_object()
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="change_postureassessment"),
            folder=assessment.folder,
        ):
            raise PermissionDenied()
        locked = self._locked(assessment)
        if locked:
            return locked

        file = request.FILES.get("file")
        if file is None:
            return Response(
                {"error": "file is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if file.size > MAX_IMPORT_FILE_SIZE:
            return Response(
                {"error": "file too large (max 10 MB)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mapping_raw = request.data.get("mapping")
        if mapping_raw:
            try:
                mapping = json.loads(mapping_raw)
            except TypeError, json.JSONDecodeError:
                return Response(
                    {"error": "mapping must be valid JSON"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not (file.name or "").lower().endswith(".csv"):
                return Response(
                    {"error": "mapped import supports .csv files only"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return self._import_mapped(request, assessment, file, mapping)

        try:
            entries, extras = parse_file(file)
        except ImportError_ as e:
            return Response({"error": e.message}, status=status.HTTP_400_BAD_REQUEST)

        tool = extras.pop("tool", "") or (file.name or "")[:100]
        if request.data.get("assets"):
            targets, error = self._target_asset_ids(request)
            if error:
                return error
            response = self._run_import_plan(
                request,
                assessment,
                [(str(asset_id), asset_id, entries) for asset_id in targets],
                tool,
            )
        else:
            response = self._ingest(
                request,
                assessment,
                asset_id=request.data.get("asset"),
                entries=entries,
                run_id=None,
                source=PostureResult.Source.IMPORT,
                tool=tool,
            )
        if response.status_code == 200:
            extras["parse_errors"] = extras.get("parse_errors", [])[:20]
            response.data.update(extras)
        return response

    @action(detail=True, methods=["post"], url_path="purge-asset")
    def purge_asset(self, request, pk=None):
        assessment = self.get_object()
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="delete_postureresult"),
            folder=assessment.folder,
        ):
            raise PermissionDenied()
        locked = self._locked(assessment)
        if locked:
            return locked
        try:
            asset_id = UUID(str(request.data.get("asset")))
        except TypeError, ValueError:
            return Response(
                {"error": "asset must be a valid UUID"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            deleted, _ = assessment.results.filter(asset_id=asset_id).delete()
            assessment.runs.filter(results__isnull=True).delete()
            assessment.assets.remove(asset_id)
        return Response({"deleted_results": deleted})

    def _follow_up_findings(self, assessment):
        if not assessment.follow_up_assessment_id:
            return {}
        if not RoleAssignment.is_access_allowed(
            user=self.request.user,
            perm=Permission.objects.get(codename="view_finding"),
            folder=assessment.follow_up_assessment.folder,
        ):
            return {}
        findings = Finding.objects.filter(
            findings_assessment_id=assessment.follow_up_assessment_id,
            requirement_node__isnull=False,
            asset__isnull=False,
        ).prefetch_related("applied_controls")
        return {(f.requirement_node_id, f.asset_id): f for f in findings}

    @action(detail=True, methods=["get"], url_path="action-plan")
    def action_plan(self, request, pk=None):
        assessment = self.get_object()
        severity = {"fail": 0, "error": 1, "not_checked": 2, "not_applicable": 3}
        non_pass = sorted(
            (
                r
                for r in assessment.current_posture(
                    asset_ids=self._viewable_asset_ids()
                )
                if r["result"] != "pass"
            ),
            key=lambda r: severity.get(r["result"], len(severity)),
        )
        findings = self._follow_up_findings(assessment)
        rows = []
        for r in non_pass:
            finding = findings.get((r["requirement_id"], r["asset_id"]))
            rows.append(
                {
                    "requirement": {
                        "id": str(r["requirement_id"]),
                        "ref_id": r["requirement__ref_id"],
                        "name": r["requirement__name"],
                    },
                    "asset": {
                        "id": str(r["asset_id"]),
                        "str": f"{r['asset__folder__name']}/{r['asset__name']}",
                    },
                    "result": r["result"],
                    "actual": r["actual"],
                    "expected": r["expected"],
                    "message": r["message"],
                    "timestamp": r["timestamp"],
                    "finding": {
                        "id": str(finding.id),
                        "name": finding.name,
                        "status": finding.status,
                        "eta": finding.eta,
                        "applied_controls": [
                            {"id": str(ac.id), "str": str(ac)}
                            for ac in finding.applied_controls.all()
                        ],
                    }
                    if finding
                    else None,
                }
            )
        by_result = Counter(row["result"] for row in rows)
        return Response(
            {
                "total": len(rows),
                "by_result": dict(by_result),
                "planned": sum(1 for row in rows if row["finding"]),
                "results": rows,
            }
        )

    @action(detail=True, methods=["post"], url_path="create-finding")
    def create_finding(self, request, pk=None):
        assessment = self.get_object()
        locked = self._locked(assessment)
        if locked:
            return locked
        requirement = RequirementNode.objects.filter(
            id=request.data.get("requirement"), framework=assessment.framework
        ).first()
        asset = assessment.assets.filter(
            id=request.data.get("asset"), id__in=self._viewable_asset_ids()
        ).first()
        if requirement is None or asset is None:
            return Response(
                {"error": "requirement and asset must belong to the assessment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow_up = assessment.follow_up_assessment
        if follow_up is None:
            return Response(
                {"error": "no follow-up assessment attached"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_finding"),
            folder=follow_up.folder,
        ):
            raise PermissionDenied()

        existing = Finding.objects.filter(
            findings_assessment=follow_up, requirement_node=requirement, asset=asset
        ).first()
        if existing:
            return Response({"finding": str(existing.id), "created": False})

        last = (
            assessment.results.filter(requirement=requirement, asset=asset)
            .order_by("-timestamp", "-created_at")
            .first()
        )
        description = ""
        if last:
            parts = [
                p
                for p in (
                    last.message,
                    last.actual and f"actual: {last.actual}",
                    last.expected and f"expected: {last.expected}",
                )
                if p
            ]
            description = "\n".join(parts)
        finding = Finding.objects.create(
            findings_assessment=follow_up,
            folder=follow_up.folder,
            requirement_node=requirement,
            asset=asset,
            name=f"{requirement.ref_id} failing on {asset.name}"[:200],
            description=description,
            status=Finding.Status.IDENTIFIED,
        )
        return Response(
            {"finding": str(finding.id), "created": True},
            status=status.HTTP_201_CREATED,
        )
