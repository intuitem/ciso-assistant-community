import structlog
from django.db.models import F
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import FeatureFlagRequired, IsGlobalAdmin
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .models import SecurityAdvisory, CWE, TTPCatalog, Tactic, Technique

logger = structlog.get_logger(__name__)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "sec_intel.serializers"


class SecurityAdvisoryViewSet(BaseModelViewSet):
    """
    API endpoint that allows security advisories to be viewed or edited.
    """

    model = SecurityAdvisory
    filterset_fields = [
        "folder",
        "provider",
        "library",
        "filtering_labels",
        "urn",
        "source",
    ]
    search_fields = ["name", "ref_id", "description", "cvss_vector", "aliases"]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(
                "folder",
                "folder__parent_folder",  # For folder path / FieldsRelatedField
                "library",  # FieldsRelatedField(["name", "id"])
            )
        )
        if self.action == "autocomplete":
            return qs
        # `filtering_labels` is rendered as FieldsRelatedField(["id", "folder"]),
        # so prefetch the nested folder too — otherwise each label fires a fresh
        # query for its folder, producing a per-row × per-label N+1.
        return qs.prefetch_related("filtering_labels__folder")

    @action(detail=False, name="Get source choices")
    def source(self, request):
        return Response(dict(SecurityAdvisory.Source.choices))

    @action(detail=False, name="Lightweight autocomplete search")
    def autocomplete(self, request):
        from sec_intel.serializers import SecurityAdvisoryReadSerializer

        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        objects = page if page is not None else qs
        serializer = SecurityAdvisoryReadSerializer(objects, many=True)
        data = serializer.data
        field_models = self._get_fieldsrelated_map(serializer)
        if field_models:
            allowed_ids = self._get_accessible_ids_map(set(field_models.values()))
            data = self._filter_related_fields(data, field_models, allowed_ids)
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)

    @action(
        detail=False,
        methods=["post"],
        url_path="sync-kev",
        permission_classes=[IsAuthenticated, IsGlobalAdmin],
    )
    def sync_kev(self, request):
        """Sync KEV feed synchronously. Scheduled async via Huey periodic tasks."""
        from sec_intel.feeds import KEVFeed

        try:
            result = KEVFeed().sync()
            return Response(
                {
                    "detail": f"KEV sync complete: {result['created']} created, {result['updated']} updated",
                    **result,
                }
            )
        except Exception:
            logger.warning("KEV sync failed", exc_info=True)
            return Response(
                {"error": "KEV sync failed due to an internal error"},
                status=502,
            )

    @action(
        detail=False,
        methods=["post"],
        url_path="sync-euvd",
        permission_classes=[IsAuthenticated, IsGlobalAdmin],
    )
    def sync_euvd(self, request):
        """Sync EUVD exploited vulnerabilities synchronously."""
        from sec_intel.feeds import EUVDFeed

        try:
            result = EUVDFeed().sync()
            return Response(
                {
                    "detail": f"EUVD sync complete: {result['created']} created, {result['updated']} updated",
                    **result,
                }
            )
        except Exception:
            logger.warning("EUVD sync failed", exc_info=True)
            return Response(
                {"error": "EUVD sync failed due to an internal error"},
                status=502,
            )

    @action(detail=True, methods=["post"], url_path="enrich")
    def enrich(self, request, pk=None):
        """Enrich this advisory with data from its source (NVD or EUVD)."""
        sa = self.get_object()
        lookup_id = sa.ref_id or sa.name

        if sa.source == "EUVD":
            from sec_intel.feeds import EUVDFeed

            if not lookup_id or not lookup_id.startswith("EUVD-"):
                return Response(
                    {"error": "EUVD ref_id must start with EUVD-"}, status=400
                )
            try:
                resp = EUVDFeed().fetch_exploited()
                # Find this specific entry
                entry = next((e for e in resp if e.get("id") == lookup_id), None)
                if not entry:
                    # Try direct lookup
                    import httpx
                    from sec_intel.feeds import _get_timeout

                    direct = httpx.get(
                        f"https://euvdservices.enisa.europa.eu/api/enisaid",
                        params={"id": lookup_id},
                        headers={"User-Agent": "CISO-Assistant/1.0"},
                        timeout=_get_timeout(),
                    )
                    direct.raise_for_status()
                    entry = direct.json()
                if not entry:
                    return Response({"error": "Advisory not found in EUVD"}, status=404)
                parsed = EUVDFeed().parse([entry])
                fields = parsed[0] if parsed else {}
            except Exception:
                logger.warning("EUVD enrich failed", exc_info=True)
                return Response({"error": "Failed to fetch data from EUVD"}, status=502)
        else:
            from sec_intel.feeds import EPSSFeed, NVDFeed, get_feed_settings

            if not lookup_id or not lookup_id.startswith("CVE-"):
                return Response(
                    {"error": "CVE ref_id or name must start with CVE-"}, status=400
                )
            raw = NVDFeed.fetch_cve(lookup_id)
            fields = NVDFeed.parse_cve(raw) if raw is not None else {}

            if get_feed_settings().get("epss_feed_enabled", False):
                epss = EPSSFeed.fetch_cve(lookup_id)
                if epss:
                    fields.update(epss)

            if raw is None and not fields:
                return Response({"error": "Failed to fetch data from NVD"}, status=502)

        if not fields:
            return Response({"detail": "No enrichment data found", "updated": []})

        skip_fields = {"euvd_id", "source", "aliases", "ref_id"}
        always_overwrite = {"epss_score", "epss_percentile"}
        updated = []
        for k, v in fields.items():
            if k in skip_fields:
                continue
            current = getattr(sa, k, None)
            if k in always_overwrite:
                if current != v:
                    setattr(sa, k, v)
                    updated.append(k)
            elif current in (None, "", 0, []):
                setattr(sa, k, v)
                updated.append(k)

        if updated:
            sa.save(update_fields=updated)

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

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("folder", "folder__parent_folder", "library")
        )
        if self.action == "autocomplete":
            return qs
        return qs.prefetch_related("filtering_labels__folder")

    @action(detail=False, name="Lightweight autocomplete search")
    def autocomplete(self, request):
        from sec_intel.serializers import CWEReadSerializer

        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        objects = page if page is not None else qs
        serializer = CWEReadSerializer(objects, many=True)
        data = serializer.data
        field_models = self._get_fieldsrelated_map(serializer)
        if field_models:
            allowed_ids = self._get_accessible_ids_map(set(field_models.values()))
            data = self._filter_related_fields(data, field_models, allowed_ids)
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)

    @action(
        detail=False,
        methods=["post"],
        url_path="sync-catalog",
        permission_classes=[IsAuthenticated, IsGlobalAdmin],
    )
    def sync_catalog(self, request):
        """Sync CWE catalog from MITRE."""
        from sec_intel.feeds import CWEFeed

        try:
            result = CWEFeed().sync()
            return Response(
                {
                    "detail": f"CWE sync complete: {result['created']} created, {result['updated']} updated",
                    **result,
                }
            )
        except Exception:
            logger.warning("CWE sync failed", exc_info=True)
            return Response(
                {"error": "CWE sync failed due to an internal error"},
                status=502,
            )


