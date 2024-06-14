from django.urls import include, path
from rest_framework import routers

from .views import GlobalSettingsViewSet


router = routers.DefaultRouter()
router.register(r"", GlobalSettingsViewSet, basename="global-settings")


urlpatterns = [
    path("", include(router.urls)),
]
