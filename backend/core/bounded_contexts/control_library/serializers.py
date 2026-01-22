"""
Serializers for Control Library bounded context
"""

from rest_framework import serializers
from .aggregates.control import Control
from .aggregates.policy import Policy
from .aggregates.evidence_item import EvidenceItem
from .associations.control_implementation import ControlImplementation
from .associations.policy_acknowledgement import PolicyAcknowledgement


class ControlSerializer(serializers.ModelSerializer):
    """Serializer for Control aggregate"""
    
    class Meta:
        model = Control
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'objective', 'ref_id',
            'control_type', 'domain',
            'lifecycle_state',
            'legalRequirementIds', 'relatedControlIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class PolicySerializer(serializers.ModelSerializer):
    """Serializer for Policy aggregate"""
    
    class Meta:
        model = Policy
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'title', 'policy_version', 'description',
            'lifecycle_state',
            'ownerUserIds', 'relatedControlIds', 'applicableOrgUnitIds',
            'publication_date', 'review_cadence_days',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class EvidenceItemSerializer(serializers.ModelSerializer):
    """Serializer for EvidenceItem aggregate"""
    
    class Meta:
        model = EvidenceItem
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description',
            'source_type', 'lifecycle_state',
            'uri', 'collected_at', 'expires_at',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ControlImplementationSerializer(serializers.ModelSerializer):
    """Serializer for ControlImplementation association"""
    
    class Meta:
        model = ControlImplementation
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'controlId', 'target_type', 'target_id',
            'lifecycle_state',
            'ownerUserIds', 'evidenceIds',
            'frequency', 'last_tested_at', 'effectiveness_rating',
            'notes',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class PolicyAcknowledgementSerializer(serializers.ModelSerializer):
    """Serializer for PolicyAcknowledgement association"""
    
    class Meta:
        model = PolicyAcknowledgement
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'policyId', 'policy_version', 'userId',
            'acknowledged_at', 'method',
            'notes',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

