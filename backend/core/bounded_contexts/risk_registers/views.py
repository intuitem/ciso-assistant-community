"""
API Views for Risk Registers bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .aggregates.asset_risk import AssetRisk
from .aggregates.third_party_risk import ThirdPartyRisk
from .aggregates.business_risk import BusinessRisk
from .supporting_entities.risk_treatment_plan import RiskTreatmentPlan
from .supporting_entities.risk_exception import RiskException
from .serializers import (
    AssetRiskSerializer,
    ThirdPartyRiskSerializer,
    BusinessRiskSerializer,
    RiskTreatmentPlanSerializer,
    RiskExceptionSerializer,
)


class AssetRiskViewSet(viewsets.ModelViewSet):
    """ViewSet for AssetRisk aggregates"""
    
    queryset = AssetRisk.objects.all()
    serializer_class = AssetRiskSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['title', 'description', 'threat', 'vulnerability']
    ordering_fields = ['title', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def assess(self, request, pk=None):
        """Assess a risk"""
        risk = self.get_object()
        likelihood = request.data.get('likelihood')
        impact = request.data.get('impact')
        inherent_score = request.data.get('inherent_score')
        residual_score = request.data.get('residual_score')
        rationale = request.data.get('rationale')
        
        if all([likelihood, impact, inherent_score, residual_score]):
            risk.assess(likelihood, impact, inherent_score, residual_score, rationale)
            risk.save()
            return Response({'status': 'assessed'})
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def treat(self, request, pk=None):
        """Treat a risk"""
        risk = self.get_object()
        treatment_plan_id = request.data.get('treatment_plan_id')
        risk.treat(treatment_plan_id)
        risk.save()
        return Response({'status': 'treated'})
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a risk"""
        risk = self.get_object()
        risk.accept()
        risk.save()
        return Response({'status': 'accepted'})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a risk"""
        risk = self.get_object()
        risk.close()
        risk.save()
        return Response({'status': 'closed'})


class ThirdPartyRiskViewSet(viewsets.ModelViewSet):
    """ViewSet for ThirdPartyRisk aggregates"""
    
    queryset = ThirdPartyRisk.objects.all()
    serializer_class = ThirdPartyRiskSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def assess(self, request, pk=None):
        """Assess a risk"""
        risk = self.get_object()
        likelihood = request.data.get('likelihood')
        impact = request.data.get('impact')
        inherent_score = request.data.get('inherent_score')
        residual_score = request.data.get('residual_score')
        rationale = request.data.get('rationale')
        
        if all([likelihood, impact, inherent_score, residual_score]):
            risk.assess(likelihood, impact, inherent_score, residual_score, rationale)
            risk.save()
            return Response({'status': 'assessed'})
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def treat(self, request, pk=None):
        """Treat a risk"""
        risk = self.get_object()
        risk.treat()
        risk.save()
        return Response({'status': 'treated'})
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a risk"""
        risk = self.get_object()
        risk.accept()
        risk.save()
        return Response({'status': 'accepted'})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a risk"""
        risk = self.get_object()
        risk.close()
        risk.save()
        return Response({'status': 'closed'})


class BusinessRiskViewSet(viewsets.ModelViewSet):
    """ViewSet for BusinessRisk aggregates"""
    
    queryset = BusinessRisk.objects.all()
    serializer_class = BusinessRiskSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def assess(self, request, pk=None):
        """Assess a risk"""
        risk = self.get_object()
        likelihood = request.data.get('likelihood')
        impact = request.data.get('impact')
        inherent_score = request.data.get('inherent_score')
        residual_score = request.data.get('residual_score')
        rationale = request.data.get('rationale')
        
        if all([likelihood, impact, inherent_score, residual_score]):
            risk.assess(likelihood, impact, inherent_score, residual_score, rationale)
            risk.save()
            return Response({'status': 'assessed'})
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def treat(self, request, pk=None):
        """Treat a risk"""
        risk = self.get_object()
        risk.treat()
        risk.save()
        return Response({'status': 'treated'})
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a risk"""
        risk = self.get_object()
        risk.accept()
        risk.save()
        return Response({'status': 'accepted'})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a risk"""
        risk = self.get_object()
        risk.close()
        risk.save()
        return Response({'status': 'closed'})


class RiskTreatmentPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for RiskTreatmentPlan supporting entities"""
    
    queryset = RiskTreatmentPlan.objects.all()
    serializer_class = RiskTreatmentPlanSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['riskId', 'strategy', 'lifecycle_state']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a treatment plan"""
        plan = self.get_object()
        plan.activate()
        plan.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a treatment plan"""
        plan = self.get_object()
        plan.complete()
        plan.save()
        return Response({'status': 'completed'})
    
    @action(detail=True, methods=['post'])
    def abandon(self, request, pk=None):
        """Abandon a treatment plan"""
        plan = self.get_object()
        plan.abandon()
        plan.save()
        return Response({'status': 'abandoned'})


class RiskExceptionViewSet(viewsets.ModelViewSet):
    """ViewSet for RiskException supporting entities"""
    
    queryset = RiskException.objects.all()
    serializer_class = RiskExceptionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['riskId', 'lifecycle_state']
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

