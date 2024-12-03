from django.urls import include, path
from rest_framework import routers

from ebios_rm.views import EbiosRMStudyViewSet, FearedEventViewSet

router = routers.DefaultRouter()

router.register(r"studies", EbiosRMStudyViewSet, basename="studies")
router.register(r"feared-events", FearedEventViewSet, basename="feared-events")

urlpatterns = [
    path("", include(router.urls)),
]
