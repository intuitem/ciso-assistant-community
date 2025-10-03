from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GenericCollectionViewSet,
    AccreditationViewSet,
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

urlpatterns = [
    path("", include(router.urls)),
]
