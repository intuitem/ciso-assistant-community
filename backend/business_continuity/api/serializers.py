"""
Serializers for Business Continuity API
"""

from rest_framework import serializers
from ..models import BCPPlan


class BCPPlanSerializer(serializers.ModelSerializer):
    """Serializer for BCPPlan aggregate"""
    class Meta:
        model = BCPPlan
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']
