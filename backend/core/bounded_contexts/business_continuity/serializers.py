"""
Serializers for BusinessContinuity bounded context
"""

from rest_framework import serializers
from .aggregates.business_continuity_plan import BusinessContinuityPlan
from .supporting_entities.bcp_task import BcpTask
from .supporting_entities.bcp_audit import BcpAudit


class BusinessContinuityPlanSerializer(serializers.ModelSerializer):
    """Serializer for BusinessContinuityPlan aggregate"""
    
    class Meta:
        model = BusinessContinuityPlan
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description',
            'lifecycle_state',
            'orgUnitIds', 'processIds', 'assetIds', 'serviceIds',
            'taskIds', 'auditIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class BcpTaskSerializer(serializers.ModelSerializer):
    """Serializer for BcpTask supporting entity"""
    
    class Meta:
        model = BcpTask
        fields = [
            'id', 'created_at', 'updated_at',
            'bcpId', 'title', 'description',
            'lifecycle_state',
            'owner_user_id', 'due_date',
            'evidenceIds',
            'tags',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BcpAuditSerializer(serializers.ModelSerializer):
    """Serializer for BcpAudit supporting entity"""
    
    class Meta:
        model = BcpAudit
        fields = [
            'id', 'created_at', 'updated_at',
            'bcpId', 'name', 'description',
            'lifecycle_state',
            'performed_at', 'outcome', 'notes',
            'evidenceIds',
            'tags',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

