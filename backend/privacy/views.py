from core.constants import COUNTRY_CHOICES
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import filters

from .models import (
    Purpose,
    PersonalData,
    DataSubject,
    DataRecipient,
    DataContractor,
    DataTransfer,
    Processing,
    LEGAL_BASIS_CHOICES,
)


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


class ProcessingViewSet(BaseModelViewSet):
    """
    API endpoint that allows processing activities to be viewed or edited.
    """

    model = Processing

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(Processing.STATUS_CHOICES))

    @action(detail=False, name="Get legal basis choices")
    def legal_basis(self, request):
        return Response(dict(LEGAL_BASIS_CHOICES))
