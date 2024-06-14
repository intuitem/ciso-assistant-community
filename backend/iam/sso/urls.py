from django.urls import include, path
from rest_framework import routers

from .views import SSOSettingsViewSet


router = routers.DefaultRouter()


urlpatterns = [
    path("", include(router.urls)),
]
