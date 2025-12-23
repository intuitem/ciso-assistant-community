from django.contrib.contenttypes.models import ContentType
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import BaseModelViewSet, LONG_CACHE_TTL
from metrology.models import (
    MetricDefinition,
    MetricInstance,
    CustomMetricSample,
    BuiltinMetricSample,
    Dashboard,
    DashboardWidget,
)
from metrology.builtin_metrics import BUILTIN_METRICS, get_available_metrics_for_model


class MetricDefinitionViewSet(BaseModelViewSet):
    """
    API endpoint that allows metric definitions to be viewed or edited.
    """

    model = MetricDefinition
    serializers_module = "metrology.serializers"
    filterset_fields = [
        "folder",
        "category",
        "unit",
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

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        providers = (
            MetricDefinition.objects.exclude(provider__isnull=True)
            .exclude(provider="")
            .values_list("provider", flat=True)
            .distinct()
            .order_by("provider")
        )
        return Response({p: p for p in providers})


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


class CustomMetricSampleViewSet(BaseModelViewSet):
    """
    API endpoint that allows custom metric samples to be viewed or edited.
    """

    model = CustomMetricSample
    serializers_module = "metrology.serializers"
    filterset_fields = ["folder", "metric_instance"]
    search_fields = []
    ordering = ["-timestamp"]  # Most recent first


class DashboardViewSet(BaseModelViewSet):
    """
    API endpoint that allows dashboards to be viewed or edited.
    """

    model = Dashboard
    serializers_module = "metrology.serializers"
    filterset_fields = ["folder", "filtering_labels"]
    search_fields = ["name", "description", "ref_id"]


class DashboardWidgetViewSet(BaseModelViewSet):
    """
    API endpoint that allows dashboard widgets to be viewed or edited.
    """

    model = DashboardWidget
    serializers_module = "metrology.serializers"
    filterset_fields = [
        "folder",
        "dashboard",
        "metric_instance",
        "chart_type",
        "time_range",
        "aggregation",
    ]
    search_fields = ["title"]
    ordering = ["position_y", "position_x"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get chart type choices")
    def chart_type(self, request):
        return Response(dict(DashboardWidget.ChartType.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get time range choices")
    def time_range(self, request):
        return Response(dict(DashboardWidget.TimeRange.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get aggregation choices")
    def aggregation(self, request):
        return Response(dict(DashboardWidget.Aggregation.choices))


class BuiltinMetricSampleViewSet(BaseModelViewSet):
    """
    API endpoint that allows builtin metric samples to be viewed.
    These are system-computed metrics for objects like ComplianceAssessment,
    RiskAssessment, FindingsAssessment, and Folder.
    """

    model = BuiltinMetricSample
    serializers_module = "metrology.serializers"
    filterset_fields = ["content_type", "object_id", "date"]
    search_fields = []
    ordering = ["-date"]

    def get_queryset(self):
        """
        Optionally filter by content_type model name.
        """
        queryset = super().get_queryset()

        # Allow filtering by model name (e.g., ?model=ComplianceAssessment)
        model_name = self.request.query_params.get("model")
        if model_name:
            try:
                content_type = ContentType.objects.get(model=model_name.lower())
                queryset = queryset.filter(content_type=content_type)
            except ContentType.DoesNotExist:
                queryset = queryset.none()

        return queryset

    @action(detail=False, methods=["get"], name="Get supported models")
    def supported_models(self, request):
        """
        Returns list of models that support builtin metrics with their available metrics.
        Includes chart_types for each metric based on the metric type.
        """
        from .builtin_metrics import METRIC_TYPE_CHART_TYPES

        result = {}
        for model_name, metrics in BUILTIN_METRICS.items():
            result[model_name] = {
                key: {
                    "label": str(meta["label"]),
                    "type": meta["type"],
                    "description": str(meta["description"]),
                    "chart_types": METRIC_TYPE_CHART_TYPES.get(meta["type"], []),
                }
                for key, meta in metrics.items()
            }
        return Response(result)

    @action(detail=False, methods=["get"], name="Get metrics for object")
    def for_object(self, request):
        """
        Get all metric samples for a specific object.
        Query params:
        - content_type_id: The ContentType ID
        - object_id: The object's UUID
        - OR -
        - model: Model name (e.g., ComplianceAssessment)
        - object_id: The object's UUID
        """
        object_id = request.query_params.get("object_id")
        if not object_id:
            return Response(
                {"error": "object_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type_id = request.query_params.get("content_type_id")
        model_name = request.query_params.get("model")

        if content_type_id:
            content_type = ContentType.objects.filter(id=content_type_id).first()
        elif model_name:
            content_type = ContentType.objects.filter(model=model_name.lower()).first()
        else:
            return Response(
                {"error": "content_type_id or model is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not content_type:
            return Response(
                {"error": "Content type not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        samples = BuiltinMetricSample.objects.filter(
            content_type=content_type, object_id=object_id
        ).order_by("-date")

        from metrology.serializers import BuiltinMetricSampleReadSerializer

        serializer = BuiltinMetricSampleReadSerializer(samples, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], name="Refresh metrics for object")
    def refresh(self, request):
        """
        Force refresh metrics for a specific object.
        Body:
        - content_type_id: The ContentType ID
        - object_id: The object's UUID
        - OR -
        - model: Model name (e.g., ComplianceAssessment)
        - object_id: The object's UUID
        """
        object_id = request.data.get("object_id")
        if not object_id:
            return Response(
                {"error": "object_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type_id = request.data.get("content_type_id")
        model_name = request.data.get("model")

        if content_type_id:
            content_type = ContentType.objects.filter(id=content_type_id).first()
        elif model_name:
            content_type = ContentType.objects.filter(model=model_name.lower()).first()
        else:
            return Response(
                {"error": "content_type_id or model is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not content_type:
            return Response(
                {"error": "Content type not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get the actual object
        model_class = content_type.model_class()
        try:
            obj = model_class.objects.get(id=object_id)
        except model_class.DoesNotExist:
            return Response(
                {"error": "Object not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update or create the snapshot
        sample, created = BuiltinMetricSample.update_or_create_snapshot(obj)

        from metrology.serializers import BuiltinMetricSampleReadSerializer

        serializer = BuiltinMetricSampleReadSerializer(sample)
        return Response(
            {
                "created": created,
                "sample": serializer.data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
