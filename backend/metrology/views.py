import uuid

from django.contrib.contenttypes.models import ContentType
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import BaseModelViewSet, LONG_CACHE_TTL
from iam.models import RoleAssignment
from metrology.models import (
    MetricDefinition,
    MetricInstance,
    CustomMetricSample,
    BuiltinMetricSample,
    Dashboard,
    DashboardWidget,
)
from metrology.builtin_metrics import BUILTIN_METRICS, METRIC_TYPE_CHART_TYPES
from metrology.serializers import BuiltinMetricSampleReadSerializer


def _user_can_read_target(user, content_type, object_id):
    target_model = content_type.model_class()
    if target_model is None:
        return False
    try:
        object_uuid = (
            object_id if isinstance(object_id, uuid.UUID) else uuid.UUID(str(object_id))
        )
    except (ValueError, TypeError):
        return False
    try:
        return RoleAssignment.is_object_readable(user, target_model, object_uuid)
    except NotImplementedError:
        return False


class MetricDefinitionViewSet(BaseModelViewSet):
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
    model = MetricInstance
    serializers_module = "metrology.serializers"
    filterset_fields = [
        "folder",
        "metric_definition",
        "status",
        "collection_frequency",
        "owner",
        "filtering_labels",
        "organisation_objectives",
        "evidences",
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
    model = CustomMetricSample
    serializers_module = "metrology.serializers"
    filterset_fields = ["folder", "metric_instance", "evidence_revision"]
    search_fields = ["observation"]
    ordering = ["-timestamp"]  # Most recent first


class DashboardViewSet(BaseModelViewSet):
    model = Dashboard
    serializers_module = "metrology.serializers"
    filterset_fields = ["folder", "filtering_labels"]
    search_fields = ["name", "description", "ref_id"]


class DashboardWidgetViewSet(BaseModelViewSet):
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
    model = BuiltinMetricSample
    serializers_module = "metrology.serializers"
    filterset_fields = ["content_type", "object_id", "date"]
    search_fields = []
    ordering = ["-date"]

    def get_queryset(self):
        queryset = super().get_queryset()
        # ?model=ComplianceAssessment maps to a ContentType filter.
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
        # chart_types are derived per-metric from each metric's declared type.
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
        # Query params: object_id + (content_type_id | model).
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

        if not _user_can_read_target(request.user, content_type, object_id):
            return Response(
                {"error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        samples = BuiltinMetricSample.objects.filter(
            content_type=content_type, object_id=object_id
        ).order_by("-date")

        serializer = BuiltinMetricSampleReadSerializer(samples, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], name="Refresh metrics for object")
    def refresh(self, request):
        # Body: object_id + (content_type_id | model).
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

        if not _user_can_read_target(request.user, content_type, object_id):
            return Response(
                {"error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        model_class = content_type.model_class()
        try:
            obj = model_class.objects.get(id=object_id)
        except model_class.DoesNotExist:
            return Response(
                {"error": "Object not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        sample, created = BuiltinMetricSample.update_or_create_snapshot(obj)
        serializer = BuiltinMetricSampleReadSerializer(sample)
        return Response(
            {
                "created": created,
                "sample": serializer.data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
