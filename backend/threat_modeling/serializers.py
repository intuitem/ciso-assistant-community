from rest_framework import serializers

from core.serializers import BaseModelSerializer, FieldsRelatedField
from .models import ThreatModel


class ThreatModelWriteSerializer(BaseModelSerializer):
    class Meta:
        model = ThreatModel
        fields = "__all__"


class ThreatModelReadSerializer(BaseModelSerializer):
    folder = FieldsRelatedField()
    catalog = FieldsRelatedField()
    risk_scenarios = FieldsRelatedField(many=True)
    node_count = serializers.IntegerField(source="nodes.count", read_only=True)

    class Meta:
        model = ThreatModel
        fields = "__all__"
