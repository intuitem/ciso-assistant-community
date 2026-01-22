"""
API Views for Privacy bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .aggregates.data_asset import DataAsset
from .aggregates.data_flow import DataFlow
from .serializers import (
    DataAssetSerializer,
    DataFlowSerializer,
)


class DataAssetViewSet(viewsets.ModelViewSet):
    """ViewSet for DataAsset aggregates"""
    
    queryset = DataAsset.objects.all()
    serializer_class = DataAssetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'contains_personal_data']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a data asset"""
        asset = self.get_object()
        asset.activate()
        asset.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire a data asset"""
        asset = self.get_object()
        asset.retire()
        asset.save()
        return Response({'status': 'retired'})
    
    @action(detail=True, methods=['post'])
    def add_data_category(self, request, pk=None):
        """Add a data category"""
        asset = self.get_object()
        category = request.data.get('category')
        if category:
            asset.add_data_category(category)
            asset.save()
            return Response({'status': 'category added'})
        return Response({'error': 'category required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_asset(self, request, pk=None):
        """Add an asset to a data asset"""
        data_asset = self.get_object()
        asset_id = request.data.get('asset_id')
        if asset_id:
            data_asset.add_asset(asset_id)
            data_asset.save()
            return Response({'status': 'asset added'})
        return Response({'error': 'asset_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign_owner(self, request, pk=None):
        """Assign an owner to a data asset"""
        data_asset = self.get_object()
        org_unit_id = request.data.get('org_unit_id')
        if org_unit_id:
            data_asset.assign_owner(org_unit_id)
            data_asset.save()
            return Response({'status': 'owner assigned'})
        return Response({'error': 'org_unit_id required'}, status=status.HTTP_400_BAD_REQUEST)


class DataFlowViewSet(viewsets.ModelViewSet):
    """ViewSet for DataFlow aggregates"""
    
    queryset = DataFlow.objects.all()
    serializer_class = DataFlowSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'encryption_in_transit']
    search_fields = ['name', 'description', 'purpose']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a data flow"""
        flow = self.get_object()
        flow.activate()
        flow.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire a data flow"""
        flow = self.get_object()
        flow.retire()
        flow.save()
        return Response({'status': 'retired'})
    
    @action(detail=True, methods=['post'])
    def change(self, request, pk=None):
        """Change a data flow"""
        flow = self.get_object()
        changes = request.data.get('changes', {})
        if changes:
            flow.change(changes)
            flow.save()
            return Response({'status': 'changed'})
        return Response({'error': 'changes required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_data_asset(self, request, pk=None):
        """Add a data asset to a flow"""
        flow = self.get_object()
        data_asset_id = request.data.get('data_asset_id')
        if data_asset_id:
            flow.add_data_asset(data_asset_id)
            flow.save()
            return Response({'status': 'data asset added'})
        return Response({'error': 'data_asset_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_third_party(self, request, pk=None):
        """Add a third party to a data flow"""
        flow = self.get_object()
        third_party_id = request.data.get('third_party_id')
        if third_party_id:
            flow.add_third_party(third_party_id)
            flow.save()
            return Response({'status': 'third party added'})
        return Response({'error': 'third_party_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_control_implementation(self, request, pk=None):
        """Add a control implementation to a data flow"""
        flow = self.get_object()
        control_implementation_id = request.data.get('control_implementation_id')
        if control_implementation_id:
            flow.add_control_implementation(control_implementation_id)
            flow.save()
            return Response({'status': 'control implementation added'})
        return Response({'error': 'control_implementation_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_privacy_risk(self, request, pk=None):
        """Add a privacy risk to a data flow"""
        flow = self.get_object()
        risk_id = request.data.get('risk_id')
        if risk_id:
            flow.add_privacy_risk(risk_id)
            flow.save()
            return Response({'status': 'privacy risk added'})
        return Response({'error': 'risk_id required'}, status=status.HTTP_400_BAD_REQUEST)

