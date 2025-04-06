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
    filterset_fields = ["processing"]


class PersonalDataViewSet(BaseModelViewSet):
    """
    API endpoint that allows personal data to be viewed or edited.
    """

    model = PersonalData
    filterset_fields = ["processing"]

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

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(Processing.STATUS_CHOICES))

    @action(detail=False, name="Get legal basis choices")
    def legal_basis(self, request):
        return Response(dict(LEGAL_BASIS_CHOICES))

    @action(detail=False, name="processing metrics")
    def metrics(self, request, pk=None):
        return Response({})

    @action(detail=False, name="aggregated metrics")
    def agg_metrics(self, request):
        # <Card icon="fa-solid fa-circle-exclamation" text="Incidents" count={data.data.privacy_incidents} />

        incidents = 123
        pd_categories = PersonalData.get_categories_count()
        total_categories = len(pd_categories)
        processings_count = Processing.objects.all().count()
        recipients_count = DataRecipient.objects.all().count()
        return Response(
            {
                "countries": agg_countries(),
                "processings_count": processings_count,
                "recipients_count": recipients_count,
                "pd_categories": pd_categories,
                "pd_cat_count": total_categories,
            }
        )


class ProcessingNatureViewSet(BaseModelViewSet):
    model = ProcessingNature
    search_fields = ["name"]
