"""
Serializers for ThirdPartyManagement bounded context
"""

from rest_framework import serializers
from .aggregates.third_party import ThirdParty


class ThirdPartySerializer(serializers.ModelSerializer):
    """Serializer for ThirdParty aggregate"""
    
    class Meta:
        model = ThirdParty
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description',
            'criticality', 'lifecycle_state',
            'serviceIds', 'contractIds',
            'assessmentRunIds', 'riskIds', 'controlImplementationIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

