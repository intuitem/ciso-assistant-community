from rest_framework import serializers

from core.serializers import BaseModelSerializer, ReferentialSerializer
from core.serializer_fields import FieldsRelatedField, PathField
from metrology.models import MetricDefinition, MetricInstance, MetricSample, Dashboard


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
        ["name", "ref_id", "id", "category", "unit", "choices_definition"]
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
    metric_instances = FieldsRelatedField(["name", "ref_id", "id"], many=True)
    filtering_labels = FieldsRelatedField(["folder"], many=True)

    class Meta:
        model = Dashboard
        fields = "__all__"
