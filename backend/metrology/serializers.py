from rest_framework import serializers

from core.serializers import BaseModelSerializer, ReferentialSerializer
from core.serializer_fields import FieldsRelatedField, PathField
from metrology.models import (
    MetricDefinition,
    MetricInstance,
    MetricSample,
    Dashboard,
    DashboardWidget,
)


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


# MetricSample serializers
class MetricSampleWriteSerializer(BaseModelSerializer):
    class Meta:
        model = MetricSample
        fields = "__all__"

    def validate_timestamp(self, value):
        """Prevent creating samples with future timestamps"""
        from django.utils import timezone

        if value > timezone.now():
            raise serializers.ValidationError(
                "Cannot create metric samples with future timestamps."
            )
        return value


class MetricSampleReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    metric_instance = FieldsRelatedField(["name", "ref_id", "id"])
    display_value = serializers.SerializerMethodField()

    class Meta:
        model = MetricSample
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
    class Meta:
        model = DashboardWidget
        fields = "__all__"

    def validate(self, data):
        """Validate widget grid positioning"""
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

    class Meta:
        model = DashboardWidget
        fields = "__all__"
