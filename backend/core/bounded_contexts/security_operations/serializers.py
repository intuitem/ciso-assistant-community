"""
Serializers for SecurityOperations bounded context
"""

from rest_framework import serializers
from .aggregates.security_incident import SecurityIncident
from .aggregates.awareness_program import AwarenessProgram
from .associations.awareness_campaign import AwarenessCampaign
from .associations.awareness_completion import AwarenessCompletion


class SecurityIncidentSerializer(serializers.ModelSerializer):
    """Serializer for SecurityIncident aggregate"""
    
    class Meta:
        model = SecurityIncident
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'title', 'description',
            'classification_id',
            'lifecycle_state', 'severity', 'detection_source',
            'affectedAssetIds', 'affectedServiceIds',
            'relatedRiskIds', 'evidenceIds',
            'timeline',
            'reported_at', 'triaged_at', 'contained_at',
            'eradicated_at', 'recovered_at', 'closed_at',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class AwarenessProgramSerializer(serializers.ModelSerializer):
    """Serializer for AwarenessProgram aggregate"""
    
    class Meta:
        model = AwarenessProgram
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description',
            'lifecycle_state',
            'audienceOrgUnitIds', 'policyIds', 'campaignIds',
            'cadence_days',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class AwarenessCampaignSerializer(serializers.ModelSerializer):
    """Serializer for AwarenessCampaign association"""
    
    class Meta:
        model = AwarenessCampaign
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'programId', 'name', 'description',
            'lifecycle_state',
            'start_date', 'end_date',
            'targetUserIds', 'completionIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class AwarenessCompletionSerializer(serializers.ModelSerializer):
    """Serializer for AwarenessCompletion association"""
    
    class Meta:
        model = AwarenessCompletion
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'campaignId', 'userId',
            'status',
            'completed_at', 'score', 'notes',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

