from django.urls import include, path
from rest_framework import routers

from ebios_rm.views import EbiosRMStudyViewSet

router = routers.DefaultRouter()

router.register(r"studies", EbiosRMStudyViewSet, basename="studies")

urlpatterns = [
    path("", include(router.urls)),
]
