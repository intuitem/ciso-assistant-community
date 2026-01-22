"""
Views for Compliance API
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import RBACPermissions

from ..models import ComplianceAssessment, RequirementAssessment, ComplianceFinding, ComplianceException
from .serializers import (
    ComplianceAssessmentSerializer,
    RequirementAssessmentSerializer,
    ComplianceFindingSerializer,
    ComplianceExceptionSerializer
)


class ComplianceAssessmentViewSet(viewsets.ModelViewSet):
    """ViewSet for ComplianceAssessment aggregates"""
    queryset = ComplianceAssessment.objects.all()
    serializer_class = ComplianceAssessmentSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'primary_framework', 'target_type', 'priority']


class RequirementAssessmentViewSet(viewsets.ModelViewSet):
    """ViewSet for RequirementAssessment aggregates"""
    queryset = RequirementAssessment.objects.all()
    serializer_class = RequirementAssessmentSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'assessment_result', 'framework', 'assessor_user_id']


class ComplianceFindingViewSet(viewsets.ModelViewSet):
    """ViewSet for ComplianceFinding aggregates"""
    queryset = ComplianceFinding.objects.all()
    serializer_class = ComplianceFindingSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'severity', 'finding_type', 'remediation_owner_user_id']


class ComplianceExceptionViewSet(viewsets.ModelViewSet):
    """ViewSet for ComplianceException aggregates"""
    queryset = ComplianceException.objects.all()
    serializer_class = ComplianceExceptionSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'exception_type', 'approved_by_user_id', 'end_date']
