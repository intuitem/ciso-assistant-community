"""
API Views for BusinessContinuity bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .aggregates.business_continuity_plan import BusinessContinuityPlan
from .supporting_entities.bcp_task import BcpTask
from .supporting_entities.bcp_audit import BcpAudit
from .serializers import (
    BusinessContinuityPlanSerializer,
    BcpTaskSerializer,
    BcpAuditSerializer,
)


class BusinessContinuityPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for BusinessContinuityPlan aggregates"""
    
    queryset = BusinessContinuityPlan.objects.all()
    serializer_class = BusinessContinuityPlanSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a BCP"""
        bcp = self.get_object()
        bcp.approve()
        bcp.save()
        return Response({'status': 'approved'})
    
    @action(detail=True, methods=['post'])
    def exercise(self, request, pk=None):
        """Exercise (test) a BCP"""
        bcp = self.get_object()
        bcp.exercise()
        bcp.save()
        return Response({'status': 'exercised'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire a BCP"""
        bcp = self.get_object()
        bcp.retire()
        bcp.save()
        return Response({'status': 'retired'})


class BcpTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for BcpTask supporting entities"""
    
    queryset = BcpTask.objects.all()
    serializer_class = BcpTaskSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['bcpId', 'lifecycle_state']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['due_date']
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a task"""
        task = self.get_object()
        task.start()
        task.save()
        return Response({'status': 'started'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a task"""
        task = self.get_object()
        task.complete()
        task.save()
        return Response({'status': 'completed'})
    
    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        """Block a task"""
        task = self.get_object()
        task.block()
        task.save()
        return Response({'status': 'blocked'})


class BcpAuditViewSet(viewsets.ModelViewSet):
    """ViewSet for BcpAudit supporting entities"""
    
    queryset = BcpAudit.objects.all()
    serializer_class = BcpAuditSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['bcpId', 'lifecycle_state', 'outcome']
    search_fields = ['name', 'description', 'notes']
    ordering_fields = ['performed_at', 'created_at']
    ordering = ['-performed_at']
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start an audit"""
        from datetime import datetime
        audit = self.get_object()
        performed_at = request.data.get('performed_at')
        performed_at_obj = None
        if performed_at:
            performed_at_obj = datetime.fromisoformat(performed_at.replace('Z', '+00:00'))
        audit.start(performed_at_obj)
        audit.save()
        return Response({'status': 'started'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete an audit"""
        audit = self.get_object()
        outcome = request.data.get('outcome')
        notes = request.data.get('notes')
        if outcome:
            audit.complete(outcome, notes)
            audit.save()
            return Response({'status': 'completed'})
        return Response({'error': 'outcome required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an audit"""
        audit = self.get_object()
        audit.close()
        audit.save()
        return Response({'status': 'closed'})

