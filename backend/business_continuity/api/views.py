"""
Views for Business Continuity API
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import RBACPermissions

from ..models import BCPPlan
from .serializers import BCPPlanSerializer


class BCPPlanViewSet(viewsets.ModelViewSet):
    """ViewSet for BCPPlan aggregates"""
    queryset = BCPPlan.objects.all()
    serializer_class = BCPPlanSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'scope', 'plan_owner_user_id', 'next_test_date']
