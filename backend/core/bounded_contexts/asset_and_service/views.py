"""
API Views for Asset and Service bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .aggregates.asset import Asset
from .aggregates.service import Service
from .aggregates.process import Process
from .associations.service_contract import ServiceContract
from .serializers import (
    AssetSerializer,
    ServiceSerializer,
    ProcessSerializer,
    ServiceContractSerializer,
)


class AssetViewSet(viewsets.ModelViewSet):
    """ViewSet for Asset aggregates"""
    
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'asset_type', 'assetClassificationId']
    search_fields = ['name', 'ref_id', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate an asset"""
        asset = self.get_object()
        asset.activate()
        asset.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive an asset"""
        asset = self.get_object()
        asset.archive()
        asset.save()
        return Response({'status': 'archived'})
    
    @action(detail=True, methods=['post'])
    def assign_control(self, request, pk=None):
        """Assign a control to an asset"""
        asset = self.get_object()
        control_id = request.data.get('control_id')
        if control_id:
            asset.assign_control(control_id)
            asset.save()
            return Response({'status': 'control assigned'})
        return Response({'error': 'control_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def assign_risk(self, request, pk=None):
        """Assign a risk to an asset"""
        asset = self.get_object()
        risk_id = request.data.get('risk_id')
        if risk_id:
            asset.assign_risk(risk_id)
            asset.save()
            return Response({'status': 'risk assigned'})
        return Response({'error': 'risk_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def link_service(self, request, pk=None):
        """Link a service to an asset"""
        asset = self.get_object()
        service_id = request.data.get('service_id')
        if service_id:
            asset.link_service(service_id)
            asset.save()
            return Response({'status': 'service linked'})
        return Response({'error': 'service_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign_business_owner(self, request, pk=None):
        """Assign a business owner to an asset"""
        asset = self.get_object()
        org_unit_id = request.data.get('org_unit_id')
        if org_unit_id:
            asset.assign_business_owner(org_unit_id)
            asset.save()
            return Response({'status': 'business owner assigned'})
        return Response({'error': 'org_unit_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign_system_owner(self, request, pk=None):
        """Assign a system owner to an asset"""
        asset = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            asset.assign_system_owner(user_id)
            asset.save()
            return Response({'status': 'system owner assigned'})
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)


class ServiceViewSet(viewsets.ModelViewSet):
    """ViewSet for Service aggregates"""
    
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'serviceClassificationId']
    search_fields = ['name', 'ref_id', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def make_operational(self, request, pk=None):
        """Make a service operational"""
        service = self.get_object()
        service.make_operational()
        service.save()
        return Response({'status': 'operational'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire a service"""
        service = self.get_object()
        service.retire()
        service.save()
        return Response({'status': 'retired'})
    
    @action(detail=True, methods=['post'])
    def link_asset(self, request, pk=None):
        """Link an asset to a service"""
        service = self.get_object()
        asset_id = request.data.get('asset_id')
        if asset_id:
            service.link_asset(asset_id)
            service.save()
            return Response({'status': 'asset linked'})
        return Response({'error': 'asset_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def link_third_party(self, request, pk=None):
        """Link a third party to a service"""
        service = self.get_object()
        third_party_id = request.data.get('third_party_id')
        if third_party_id:
            service.link_third_party(third_party_id)
            service.save()
            return Response({'status': 'third party linked'})
        return Response({'error': 'third_party_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign_control(self, request, pk=None):
        """Assign a control to a service"""
        service = self.get_object()
        control_id = request.data.get('control_id')
        if control_id:
            service.assign_control(control_id)
            service.save()
            return Response({'status': 'control assigned'})
        return Response({'error': 'control_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign_risk(self, request, pk=None):
        """Assign a risk to a service"""
        service = self.get_object()
        risk_id = request.data.get('risk_id')
        if risk_id:
            service.assign_risk(risk_id)
            service.save()
            return Response({'status': 'risk assigned'})
        return Response({'error': 'risk_id required'}, status=status.HTTP_400_BAD_REQUEST)


class ProcessViewSet(viewsets.ModelViewSet):
    """ViewSet for Process aggregates"""
    
    queryset = Process.objects.all()
    serializer_class = ProcessSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['name', 'ref_id', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a process"""
        process = self.get_object()
        process.activate()
        process.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire a process"""
        process = self.get_object()
        process.retire()
        process.save()
        return Response({'status': 'retired'})

    @action(detail=True, methods=['post'])
    def assign_to_org_unit(self, request, pk=None):
        """Assign process to an organizational unit"""
        process = self.get_object()
        org_unit_id = request.data.get('org_unit_id')
        if org_unit_id:
            process.assign_to_org_unit(org_unit_id)
            process.save()
            return Response({'status': 'assigned to org unit'})
        return Response({'error': 'org_unit_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def link_asset(self, request, pk=None):
        """Link an asset to a process"""
        process = self.get_object()
        asset_id = request.data.get('asset_id')
        if asset_id:
            process.link_asset(asset_id)
            process.save()
            return Response({'status': 'asset linked'})
        return Response({'error': 'asset_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign_control(self, request, pk=None):
        """Assign a control to a process"""
        process = self.get_object()
        control_id = request.data.get('control_id')
        if control_id:
            process.assign_control(control_id)
            process.save()
            return Response({'status': 'control assigned'})
        return Response({'error': 'control_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign_risk(self, request, pk=None):
        """Assign a risk to a process"""
        process = self.get_object()
        risk_id = request.data.get('risk_id')
        if risk_id:
            process.assign_risk(risk_id)
            process.save()
            return Response({'status': 'risk assigned'})
        return Response({'error': 'risk_id required'}, status=status.HTTP_400_BAD_REQUEST)


class ServiceContractViewSet(viewsets.ModelViewSet):
    """ViewSet for ServiceContract associations"""
    
    queryset = ServiceContract.objects.all()
    serializer_class = ServiceContractSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['serviceId', 'thirdPartyId', 'lifecycle_state']
    search_fields = ['key_terms', 'notes']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """Renew a service contract"""
        from datetime import date
        contract = self.get_object()
        new_end_date = request.data.get('new_end_date')
        renewal_date = request.data.get('renewal_date')
        
        if new_end_date:
            from datetime import datetime
            new_end_date = datetime.strptime(new_end_date, '%Y-%m-%d').date()
            renewal_date_obj = None
            if renewal_date:
                renewal_date_obj = datetime.strptime(renewal_date, '%Y-%m-%d').date()
            
            contract.renew(new_end_date, renewal_date_obj)
            contract.save()
            return Response({'status': 'renewed'})
        return Response({'error': 'new_end_date required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def expire(self, request, pk=None):
        """Expire a service contract"""
        contract = self.get_object()
        contract.expire()
        contract.save()
        return Response({'status': 'expired'})

