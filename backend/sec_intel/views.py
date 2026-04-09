import structlog
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .models import CVE, CWE

logger = structlog.get_logger(__name__)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "sec_intel.serializers"


class CVEViewSet(BaseModelViewSet):
    """
    API endpoint that allows CVEs to be viewed or edited.
    """

    model = CVE
    filterset_fields = [
        "folder",
        "provider",
        "library",
        "filtering_labels",
        "urn",
    ]
    search_fields = ["name", "ref_id", "description", "cvss_vector"]

    @action(detail=False, name="Lightweight autocomplete search")
    def autocomplete(self, request):
        from sec_intel.serializers import CVEReadSerializer

        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        objects = page if page is not None else qs
        serializer = CVEReadSerializer(objects, many=True)
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )

    @action(detail=False, methods=["post"], url_path="sync-kev")
    def sync_kev(self, request):
        """Sync KEV feed: create new CVEs + update existing ones."""
        from sec_intel.feeds import KEVFeed

        try:
            result = KEVFeed().sync()
            return Response(
                {
                    "detail": f"KEV sync complete: {result['created']} created, {result['updated']} updated",
                    **result,
                }
            )
        except Exception as e:
            logger.warning("KEV sync failed", exc_info=True)
            return Response({"error": str(e)}, status=502)

    @action(detail=True, methods=["post"], url_path="enrich")
    def enrich(self, request, pk=None):
        """Enrich this CVE with data from NVD."""
        from sec_intel.feeds import NVDFeed

        cve = self.get_object()
        cve_id = cve.ref_id or cve.name
        if not cve_id or not cve_id.startswith("CVE-"):
            return Response(
                {"error": "CVE ref_id or name must start with CVE-"}, status=400
            )

        raw = NVDFeed.fetch_cve(cve_id)
        if raw is None:
            return Response({"error": "Failed to fetch data from NVD"}, status=502)

        fields = NVDFeed.parse_cve(raw)
        if not fields:
            return Response({"detail": "No enrichment data found", "updated": []})

        updated = []
        for k, v in fields.items():
            current = getattr(cve, k, None)
            if current in (None, "", 0, []):
                setattr(cve, k, v)
                updated.append(k)

        if updated:
            cve.save(update_fields=updated)

        return Response(
            {"detail": f"Enriched {len(updated)} fields", "updated": updated}
        )


class CWEViewSet(BaseModelViewSet):
    """
    API endpoint that allows CWEs to be viewed or edited.
    """

    model = CWE
    filterset_fields = [
        "folder",
        "provider",
        "library",
        "filtering_labels",
        "urn",
    ]
    search_fields = ["name", "ref_id", "description"]

    @action(detail=False, name="Lightweight autocomplete search")
    def autocomplete(self, request):
        from sec_intel.serializers import CWEReadSerializer

        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        objects = page if page is not None else qs
        serializer = CWEReadSerializer(objects, many=True)
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )

    @action(detail=False, methods=["post"], url_path="sync-catalog")
    def sync_catalog(self, request):
        """Sync CWE catalog from MITRE: create new + update existing."""
        from sec_intel.feeds import CWEFeed

        try:
            result = CWEFeed().sync()
            return Response(
                {
                    "detail": f"CWE sync complete: {result['created']} created, {result['updated']} updated",
                    **result,
                }
            )
        except Exception as e:
            logger.warning("CWE sync failed", exc_info=True)
            return Response({"error": str(e)}, status=502)
