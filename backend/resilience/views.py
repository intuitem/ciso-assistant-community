from os import name
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from core.serializers import RiskMatrixReadSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from iam.models import RoleAssignment, Folder
from core.models import Asset

SHORT_CACHE_TTL = 2  # mn
MED_CACHE_TTL = 5  # mn
LONG_CACHE_TTL = 60  # mn

from .models import (
    BusinessImpactAnalysis,
    AssetAssessment,
    EscalationThreshold,
)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "resilience.serializers"


class BusinessImpactAnalysisViewSet(BaseModelViewSet):
    model = BusinessImpactAnalysis
    filterset_fields = [
        "perimeter",
        "perimeter__folder",
        "authors",
        "risk_matrix",
        "status",
    ]

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

    def _get_asset_verdict(self, asset):
        """
        Calculate verdict based on security and recovery objectives vs capabilities.
        Returns False if any objective is not met, True if all are met, None otherwise.
        """
        # Get comparisons from the asset's methods
        security_comparison = asset.get_security_objectives_comparison()
        recovery_comparison = asset.get_recovery_objectives_comparison()

        all_comparisons = []

        if security_comparison:
            all_comparisons.extend(security_comparison)
        if recovery_comparison:
            all_comparisons.extend(recovery_comparison)

        if not all_comparisons:
            return None

        # Check if any comparison has failed (verdict is False)
        if any(comp.get("verdict") is False for comp in all_comparisons):
            return False

        # Check if all comparisons have passed (verdict is True)
        if all(comp.get("verdict") is True for comp in all_comparisons):
            return True

        return None  # Some are indeterminate

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
        """
        Returns graph data for visualizing asset dependencies.
        Includes nodes grouped by folder and links between parent-child assets.
        Only includes assets that are viewable by the current user.
        """

        aa = self.get_object()
        asset = aa.asset

        # Get all descendants of the asset
        descendants = asset.get_descendants()
        all_assets = {asset} | descendants
        all_asset_ids = {a.id for a in all_assets}

        # Get viewable asset IDs using the standard pattern
        viewable_asset_ids = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(), user=request.user, object_type=Asset
        )[0]

        # Filter to only assets that are both in our tree and viewable
        accessible_asset_ids = all_asset_ids & set(viewable_asset_ids)
        viewable_assets = Asset.objects.filter(id__in=accessible_asset_ids)

        # Build nodes grouped by folder
        folder_groups = {}
        nodes = []

        for a in viewable_assets:
            folder_name = a.folder.name if a.folder else "No Folder"
            folder_id = str(a.folder.id) if a.folder else "no-folder"

            if folder_id not in folder_groups:
                folder_groups[folder_id] = {
                    "id": folder_id,
                    "name": folder_name,
                    "nodes": [],
                }

            # Calculate verdict based on objectives vs capabilities
            verdict = self._get_asset_verdict(a)

            node = {
                "id": str(a.id),
                "label": a.name,
                "folder": folder_id,
                "verdict": verdict,
            }
            nodes.append(node)
            folder_groups[folder_id]["nodes"].append(str(a.id))

        # Build links - invert direction to show children supporting parents
        links = []

        for a in viewable_assets:
            # Get direct children that are also viewable
            children = a.child_assets.filter(id__in=accessible_asset_ids)
            for child in children:
                # Invert: child (source) -> parent (target) to show support relationship
                links.append(
                    {
                        "source": str(child.id),
                        "target": str(a.id),
                    }
                )

        return Response(
            {
                "nodes": nodes,
                "links": links,
                "groups": list(folder_groups.values()),
            }
        )


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

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get impact choices")
    def quali_impact(self, request, pk):
        escalation_threshold = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in escalation_threshold.parsed_matrix["impact"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)
