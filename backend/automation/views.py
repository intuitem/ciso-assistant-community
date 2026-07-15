import uuid
from collections import Counter
from uuid import UUID

from django.contrib.auth.models import Permission
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.models import Finding, FindingsAssessment, RequirementNode
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from iam.models import RoleAssignment

from .models import PostureAssessment, PostureResult

LONG_CACHE_TTL = 60  # mn


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

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get result choices")
    def result(self, request):
        return Response(dict(PostureResult.Result.choices))

    @staticmethod
    def _row_payload(row):
        return {
            "id": str(row["id"]),
            "requirement": {
                "id": str(row["requirement_id"]),
                "ref_id": row["requirement__ref_id"],
                "name": row["requirement__name"],
            },
            "asset": {"id": str(row["asset_id"]), "str": row["asset__name"]},
            "result": row["result"],
            "timestamp": row["timestamp"],
            "run_id": str(row["run_id"]),
            "actual": row["actual"],
            "expected": row["expected"],
            "message": row["message"],
        }

    @action(detail=True, methods=["get"])
    def posture(self, request, pk=None):
        assessment = self.get_object()
        rows = assessment.current_posture()
        counts = Counter(row["result"] for row in rows)
        applicable = counts["pass"] + counts["fail"]
        score = round(100 * counts["pass"] / applicable, 1) if applicable else None
        return Response(
            {
                "score": score,
                "results": [self._row_payload(row) for row in rows],
            }
        )

    @action(detail=True, methods=["get"])
    def tree(self, request, pk=None):
        assessment = self.get_object()
        asset_id = request.query_params.get("asset")
        if asset_id:
            try:
                asset_id = UUID(str(asset_id))
            except ValueError:
                return Response(
                    {"error": "asset must be a valid UUID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        rows = assessment.current_posture(asset_id=asset_id)
        counts_by_requirement = {}
        row_by_requirement = {}
        for r in rows:
            counts_by_requirement.setdefault(r["requirement_id"], Counter())[
                r["result"]
            ] += 1
            if asset_id:
                row_by_requirement[r["requirement_id"]] = r

        nodes = list(RequirementNode.objects.filter(framework=assessment.framework))
        for node in nodes:
            if node.order_id is None:
                node.order_id = node.created_at
        children = {}
        for node in nodes:
            children.setdefault(node.parent_urn, []).append(node)
        for siblings in children.values():
            siblings.sort(key=lambda n: n.order_id)

        def serialize(node):
            entry = {
                "id": str(node.id),
                "urn": node.urn,
                "ref_id": node.ref_id,
                "name": node.name,
                "description": node.description,
                "assessable": node.assessable,
                "counts": dict(counts_by_requirement.get(node.id, {})),
                "children": [serialize(c) for c in children.get(node.urn, [])],
            }
            for child in entry["children"]:
                for result, count in child["counts"].items():
                    entry["counts"][result] = entry["counts"].get(result, 0) + count
            row = row_by_requirement.get(node.id)
            if row:
                entry["current"] = {
                    "result": row["result"],
                    "timestamp": row["timestamp"],
                    "actual": row["actual"],
                    "expected": row["expected"],
                    "message": row["message"],
                }
            return entry

        return Response(
            {
                "tree": [serialize(n) for n in children.get(None, [])],
                "assets": [
                    {"id": str(a.id), "str": str(a)} for a in assessment.assets.all()
                ],
            }
        )

    @action(detail=True, methods=["get"])
    def trend(self, request, pk=None):
        assessment = self.get_object()
        rows = assessment.results.order_by("timestamp", "created_at").values(
            "asset_id", "requirement_id", "result", "run_id", "timestamp"
        )
        latest = {}
        points = []
        current_run = None
        current_ts = None

        def snapshot():
            counts = Counter(latest.values())
            applicable = counts["pass"] + counts["fail"]
            score = round(100 * counts["pass"] / applicable, 1) if applicable else None
            return {
                "run_id": str(current_run),
                "timestamp": current_ts,
                "score": score,
                "counts": dict(counts),
            }

        for row in rows:
            if current_run is not None and row["run_id"] != current_run:
                points.append(snapshot())
            current_run = row["run_id"]
            current_ts = row["timestamp"]
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

        asset_id = request.data.get("asset")
        entries = request.data.get("results")
        if not asset_id or not isinstance(entries, list) or not entries:
            return Response(
                {"error": "asset and a non-empty results list are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset = assessment.assets.filter(id=asset_id).first()
        if asset is None:
            return Response(
                {"error": "asset is not in the assessment scope", "asset": asset_id},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_results = set(PostureResult.Result.values)
        invalid = [
            e.get("ref_id") for e in entries if e.get("result") not in valid_results
        ]
        if invalid:
            return Response(
                {"error": "invalid result values", "ref_ids": invalid},
                status=status.HTTP_400_BAD_REQUEST,
            )

        run_id = request.data.get("run_id")
        if run_id:
            try:
                run_id = UUID(str(run_id))
            except ValueError:
                return Response(
                    {"error": "run_id must be a valid UUID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            run_id = uuid.uuid4()

        source = request.data.get("source", PostureResult.Source.API)
        if source not in PostureResult.Source.values:
            return Response(
                {"error": "invalid source"}, status=status.HTTP_400_BAD_REQUEST
            )

        timestamp = timezone.now()
        tool = request.data.get("tool", "")

        nodes = {
            node.ref_id: node
            for node in RequirementNode.objects.filter(
                framework=assessment.framework, assessable=True
            )
            if node.ref_id
        }
        unknown_refs = [
            e.get("ref_id") for e in entries if e.get("ref_id") not in nodes
        ]

        touched = set()
        created = updated = 0
        for entry in entries:
            node = nodes.get(entry.get("ref_id"))
            if node is None:
                continue
            _, was_created = PostureResult.objects.update_or_create(
                run_id=run_id,
                asset=asset,
                requirement=node,
                defaults={
                    "posture_assessment": assessment,
                    "result": entry["result"],
                    "timestamp": timestamp,
                    "actual": entry.get("actual", ""),
                    "expected": entry.get("expected", ""),
                    "message": entry.get("message", ""),
                    "tool": tool,
                    "source": source,
                    "imported_by": request.user,
                },
            )
            created += was_created
            updated += not was_created
            touched.add((asset.id, node.id))

        assessment.prune_history(touched)
        return Response(
            {
                "run_id": str(run_id),
                "created": created,
                "updated": updated,
                "unknown_ref_ids": unknown_refs,
            }
        )

    def _follow_up_findings(self, assessment):
        if not assessment.follow_up_assessment_id:
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
        fails = [r for r in assessment.current_posture() if r["result"] == "fail"]
        findings = self._follow_up_findings(assessment)
        rows = []
        for r in fails:
            finding = findings.get((r["requirement_id"], r["asset_id"]))
            rows.append(
                {
                    "requirement": {
                        "id": str(r["requirement_id"]),
                        "ref_id": r["requirement__ref_id"],
                        "name": r["requirement__name"],
                    },
                    "asset": {"id": str(r["asset_id"]), "str": r["asset__name"]},
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
        return Response(
            {
                "total_fails": len(rows),
                "planned": sum(1 for row in rows if row["finding"]),
                "results": rows,
            }
        )

    @action(detail=True, methods=["post"], url_path="create-finding")
    def create_finding(self, request, pk=None):
        assessment = self.get_object()
        requirement = RequirementNode.objects.filter(
            id=request.data.get("requirement"), framework=assessment.framework
        ).first()
        asset = assessment.assets.filter(id=request.data.get("asset")).first()
        if requirement is None or asset is None:
            return Response(
                {"error": "requirement and asset must belong to the assessment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow_up = assessment.follow_up_assessment
        if follow_up is None:
            if not RoleAssignment.is_access_allowed(
                user=request.user,
                perm=Permission.objects.get(codename="add_findingsassessment"),
                folder=assessment.folder,
            ):
                raise PermissionDenied()
            follow_up = FindingsAssessment.objects.create(
                name=f"{assessment.name} — follow-up"[:200],
                folder=assessment.folder,
                perimeter=assessment.perimeter,
                category=FindingsAssessment.Category.POSTURE,
            )
            assessment.follow_up_assessment = follow_up
            assessment.save(update_fields=["follow_up_assessment"])

        existing = Finding.objects.filter(
            findings_assessment=follow_up, requirement_node=requirement, asset=asset
        ).first()
        if existing:
            return Response({"finding": str(existing.id), "created": False})

        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_finding"),
            folder=follow_up.folder,
        ):
            raise PermissionDenied()

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
