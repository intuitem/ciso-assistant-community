"""
URL configuration for accounts app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ClientAccountViewSet

router = DefaultRouter()
router.register(r"client-accounts", ClientAccountViewSet, basename="client-accounts")

urlpatterns = [
    path("", include(router.urls)),
]
