from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GenericCollectionViewSet,
    AccreditationViewSet,
    ResponsibilityRoleViewSet,
    ResponsibilityMatrixViewSet,
    ResponsibilityMatrixActivityViewSet,
    ResponsibilityMatrixActorViewSet,
    ResponsibilityAssignmentViewSet,
)

router = DefaultRouter()
router.register(
    "generic-collections",
    GenericCollectionViewSet,
    basename="generic-collections",
)
router.register(
    "accreditations",
    AccreditationViewSet,
    basename="accreditations",
)
router.register(
    "responsibility-roles",
    ResponsibilityRoleViewSet,
    basename="responsibility-roles",
)
router.register(
    "responsibility-matrices",
    ResponsibilityMatrixViewSet,
    basename="responsibility-matrices",
)
router.register(
    "responsibility-matrix-activities",
    ResponsibilityMatrixActivityViewSet,
    basename="responsibility-matrix-activities",
)
router.register(
    "responsibility-matrix-actors",
    ResponsibilityMatrixActorViewSet,
    basename="responsibility-matrix-actors",
)
router.register(
    "responsibility-assignments",
    ResponsibilityAssignmentViewSet,
    basename="responsibility-assignments",
)

urlpatterns = [
    path("", include(router.urls)),
]
