"""
Serializers for Security Operations API
"""

from rest_framework import serializers
from ..models import SecurityIncident


class SecurityIncidentSerializer(serializers.ModelSerializer):
    """Serializer for SecurityIncident aggregate"""
    class Meta:
        model = SecurityIncident
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']
