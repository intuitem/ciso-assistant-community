from django.urls import include, path

from .views import (
    LicenseStatusView,
    get_build,
    LogEntryViewSet,
    PermissionViewSet,
    RoleViewSet,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"log-entries", LogEntryViewSet, basename="log-entries")
router.register(r"roles", RoleViewSet, basename="roles")
router.register(r"permissions", PermissionViewSet, basename="permissions")

urlpatterns = [
    path("", include(router.urls)),
    path("build/", get_build, name="get_build"),
    path("license-status/", LicenseStatusView.as_view(), name="license-status"),
]
