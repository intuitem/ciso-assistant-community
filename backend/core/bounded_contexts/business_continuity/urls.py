"""
URL configuration for BusinessContinuity bounded context API
"""

from django.urls import path, include
from rest_framework import routers
from .views import (
    BusinessContinuityPlanViewSet,
    BcpTaskViewSet,
    BcpAuditViewSet,
)

router = routers.DefaultRouter()
router.register(r'business-continuity-plans', BusinessContinuityPlanViewSet, basename='business-continuity-plans')
router.register(r'bcp-tasks', BcpTaskViewSet, basename='bcp-tasks')
router.register(r'bcp-audits', BcpAuditViewSet, basename='bcp-audits')

urlpatterns = [
    path('', include(router.urls)),
]

