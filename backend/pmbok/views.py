from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import BaseModelViewSet
from pmbok.models import GenericCollection, Accreditation

LONG_CACHE_TTL = 60  # mn


class GenericCollectionViewSet(BaseModelViewSet):
    """
    API endpoint that allows generic collections to be viewed or edited.
    """

    model = GenericCollection
    serializers_module = "pmbok.serializers"
    filterset_fields = [
        "folder",
        "compliance_assessments",
        "risk_assessments",
        "crq_studies",
        "ebios_studies",
        "entity_assessments",
        "findings_assessments",
        "documents",
        "security_exceptions",
        "policies",
        "filtering_labels",
    ]
    search_fields = ["name", "description", "ref_id"]
    ordering = ["created_at"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Generic Collection status choices")
    def status(self, request):
        # Add status choices if needed in the future
        return Response({})


class AccreditationViewSet(BaseModelViewSet):
    """
    API endpoint that allows accreditations to be viewed or edited.
    """

    model = Accreditation
    serializers_module = "pmbok.serializers"
    filterset_fields = [
        "folder",
        "status",
        "category",
        "author",
        "authority",
        "linked_collection",
        "checklist",
        "filtering_labels",
    ]
    search_fields = ["name", "description", "ref_id", "authority"]
    ordering = ["created_at"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Accreditation status choices")
    def status(self, request):
        return Response(dict(Accreditation.STATUS_CHOICES))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get Accreditation category choices")
    def category(self, request):
        return Response(dict(Accreditation.CATEGORY_CHOICES))
