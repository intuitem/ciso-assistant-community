from rest_framework import serializers

from core.serializers import BaseModelSerializer, ReferentialSerializer
from core.serializer_fields import FieldsRelatedField, PathField
from metrology.models import MetricDefinition, MetricInstance, MetricSample


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

    class Meta:
        model = MetricInstance
        fields = "__all__"


# MetricSample serializers
class MetricSampleWriteSerializer(BaseModelSerializer):
    class Meta:
        model = MetricSample
        fields = "__all__"


class MetricSampleReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    metric_instance = FieldsRelatedField(["name", "ref_id", "id"])

    class Meta:
        model = MetricSample
        fields = "__all__"
