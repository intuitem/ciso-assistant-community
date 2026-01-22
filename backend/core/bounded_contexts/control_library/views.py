"""
API Views for Control Library bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .aggregates.control import Control
from .aggregates.policy import Policy
from .aggregates.evidence_item import EvidenceItem
from .associations.control_implementation import ControlImplementation
from .associations.policy_acknowledgement import PolicyAcknowledgement
from .serializers import (
    ControlSerializer,
    PolicySerializer,
    EvidenceItemSerializer,
    ControlImplementationSerializer,
    PolicyAcknowledgementSerializer,
)


class ControlViewSet(viewsets.ModelViewSet):
    """ViewSet for Control aggregates"""
    
    queryset = Control.objects.all()
    serializer_class = ControlSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'control_type']
    search_fields = ['name', 'ref_id', 'objective', 'domain']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a control"""
        control = self.get_object()
        control.approve()
        control.save()
        return Response({'status': 'approved'})
    
    @action(detail=True, methods=['post'])
    def deprecate(self, request, pk=None):
        """Deprecate a control"""
        control = self.get_object()
        control.deprecate()
        control.save()
        return Response({'status': 'deprecated'})
    
    @action(detail=True, methods=['post'])
    def add_legal_requirement(self, request, pk=None):
        """Add a legal requirement to a control"""
        control = self.get_object()
        requirement_id = request.data.get('requirement_id')
        if requirement_id:
            control.add_legal_requirement(requirement_id)
            control.save()
            return Response({'status': 'legal requirement added'})
        return Response({'error': 'requirement_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_related_control(self, request, pk=None):
        """Add a related control"""
        control = self.get_object()
        related_control_id = request.data.get('related_control_id')
        if related_control_id:
            control.add_related_control(related_control_id)
            control.save()
            return Response({'status': 'related control added'})
        return Response({'error': 'related_control_id required'}, status=status.HTTP_400_BAD_REQUEST)


class PolicyViewSet(viewsets.ModelViewSet):
    """ViewSet for Policy aggregates"""
    
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['title', 'version', 'description']
    ordering_fields = ['title', 'publication_date', 'created_at']
    ordering = ['title']
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a policy"""
        from datetime import date
        policy = self.get_object()
        publication_date = request.data.get('publication_date')
        pub_date = None
        if publication_date:
            from datetime import datetime
            pub_date = datetime.strptime(publication_date, '%Y-%m-%d').date()
        
        policy.publish(pub_date)
        policy.save()
        return Response({'status': 'published'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire a policy"""
        policy = self.get_object()
        policy.retire()
        policy.save()
        return Response({'status': 'retired'})
    
    @action(detail=True, methods=['post'])
    def assign_owner(self, request, pk=None):
        """Assign an owner to a policy"""
        policy = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            policy.assign_owner(user_id)
            policy.save()
            return Response({'status': 'owner assigned'})
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)


class EvidenceItemViewSet(viewsets.ModelViewSet):
    """ViewSet for EvidenceItem aggregates"""
    
    queryset = EvidenceItem.objects.all()
    serializer_class = EvidenceItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'source_type']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'collected_at', 'expires_at']
    ordering = ['-collected_at']
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify an evidence item"""
        evidence = self.get_object()
        evidence.verify()
        evidence.save()
        return Response({'status': 'verified'})
    
    @action(detail=True, methods=['post'])
    def expire(self, request, pk=None):
        """Expire an evidence item"""
        evidence = self.get_object()
        evidence.expire()
        evidence.save()
        return Response({'status': 'expired'})


class ControlImplementationViewSet(viewsets.ModelViewSet):
    """ViewSet for ControlImplementation associations"""
    
    queryset = ControlImplementation.objects.all()
    serializer_class = ControlImplementationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['controlId', 'target_type', 'lifecycle_state']
    search_fields = ['notes']
    ordering_fields = ['created_at', 'last_tested_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def mark_implemented(self, request, pk=None):
        """Mark implementation as implemented"""
        impl = self.get_object()
        impl.mark_implemented()
        impl.save()
        return Response({'status': 'implemented'})
    
    @action(detail=True, methods=['post'])
    def mark_operating(self, request, pk=None):
        """Mark implementation as operating"""
        impl = self.get_object()
        impl.mark_operating()
        impl.save()
        return Response({'status': 'operating'})
    
    @action(detail=True, methods=['post'])
    def mark_ineffective(self, request, pk=None):
        """Mark implementation as ineffective"""
        impl = self.get_object()
        impl.mark_ineffective()
        impl.save()
        return Response({'status': 'ineffective'})
    
    @action(detail=True, methods=['post'])
    def record_test(self, request, pk=None):
        """Record a test of the control implementation"""
        from datetime import datetime
        impl = self.get_object()
        effectiveness_rating = request.data.get('effectiveness_rating')
        tested_at = request.data.get('tested_at')
        
        if effectiveness_rating:
            tested_at_obj = None
            if tested_at:
                tested_at_obj = datetime.fromisoformat(tested_at.replace('Z', '+00:00'))
            
            impl.record_test(int(effectiveness_rating), tested_at_obj)
            impl.save()
            return Response({'status': 'test recorded'})
        return Response({'error': 'effectiveness_rating required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_evidence(self, request, pk=None):
        """Add evidence to an implementation"""
        impl = self.get_object()
        evidence_id = request.data.get('evidence_id')
        if evidence_id:
            impl.add_evidence(evidence_id)
            impl.save()
            return Response({'status': 'evidence added'})
        return Response({'error': 'evidence_id required'}, status=status.HTTP_400_BAD_REQUEST)


class PolicyAcknowledgementViewSet(viewsets.ModelViewSet):
    """ViewSet for PolicyAcknowledgement associations"""
    
    queryset = PolicyAcknowledgement.objects.all()
    serializer_class = PolicyAcknowledgementSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['policyId', 'userId', 'method']
    search_fields = ['notes']
    ordering_fields = ['acknowledged_at']
    ordering = ['-acknowledged_at']

