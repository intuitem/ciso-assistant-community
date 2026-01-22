"""
Views for Third Party Management API
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import RBACPermissions

from ..models import ThirdPartyEntity
from .serializers import ThirdPartyEntitySerializer


class ThirdPartyEntityViewSet(viewsets.ModelViewSet):
    """ViewSet for ThirdPartyEntity aggregates"""
    queryset = ThirdPartyEntity.objects.all()
    serializer_class = ThirdPartyEntitySerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['entity_type', 'status', 'inherent_risk_level', 'compliance_status']
