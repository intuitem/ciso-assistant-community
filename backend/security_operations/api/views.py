"""
Views for Security Operations API
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import RBACPermissions

from ..models import SecurityIncident
from .serializers import SecurityIncidentSerializer


class SecurityIncidentViewSet(viewsets.ModelViewSet):
    """ViewSet for SecurityIncident aggregates"""
    queryset = SecurityIncident.objects.all()
    serializer_class = SecurityIncidentSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'severity', 'category', 'assigned_analyst_user_id']
