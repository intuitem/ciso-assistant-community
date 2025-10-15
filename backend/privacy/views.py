from core.constants import COUNTRY_CHOICES
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import filters
from django.db.models import Count
from itertools import chain
from collections import defaultdict

from .models import (
    ProcessingNature,
    Purpose,
    PersonalData,
    DataSubject,
    DataRecipient,
    DataContractor,
    DataTransfer,
    Processing,
    RightRequest,
    DataBreach,
    LEGAL_BASIS_CHOICES,
)

EU_COUNTRIES_SET = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
}


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "privacy.serializers"


class PurposeViewSet(BaseModelViewSet):
    """
    API endpoint that allows purposes to be viewed or edited.
    """

    model = Purpose
    filterset_fields = ["processing", "legal_basis"]

    @action(detail=False, name="Get legal basis choices")
    def legal_basis(self, request):
        return Response(dict(LEGAL_BASIS_CHOICES))


class PersonalDataViewSet(BaseModelViewSet):
    """
    API endpoint that allows personal data to be viewed or edited.
    """

    model = PersonalData
    filterset_fields = ["processing", "category", "assets"]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(PersonalData.PERSONAL_DATA_CHOICES))

    @action(detail=False, name="Get deletion policy choices")
    def deletion_policy(self, request):
        return Response(dict(PersonalData.DELETION_POLICY_CHOICES))


class DataSubjectViewSet(BaseModelViewSet):
    """
    API endpoint that allows data subjects to be viewed or edited.
    """

    model = DataSubject
    filterset_fields = ["processing"]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(DataSubject.CATEGORY_CHOICES))


class DataRecipientViewSet(BaseModelViewSet):
    """
    API endpoint that allows data recipients to be viewed or edited.
    """

    model = DataRecipient
    filterset_fields = ["processing"]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(DataRecipient.CATEGORY_CHOICES))


class DataContractorViewSet(BaseModelViewSet):
    """
    API endpoint that allows data contractors to be viewed or edited.
    """

    model = DataContractor
    filterset_fields = ["processing"]

    @action(detail=False, name="Get category choices")
    def relationship_type(self, request):
        return Response(dict(DataContractor.RELATIONSHIP_TYPE_CHOICES))

    # this should be cached
    @action(detail=False, name="Get countries list")
    def country(self, request):
        return Response(dict(COUNTRY_CHOICES))


class DataTransferViewSet(BaseModelViewSet):
    """
    API endpoint that allows data transfers to be viewed or edited.
    """

    model = DataTransfer
    filterset_fields = ["processing"]

    # this should be cached
    @action(detail=False, name="Get countries list")
    def country(self, request):
        return Response(dict(COUNTRY_CHOICES))

    @action(detail=False, name="Get legal basis choices")
    def legal_basis(self, request):
        return Response(dict(LEGAL_BASIS_CHOICES))


def agg_countries():
    transfer_countries = DataTransfer.objects.values("country").annotate(
        count=Count("id")
    )
    contractor_countries = DataContractor.objects.values("country").annotate(
        count=Count("id")
    )
    country_counts = defaultdict(int)
    for item in chain(transfer_countries, contractor_countries):
        country_counts[item["country"]] += item["count"]

    # if country code is in EU (GDPR scope) set the dict color to #A7CC74 otherwise to #F4B83D
    countries = [
        {
            "id": country,
            "count": count,
            "color": "#A7CC74" if country in EU_COUNTRIES_SET else "#F4B83D",
        }
        for country, count in country_counts.items()
    ]

    return countries


