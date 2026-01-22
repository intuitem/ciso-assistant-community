"""
API Views for Compliance bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .aggregates.compliance_framework import ComplianceFramework
from .aggregates.requirement import Requirement
from .aggregates.online_assessment import OnlineAssessment
from .associations.assessment_run import AssessmentRun
from .associations.compliance_audit import ComplianceAudit
from .associations.compliance_finding import ComplianceFinding
from .associations.compliance_exception import ComplianceException
from .serializers import (
    ComplianceFrameworkSerializer,
    RequirementSerializer,
    OnlineAssessmentSerializer,
    AssessmentRunSerializer,
    ComplianceAuditSerializer,
    ComplianceFindingSerializer,
    ComplianceExceptionSerializer,
)


class ComplianceFrameworkViewSet(viewsets.ModelViewSet):
    """ViewSet for ComplianceFramework aggregates"""
    
    queryset = ComplianceFramework.objects.all()
    serializer_class = ComplianceFrameworkSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['name', 'version', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a framework"""
        framework = self.get_object()
        framework.activate()
        framework.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire a framework"""
        framework = self.get_object()
        framework.retire()
        framework.save()
        return Response({'status': 'retired'})


class RequirementViewSet(viewsets.ModelViewSet):
    """ViewSet for Requirement aggregates"""
    
    queryset = Requirement.objects.all()
    serializer_class = RequirementSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['frameworkId', 'lifecycle_state']
    search_fields = ['code', 'statement', 'description']
    ordering_fields = ['code', 'created_at']
    ordering = ['code']
    
    @action(detail=True, methods=['post'])
    def map_to_control(self, request, pk=None):
        """Map a requirement to a control"""
        requirement = self.get_object()
        control_id = request.data.get('control_id')
        if control_id:
            requirement.map_to_control(control_id)
            requirement.save()
            return Response({'status': 'mapped'})
        return Response({'error': 'control_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire a requirement"""
        requirement = self.get_object()
        requirement.retire()
        requirement.save()
        return Response({'status': 'retired'})


class OnlineAssessmentViewSet(viewsets.ModelViewSet):
    """ViewSet for OnlineAssessment aggregates"""
    
    queryset = OnlineAssessment.objects.all()
    serializer_class = OnlineAssessmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'target_type']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish an assessment"""
        assessment = self.get_object()
        assessment.publish()
        assessment.save()
        return Response({'status': 'published'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire an assessment"""
        assessment = self.get_object()
        assessment.retire()
        assessment.save()
        return Response({'status': 'retired'})


class AssessmentRunViewSet(viewsets.ModelViewSet):
    """ViewSet for AssessmentRun associations"""
    
    queryset = AssessmentRun.objects.all()
    serializer_class = AssessmentRunSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['assessmentId', 'target_type', 'lifecycle_state']
    search_fields = ['notes']
    ordering_fields = ['created_at', 'submitted_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start an assessment run"""
        run = self.get_object()
        respondent_user_id = request.data.get('respondent_user_id')
        if respondent_user_id:
            run.start(respondent_user_id)
            run.save()
            return Response({'status': 'started'})
        return Response({'error': 'respondent_user_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit an assessment run"""
        run = self.get_object()
        answers = request.data.get('answers')
        score = request.data.get('score')
        run.submit(answers, score)
        run.save()
        return Response({'status': 'submitted'})
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Review an assessment run"""
        run = self.get_object()
        run.review()
        run.save()
        return Response({'status': 'reviewed'})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an assessment run"""
        run = self.get_object()
        run.close()
        run.save()
        return Response({'status': 'closed'})


class ComplianceAuditViewSet(viewsets.ModelViewSet):
    """ViewSet for ComplianceAudit associations"""
    
    queryset = ComplianceAudit.objects.all()
    serializer_class = ComplianceAuditSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['name', 'description', 'auditor_org']
    ordering_fields = ['start_date', 'created_at']
    ordering = ['-start_date']
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start an audit"""
        audit = self.get_object()
        audit.start()
        audit.save()
        return Response({'status': 'started'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete an audit"""
        from datetime import date
        audit = self.get_object()
        end_date = request.data.get('end_date')
        end_date_obj = None
        if end_date:
            from datetime import datetime
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        audit.complete(end_date_obj)
        audit.save()
        return Response({'status': 'completed'})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an audit"""
        audit = self.get_object()
        audit.close()
        audit.save()
        return Response({'status': 'closed'})


class ComplianceFindingViewSet(viewsets.ModelViewSet):
    """ViewSet for ComplianceFinding associations"""
    
    queryset = ComplianceFinding.objects.all()
    serializer_class = ComplianceFindingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['source_type', 'lifecycle_state', 'severity']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'severity']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def triage(self, request, pk=None):
        """Triage a finding"""
        finding = self.get_object()
        finding.triage()
        finding.save()
        return Response({'status': 'triaged'})
    
    @action(detail=True, methods=['post'])
    def start_remediation(self, request, pk=None):
        """Start remediating a finding"""
        finding = self.get_object()
        finding.start_remediation()
        finding.save()
        return Response({'status': 'remediation_started'})
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a finding is resolved"""
        finding = self.get_object()
        finding.verify()
        finding.save()
        return Response({'status': 'verified'})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a finding"""
        finding = self.get_object()
        finding.close()
        finding.save()
        return Response({'status': 'closed'})


class ComplianceExceptionViewSet(viewsets.ModelViewSet):
    """ViewSet for ComplianceException associations"""
    
    queryset = ComplianceException.objects.all()
    serializer_class = ComplianceExceptionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['requirementId', 'lifecycle_state']
    search_fields = ['reason', 'description']
    ordering_fields = ['created_at', 'expires_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an exception"""
        exception = self.get_object()
        approved_by_user_id = request.data.get('approved_by_user_id')
        if approved_by_user_id:
            exception.approve(approved_by_user_id)
            exception.save()
            return Response({'status': 'approved'})
        return Response({'error': 'approved_by_user_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def expire(self, request, pk=None):
        """Expire an exception"""
        exception = self.get_object()
        exception.expire()
        exception.save()
        return Response({'status': 'expired'})
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke an exception"""
        exception = self.get_object()
        exception.revoke()
        exception.save()
        return Response({'status': 'revoked'})

