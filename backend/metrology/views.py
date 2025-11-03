from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import BaseModelViewSet, LONG_CACHE_TTL
from metrology.models import MetricDefinition, MetricInstance, MetricSample


class MetricDefinitionViewSet(BaseModelViewSet):
    """
    API endpoint that allows metric definitions to be viewed or edited.
    """

    model = MetricDefinition
    serializers_module = "metrology.serializers"
    filterset_fields = [
        "folder",
        "category",
        "library",
        "provider",
        "filtering_labels",
        "is_published",
    ]
    search_fields = ["name", "description", "ref_id", "provider"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(MetricDefinition.Category.choices))


class MetricInstanceViewSet(BaseModelViewSet):
    """
    API endpoint that allows metric instances to be viewed or edited.
    """

    model = MetricInstance
    serializers_module = "metrology.serializers"
    filterset_fields = [
        "folder",
        "metric_definition",
        "status",
        "collection_frequency",
        "owner",
        "filtering_labels",
    ]
    search_fields = ["name", "description", "ref_id"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(MetricInstance.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get collection frequency choices")
    def collection_frequency(self, request):
        return Response(dict(MetricInstance.Frequency.choices))


class MetricSampleViewSet(BaseModelViewSet):
    """
    API endpoint that allows metric samples to be viewed or edited.
    """

    model = MetricSample
    serializers_module = "metrology.serializers"
    filterset_fields = ["folder", "metric_instance"]
    search_fields = []
    ordering = ["-timestamp"]  # Most recent first
