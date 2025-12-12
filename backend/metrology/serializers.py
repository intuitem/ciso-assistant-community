from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from core.serializers import BaseModelSerializer, ReferentialSerializer
from core.serializer_fields import FieldsRelatedField, PathField
from metrology.models import (
    MetricDefinition,
    MetricInstance,
    CustomMetricSample,
    BuiltinMetricSample,
    Dashboard,
    DashboardWidget,
)
from metrology.builtin_metrics import get_available_metrics_for_model


# MetricDefinition serializers
class MetricDefinitionWriteSerializer(BaseModelSerializer):
    class Meta:
        model = MetricDefinition
        exclude = ["translations"]


class MetricDefinitionReadSerializer(ReferentialSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    library = FieldsRelatedField(["name", "id"])
    unit = FieldsRelatedField(["name", "id"])
    filtering_labels = FieldsRelatedField(["folder"], many=True)

    class Meta:
        model = MetricDefinition
        exclude = ["translations"]


# MetricInstance serializers
class MetricInstanceWriteSerializer(BaseModelSerializer):
    class Meta:
        model = MetricInstance
        fields = "__all__"


class MetricInstanceReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    metric_definition = FieldsRelatedField(
        [
            "name",
            "ref_id",
            "id",
            "category",
            "unit",
            "choices_definition",
            "higher_is_better",
        ]
    )
    owner = FieldsRelatedField(many=True)
    filtering_labels = FieldsRelatedField(["folder"], many=True)
    status = serializers.CharField(source="get_status_display", read_only=True)
    collection_frequency = serializers.CharField(
        source="get_collection_frequency_display", read_only=True
    )
    current_value = serializers.SerializerMethodField()

    class Meta:
        model = MetricInstance
        fields = "__all__"

    def get_current_value(self, obj):
        """Get the current value from the latest sample"""
        return obj.current_value()


# CustomMetricSample serializers
class CustomMetricSampleWriteSerializer(BaseModelSerializer):
    class Meta:
        model = CustomMetricSample
        fields = "__all__"

    def validate_timestamp(self, value):
        """Prevent creating samples with future timestamps"""
        from django.utils import timezone

        if value > timezone.now():
            raise serializers.ValidationError(
                "Cannot create metric samples with future timestamps."
            )
        return value


class CustomMetricSampleReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    metric_instance = FieldsRelatedField(["name", "ref_id", "id"])
    display_value = serializers.SerializerMethodField()

    class Meta:
        model = CustomMetricSample
        fields = "__all__"

    def get_display_value(self, obj):
        """Get the human-readable display value"""
        return obj.display_value()


# Dashboard serializers
class DashboardWriteSerializer(BaseModelSerializer):
    class Meta:
        model = Dashboard
        fields = "__all__"


class DashboardReadSerializer(BaseModelSerializer):
    path = PathField(read_only=True)
    folder = FieldsRelatedField()
    filtering_labels = FieldsRelatedField(["folder"], many=True)
    widget_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dashboard
        fields = "__all__"


# DashboardWidget serializers
class DashboardWidgetWriteSerializer(BaseModelSerializer):
    # Accept model name and convert to ContentType
    target_model = serializers.CharField(
        write_only=True, required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = DashboardWidget
        fields = "__all__"
        extra_kwargs = {
            "target_content_type": {"required": False},
            "target_object_id": {"required": False},
            "metric_key": {"required": False},
            "metric_instance": {"required": False},
        }

    def get_fields(self):
        fields = super().get_fields()
        # Ensure target_model is included
        fields["target_model"] = serializers.CharField(
            write_only=True, required=False, allow_blank=True, allow_null=True
        )
        return fields

    def validate(self, data):
        """Validate widget grid positioning and convert target_model to target_content_type"""
        position_x = data.get("position_x", 0)
        width = data.get("width", 6)
        height = data.get("height", 2)

        if position_x < 0 or position_x > 11:
            raise serializers.ValidationError(
                {"position_x": "Position X must be between 0 and 11"}
            )
        if width < 1 or width > 12:
            raise serializers.ValidationError(
                {"width": "Width must be between 1 and 12"}
            )
        if position_x + width > 12:
            raise serializers.ValidationError(
                {"width": "Widget exceeds grid boundary (position_x + width > 12)"}
            )
        if height < 1:
            raise serializers.ValidationError({"height": "Height must be at least 1"})

        # Convert target_model to target_content_type
        target_model = data.pop("target_model", None)
        if target_model:  # Only process if not empty/null
            from django.contrib.contenttypes.models import ContentType

            try:
                content_type = ContentType.objects.get(model=target_model.lower())
                data["target_content_type"] = content_type
            except ContentType.DoesNotExist:
                raise serializers.ValidationError(
                    {"target_model": f"Unknown model: {target_model}"}
                )

        # Clean up empty builtin fields to avoid validation issues
        # If metric_key is empty string, set to None
        if data.get("metric_key") == "":
            data["metric_key"] = None
        # If target_object_id is empty string, set to None
        if data.get("target_object_id") == "":
            data["target_object_id"] = None

        return data


class DashboardWidgetReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    dashboard = FieldsRelatedField(["name", "id"])
    metric_instance = FieldsRelatedField(
        [
            "name",
            "ref_id",
            "id",
            "target_value",
            {
                "metric_definition": [
                    "name",
                    "id",
                    "category",
                    {"unit": ["name", "id"]},
                    "choices_definition",
                    "higher_is_better",
                ]
            },
        ]
    )
    display_title = serializers.CharField(read_only=True)
    chart_type_display = serializers.CharField(
        source="get_chart_type_display", read_only=True
    )
    time_range_display = serializers.CharField(
        source="get_time_range_display", read_only=True
    )
    aggregation_display = serializers.CharField(
        source="get_aggregation_display", read_only=True
    )
    is_builtin_metric = serializers.BooleanField(read_only=True)
    is_custom_metric = serializers.BooleanField(read_only=True)
    target_content_type_display = serializers.SerializerMethodField()
    target_object_name = serializers.SerializerMethodField()

    class Meta:
        model = DashboardWidget
        fields = "__all__"

    def get_target_content_type_display(self, obj):
        """Get the content type model name for builtin metrics"""
        if obj.target_content_type:
            return obj.target_content_type.model.title()
        return None

    def get_target_object_name(self, obj):
        """Get the name of the target object for builtin metrics"""
        if obj.target_content_type and obj.target_object_id:
            try:
                model_class = obj.target_content_type.model_class()
                target_obj = model_class.objects.get(id=obj.target_object_id)
                return str(target_obj)
            except (model_class.DoesNotExist, AttributeError):
                return None
        return None


# BuiltinMetricSample serializers
class BuiltinMetricSampleWriteSerializer(BaseModelSerializer):
    """
    Write serializer for BuiltinMetricSample.
    Generally not used directly as samples are system-generated.
    """

    class Meta:
        model = BuiltinMetricSample
        fields = "__all__"


class BuiltinMetricSampleReadSerializer(BaseModelSerializer):
    """Read serializer for BuiltinMetricSample with enriched data."""

    content_type_display = serializers.SerializerMethodField()
    object_name = serializers.SerializerMethodField()
    available_metrics = serializers.SerializerMethodField()

    class Meta:
        model = BuiltinMetricSample
        fields = [
            "id",
            "content_type",
            "content_type_display",
            "object_id",
            "object_name",
            "date",
            "metrics",
            "available_metrics",
            "created_at",
            "updated_at",
        ]

    def get_content_type_display(self, obj):
        """Get the human-readable content type name"""
        return obj.content_type.model.title()

    def get_object_name(self, obj):
        """Get the name of the target object"""
        try:
            target_obj = obj.object
            if target_obj:
                return str(target_obj)
        except Exception:
            pass
        return None

    def get_available_metrics(self, obj):
        """Get the list of available metrics for this object type"""
        model_name = obj.content_type.model_class().__name__
        metrics = get_available_metrics_for_model(model_name)
        return {
            key: {
                "label": str(meta["label"]),
                "type": meta["type"],
                "description": str(meta["description"]),
            }
            for key, meta in metrics.items()
        }
