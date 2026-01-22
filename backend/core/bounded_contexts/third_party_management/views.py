"""
API Views for ThirdPartyManagement bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .aggregates.third_party import ThirdParty
from .serializers import ThirdPartySerializer


class ThirdPartyViewSet(viewsets.ModelViewSet):
    """ViewSet for ThirdParty aggregates"""
    
    queryset = ThirdParty.objects.all()
    serializer_class = ThirdPartySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'criticality']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a third party"""
        third_party = self.get_object()
        third_party.activate()
        third_party.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def start_offboarding(self, request, pk=None):
        """Start offboarding a third party"""
        third_party = self.get_object()
        third_party.start_offboarding()
        third_party.save()
        return Response({'status': 'offboarding_started'})
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a third party"""
        third_party = self.get_object()
        third_party.archive()
        third_party.save()
        return Response({'status': 'archived'})

