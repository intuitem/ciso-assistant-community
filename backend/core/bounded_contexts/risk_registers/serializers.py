"""
Serializers for Risk Registers bounded context
"""

from rest_framework import serializers
from .aggregates.asset_risk import AssetRisk
from .aggregates.third_party_risk import ThirdPartyRisk
from .aggregates.business_risk import BusinessRisk
from .supporting_entities.risk_treatment_plan import RiskTreatmentPlan
from .supporting_entities.risk_exception import RiskException


class AssetRiskSerializer(serializers.ModelSerializer):
    """Serializer for AssetRisk aggregate"""
    
    class Meta:
        model = AssetRisk
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'title', 'description', 'threat', 'vulnerability',
            'lifecycle_state',
            'assetIds', 'controlImplementationIds', 'exceptionIds', 'relatedRiskIds',
            'scoring', 'treatmentPlanId',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ThirdPartyRiskSerializer(serializers.ModelSerializer):
    """Serializer for ThirdPartyRisk aggregate"""

    class Meta:
        model = ThirdPartyRisk
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'title', 'description',
            'lifecycle_state',
            'thirdPartyIds', 'serviceIds', 'controlImplementationIds',
            'assessmentRunIds', 'exceptionIds',
            'scoring', 'treatmentPlanId',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class BusinessRiskSerializer(serializers.ModelSerializer):
    """Serializer for BusinessRisk aggregate"""

    class Meta:
        model = BusinessRisk
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'title', 'description',
            'lifecycle_state',
            'processIds', 'orgUnitIds', 'controlImplementationIds', 'exceptionIds',
            'scoring', 'treatmentPlanId',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class RiskTreatmentPlanSerializer(serializers.ModelSerializer):
    """Serializer for RiskTreatmentPlan supporting entity"""
    
    class Meta:
        model = RiskTreatmentPlan
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'riskId', 'name', 'description',
            'strategy', 'lifecycle_state',
            'tasks', 'started_at', 'completed_at',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class RiskExceptionSerializer(serializers.ModelSerializer):
    """Serializer for RiskException supporting entity"""
    
    class Meta:
        model = RiskException
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'riskId', 'reason', 'description',
            'lifecycle_state',
            'approved_by_user_id', 'approved_at',
            'expires_at',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

