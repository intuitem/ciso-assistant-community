from django.urls import include, path

from .views import LicenseStatusView, get_build, LogEntryViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"log-entries", LogEntryViewSet, basename="log-entries")

urlpatterns = [
    path("", include(router.urls)),
    path("build/", get_build, name="get_build"),
    path("license-status/", LicenseStatusView.as_view(), name="license-status"),
]
