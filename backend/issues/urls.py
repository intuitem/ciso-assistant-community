from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CommitmentVersionViewSet, RemediationIssueViewSet

router = DefaultRouter()
router.register(
    "remediation-issues",
    RemediationIssueViewSet,
    basename="remediation-issues",
)
router.register(
    "commitment-versions",
    CommitmentVersionViewSet,
    basename="commitment-versions",
)

urlpatterns = [
    path("", include(router.urls)),
]