class ProcessingViewSet(BaseModelViewSet):
    model = Processing

    filterset_fields = ["folder", "nature", "status", "filtering_labels"]

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(Processing.STATUS_CHOICES))

    @action(detail=False, name="processing metrics")
    def metrics(self, request, pk=None):
        return Response({})

    @action(detail=False, name="aggregated metrics")
    def agg_metrics(self, request):
        pd_categories = PersonalData.get_categories_count()
        total_categories = len(pd_categories)
        processings_count = Processing.objects.all().count()

        # Count distinct entities from data contractors and data transfers
        contractor_entities = (
            DataContractor.objects.filter(entity__isnull=False)
            .values_list("entity", flat=True)
            .distinct()
        )
        transfer_entities = (
            DataTransfer.objects.filter(entity__isnull=False)
            .values_list("entity", flat=True)
            .distinct()
        )
        recipients_count = len(set(list(contractor_entities) + list(transfer_entities)))

        open_right_requests_count = RightRequest.objects.exclude(status="done").count()
        open_data_breaches_count = DataBreach.objects.exclude(
            status="privacy_closed"
        ).count()

        # Aggregate data breaches by breach type
        breach_types = DataBreach.objects.values("breach_type").annotate(
            count=Count("id")
        )
        breach_type_data = [
            {"name": item["breach_type"], "value": item["count"]}
            for item in breach_types
        ]

        # Aggregate right requests by request type
        request_types = RightRequest.objects.values("request_type").annotate(
            count=Count("id")
        )
        request_type_data = [
            {"name": item["request_type"], "value": item["count"]}
            for item in request_types
        ]

        # Build Sankey diagram data: Personal Data → Processing → Legal Basis
        sankey_nodes = []
        sankey_links = []
        node_indices = {}  # Map node names to indices

        # Get all personal data with their processings and legal bases
        personal_data = (
            PersonalData.objects.select_related("processing")
            .prefetch_related("processing__purposes", "processing__data_transfers")
            .all()
        )

        for pd in personal_data:
            pd_category = pd.category
            processing_name = (
                pd.processing.name if pd.processing else "Unknown Processing"
            )

            # Add personal data category node (depth 0)
            pd_key = f"pd_{pd_category}"
            if pd_key not in node_indices:
                node_indices[pd_key] = len(sankey_nodes)
                sankey_nodes.append({"name": pd_category, "depth": 0})

            # Add processing node (depth 1)
            proc_key = f"proc_{processing_name}"
            if proc_key not in node_indices:
                node_indices[proc_key] = len(sankey_nodes)
                sankey_nodes.append(
                    {"name": f"Processing: {processing_name}", "depth": 1}
                )

            # Link personal data to processing
            existing_link = next(
                (
                    l
                    for l in sankey_links
                    if l["source"] == node_indices[pd_key]
                    and l["target"] == node_indices[proc_key]
                ),
                None,
            )
            if existing_link:
                existing_link["value"] += 1
            else:
                sankey_links.append(
                    {
                        "source": node_indices[pd_key],
                        "target": node_indices[proc_key],
                        "value": 1,
                    }
                )

            # Get legal bases from purposes and data transfers
            legal_bases = set()
            if pd.processing:
                for purpose in pd.processing.purposes.all():
                    if purpose.legal_basis:
                        legal_bases.add(purpose.legal_basis)
                for transfer in pd.processing.data_transfers.all():
                    if transfer.legal_basis:
                        legal_bases.add(transfer.legal_basis)

            # Link processing to legal bases (depth 2)
            for legal_basis in legal_bases:
                legal_key = f"legal_{legal_basis}"
                if legal_key not in node_indices:
                    node_indices[legal_key] = len(sankey_nodes)
                    sankey_nodes.append(
                        {"name": f"LegalBasis: {legal_basis}", "depth": 2}
                    )

                existing_link = next(
                    (
                        l
                        for l in sankey_links
                        if l["source"] == node_indices[proc_key]
                        and l["target"] == node_indices[legal_key]
                    ),
                    None,
                )
                if existing_link:
                    existing_link["value"] += 1
                else:
                    sankey_links.append(
                        {
                            "source": node_indices[proc_key],
                            "target": node_indices[legal_key],
                            "value": 1,
                        }
                    )

        return Response(
            {
                "countries": agg_countries(),
                "processings_count": processings_count,
                "recipients_count": recipients_count,
                "pd_categories": pd_categories,
                "pd_cat_count": total_categories,
                "open_right_requests_count": open_right_requests_count,
                "open_data_breaches_count": open_data_breaches_count,
                "breach_types": breach_type_data,
                "request_types": request_type_data,
                "sankey_nodes": sankey_nodes,
                "sankey_links": sankey_links,
            }
        )


class ProcessingNatureViewSet(BaseModelViewSet):
    model = ProcessingNature
    search_fields = ["name"]


class RightRequestViewSet(BaseModelViewSet):
    """
    API endpoint that allows right requests to be viewed or edited.
    """

    model = RightRequest
    filterset_fields = ["owner", "request_type", "status", "processings", "folder"]

    @action(detail=False, name="Get request type choices")
    def request_type(self, request):
        return Response(dict(RightRequest.REQUEST_TYPE_CHOICES))

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(RightRequest.STATUS_CHOICES))


class DataBreachViewSet(BaseModelViewSet):
    """
    API endpoint that allows data breaches to be viewed or edited.
    """

    model = DataBreach
    filterset_fields = [
        "folder",
        "breach_type",
        "risk_level",
        "status",
        "authorities",
        "affected_processings",
        "incident",
    ]

    @action(detail=False, name="Get breach type choices")
    def breach_type(self, request):
        return Response(dict(DataBreach.BREACH_TYPE_CHOICES))

    @action(detail=False, name="Get risk level choices")
    def risk_level(self, request):
        return Response(dict(DataBreach.RISK_LEVEL_CHOICES))

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(DataBreach.STATUS_CHOICES))