class TacticViewSet(BaseModelViewSet):
    """
    API endpoint that allows tactics to be viewed or edited.
    """

    feature_flag = "ttps"

    def get_permissions(self):
        return super().get_permissions() + [FeatureFlagRequired()]

    model = Tactic
    filterset_fields = ["folder", "provider", "library", "catalog", "urn"]
    search_fields = ["ref_id", "name", "description"]

    def get_queryset(self):
        return super().get_queryset().select_related("folder", "library", "catalog")


class TechniqueViewSet(BaseModelViewSet):
    """
    API endpoint that allows techniques to be viewed or edited.
    """

    feature_flag = "ttps"

    def get_permissions(self):
        return super().get_permissions() + [FeatureFlagRequired()]

    model = Technique
    filterset_fields = [
        "folder",
        "provider",
        "library",
        "catalog",
        "tactics",
        "parent",
        "is_deprecated",
        "filtering_labels",
        "urn",
    ]
    search_fields = ["ref_id", "name", "provider", "description"]

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related(
                "folder",
                "folder__parent_folder",
                "library",
                "parent",  # display_short composes the parent name
                "catalog",
            )
            .prefetch_related(
                "filtering_labels__folder", "tactics", "reference_controls"
            )
        )
        if not self.request.query_params.get("is_deprecated"):
            queryset = queryset.filter(is_deprecated=False)
        return queryset

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        providers = set(
            Technique.objects.filter(provider__isnull=False).values_list(
                "provider", flat=True
            )
        )
        return Response({p: p for p in providers})


def build_catalog_matrix(catalog) -> dict:
    columns = [
        {
            "id": tactic.id,
            "ref_id": tactic.ref_id,
            "name": tactic.get_name_translated,
            "description": tactic.get_description_translated,
        }
        for tactic in catalog.tactics.order_by(F("order_id").asc(nulls_last=True))
    ]

    techniques = (
        Technique.objects.filter(catalog=catalog, is_deprecated=False)
        .select_related("parent")
        .prefetch_related("tactics")
    )

    children, cells = {}, []
    for technique in techniques:
        payload = {
            "id": technique.id,
            "ref_id": technique.ref_id,
            "name": technique.get_name_translated,
            "tactics": [str(t.id) for t in technique.tactics.all()],
            "groups": technique.groups or [],
        }
        if technique.parent_id:
            children.setdefault(str(technique.parent_id), []).append(payload)
        else:
            cells.append(payload)

    # published matrices order cells by name, sub-techniques by ref_id
    for cell in cells:
        cell["children"] = sorted(
            children.pop(str(cell["id"]), []), key=lambda item: item["ref_id"]
        )
    for orphans in children.values():
        cells.extend({**orphan, "children": []} for orphan in orphans)
    cells.sort(key=lambda item: item["name"].casefold())

    return {
        "catalog": {
            "id": catalog.id,
            "ref_id": catalog.ref_id,
            "name": catalog.get_name_translated,
            "description": catalog.get_description_translated,
        },
        "columns": columns,
        "facets": catalog.grouping_definition or [],
        "cells": cells,
    }


class TTPCatalogViewSet(BaseModelViewSet):
    """
    API endpoint that allows TTP catalogs to be viewed or edited.
    """

    feature_flag = "ttps"

    def get_permissions(self):
        return super().get_permissions() + [FeatureFlagRequired()]

    model = TTPCatalog
    filterset_fields = ["folder", "provider", "library", "urn"]
    search_fields = ["ref_id", "name", "provider", "description"]

    @action(detail=True, name="Get the catalog rendered as a matrix")
    def matrix(self, request, pk):
        return Response(build_catalog_matrix(self.get_object()))
