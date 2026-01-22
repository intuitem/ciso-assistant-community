"""
URL configuration for Organization bounded context API
"""

from django.urls import path, include
from rest_framework import routers
from .views import (
    OrgUnitViewSet,
    UserViewSet,
    GroupViewSet,
    ResponsibilityAssignmentViewSet,
)

router = routers.DefaultRouter()
router.register(r'org-units', OrgUnitViewSet, basename='org-units')
router.register(r'users', UserViewSet, basename='organization-users')
router.register(r'groups', GroupViewSet, basename='organization-groups')
router.register(r'responsibility-assignments', ResponsibilityAssignmentViewSet, basename='responsibility-assignments')

urlpatterns = [
    path('', include(router.urls)),
]

