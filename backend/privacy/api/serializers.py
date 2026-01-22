"""
Serializers for Privacy API
"""

from rest_framework import serializers
from ..models import DataAsset, ConsentRecord, DataSubjectRight


class DataAssetSerializer(serializers.ModelSerializer):
    """Serializer for DataAsset aggregate"""
    class Meta:
        model = DataAsset
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']


class ConsentRecordSerializer(serializers.ModelSerializer):
    """Serializer for ConsentRecord aggregate"""
    class Meta:
        model = ConsentRecord
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']


class DataSubjectRightSerializer(serializers.ModelSerializer):
    """Serializer for DataSubjectRight aggregate"""
    class Meta:
        model = DataSubjectRight
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']
