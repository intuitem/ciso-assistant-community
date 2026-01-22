"""
Serializers for Asset and Service bounded context
"""

from rest_framework import serializers
from .aggregates.asset import Asset
from .aggregates.service import Service
from .aggregates.process import Process
from .associations.service_contract import ServiceContract


class AssetSerializer(serializers.ModelSerializer):
    """Serializer for Asset aggregate"""
    
    class Meta:
        model = Asset
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description', 'ref_id',
            'asset_type', 'lifecycle_state',
            'assetClassificationId',
            'assetLabelIds', 'businessOwnerOrgUnitIds', 'systemOwnerUserIds',
            'processIds', 'dataAssetIds', 'serviceIds', 'thirdPartyIds',
            'controlIds', 'riskIds',
            'business_value', 'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ServiceSerializer(serializers.ModelSerializer):
    """Serializer for Service aggregate"""
    
    class Meta:
        model = Service
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description', 'ref_id',
            'serviceClassificationId', 'lifecycle_state',
            'assetIds', 'thirdPartyIds', 'controlIds', 'riskIds', 'contractIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ProcessSerializer(serializers.ModelSerializer):
    """Serializer for Process aggregate"""
    
    class Meta:
        model = Process
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description', 'ref_id',
            'lifecycle_state',
            'orgUnitIds', 'assetIds', 'controlIds', 'riskIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ServiceContractSerializer(serializers.ModelSerializer):
    """Serializer for ServiceContract association"""
    
    class Meta:
        model = ServiceContract
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'serviceId', 'thirdPartyId',
            'lifecycle_state',
            'start_date', 'end_date', 'renewal_date',
            'key_terms', 'notes',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

