"""
Serializers for Compliance bounded context
"""

from rest_framework import serializers
from .aggregates.compliance_framework import ComplianceFramework
from .aggregates.requirement import Requirement
from .aggregates.online_assessment import OnlineAssessment
from .associations.assessment_run import AssessmentRun
from .associations.compliance_audit import ComplianceAudit
from .associations.compliance_finding import ComplianceFinding
from .associations.compliance_exception import ComplianceException


class ComplianceFrameworkSerializer(serializers.ModelSerializer):
    """Serializer for ComplianceFramework aggregate"""
    
    class Meta:
        model = ComplianceFramework
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'version', 'description',
            'lifecycle_state',
            'requirementIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class RequirementSerializer(serializers.ModelSerializer):
    """Serializer for Requirement aggregate"""
    
    class Meta:
        model = Requirement
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'frameworkId', 'code', 'statement', 'description',
            'lifecycle_state',
            'mappedControlIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class OnlineAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for OnlineAssessment aggregate"""
    
    class Meta:
        model = OnlineAssessment
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description',
            'questionnaireId', 'target_type',
            'scoring_model',
            'lifecycle_state',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class AssessmentRunSerializer(serializers.ModelSerializer):
    """Serializer for AssessmentRun association"""
    
    class Meta:
        model = AssessmentRun
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'assessmentId', 'target_type', 'target_id',
            'lifecycle_state',
            'invitedUserIds', 'respondentUserIds',
            'findingIds', 'evidenceIds',
            'started_at', 'submitted_at', 'score',
            'answers', 'notes',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ComplianceAuditSerializer(serializers.ModelSerializer):
    """Serializer for ComplianceAudit association"""
    
    class Meta:
        model = ComplianceAudit
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description',
            'lifecycle_state',
            'scopeFrameworkIds', 'scopeRequirementIds',
            'auditor_org', 'start_date', 'end_date',
            'findingIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ComplianceFindingSerializer(serializers.ModelSerializer):
    """Serializer for ComplianceFinding association"""
    
    class Meta:
        model = ComplianceFinding
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'title', 'description',
            'source_type', 'source_id',
            'lifecycle_state', 'severity',
            'requirementIds', 'controlImplementationIds',
            'remediationTaskIds', 'evidenceIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ComplianceExceptionSerializer(serializers.ModelSerializer):
    """Serializer for ComplianceException association"""
    
    class Meta:
        model = ComplianceException
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'requirementId', 'reason', 'description',
            'lifecycle_state',
            'approved_by_user_id', 'expires_at',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

