from django.urls import include, path
from rest_framework import routers

from .views import (
    PortalPresetViewSet,
    PortalViewSet,
    PublicDocumentServeView,
    PublicDocumentViewSet,
    PublicPortalView,
    PublicPrimaryPortalView,
)

router = routers.DefaultRouter()
router.register(r"portal-presets", PortalPresetViewSet, basename="portal-presets")
router.register(r"portals", PortalViewSet, basename="portals")
router.register(r"public-documents", PublicDocumentViewSet, basename="public-documents")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "public/portals/primary/",
        PublicPrimaryPortalView.as_view(),
        name="public-primary-portal",
    ),
    path(
        "public/portals/<str:token>/",
        PublicPortalView.as_view(),
        name="public-portal",
    ),
    path(
        "public/documents/<str:token>/",
        PublicDocumentServeView.as_view(),
        name="public-document",
    ),
]
