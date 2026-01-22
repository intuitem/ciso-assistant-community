"""
Serializers for Compliance API
"""

from rest_framework import serializers
from ..models import ComplianceAssessment, RequirementAssessment, ComplianceFinding, ComplianceException


class ComplianceAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for ComplianceAssessment aggregate"""
    class Meta:
        model = ComplianceAssessment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']


class RequirementAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for RequirementAssessment aggregate"""
    class Meta:
        model = RequirementAssessment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']


class ComplianceFindingSerializer(serializers.ModelSerializer):
    """Serializer for ComplianceFinding aggregate"""
    class Meta:
        model = ComplianceFinding
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']


class ComplianceExceptionSerializer(serializers.ModelSerializer):
    """Serializer for ComplianceException aggregate"""
    class Meta:
        model = ComplianceException
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']
