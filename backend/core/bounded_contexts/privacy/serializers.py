"""
Serializers for Privacy bounded context
"""

from rest_framework import serializers
from .aggregates.data_asset import DataAsset
from .aggregates.data_flow import DataFlow


class DataAssetSerializer(serializers.ModelSerializer):
    """Serializer for DataAsset aggregate"""
    
    class Meta:
        model = DataAsset
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description',
            'data_categories', 'contains_personal_data', 'retention_policy',
            'lifecycle_state',
            'assetIds', 'ownerOrgUnitIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class DataFlowSerializer(serializers.ModelSerializer):
    """Serializer for DataFlow aggregate"""
    
    class Meta:
        model = DataFlow
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description', 'purpose',
            'source_system_asset_id', 'destination_system_asset_id',
            'lifecycle_state',
            'dataAssetIds', 'thirdPartyIds',
            'controlImplementationIds', 'privacyRiskIds',
            'transfer_mechanisms', 'encryption_in_transit',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

