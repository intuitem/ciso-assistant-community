"""
Serializers for Third Party Management API
"""

from rest_framework import serializers
from ..models import ThirdPartyEntity


class ThirdPartyEntitySerializer(serializers.ModelSerializer):
    """Serializer for ThirdPartyEntity aggregate"""
    class Meta:
        model = ThirdPartyEntity
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']
