"""
Views for Privacy API
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import RBACPermissions

from ..models import DataAsset, ConsentRecord, DataSubjectRight
from .serializers import DataAssetSerializer, ConsentRecordSerializer, DataSubjectRightSerializer


class DataAssetViewSet(viewsets.ModelViewSet):
    """ViewSet for DataAsset aggregates"""
    queryset = DataAsset.objects.all()
    serializer_class = DataAssetSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sensitivity_level', 'compliance_status', 'pia_required']


class ConsentRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for ConsentRecord aggregates"""
    queryset = ConsentRecord.objects.all()
    serializer_class = ConsentRecordSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'consent_method', 'legal_basis']


class DataSubjectRightViewSet(viewsets.ModelViewSet):
    """ViewSet for DataSubjectRight aggregates"""
    queryset = DataSubjectRight.objects.all()
    serializer_class = DataSubjectRightSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'primary_right', 'priority']
