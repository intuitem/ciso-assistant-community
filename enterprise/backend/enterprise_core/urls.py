from django.urls import include, path

from .views import (
    AuditedModelsView,
    LicenseStatusView,
    ObjectAuditTrailView,
    TimelineEntriesView,
    get_build,
    LogEntryViewSet,
    PermissionViewSet,
    RoleViewSet,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"log-entries", LogEntryViewSet, basename="log-entries")
router.register(r"permissions", PermissionViewSet, basename="permissions")
# Custom-role management is enterprise-only: this full-CRUD viewset shadows the
# community read-only one (enterprise URL modules are mounted first).
router.register(r"roles", RoleViewSet, basename="roles")

urlpatterns = [
    path("", include(router.urls)),
    path("build/", get_build, name="get_build"),
    path("license-status/", LicenseStatusView.as_view(), name="license-status"),
    path(
        "object-audit-trail/",
        ObjectAuditTrailView.as_view(),
        name="object-audit-trail",
    ),
    path("audited-models/", AuditedModelsView.as_view(), name="audited-models"),
    path(
        "insights-timeline/",
        TimelineEntriesView.as_view(),
        name="insights-timeline",
    ),
]
