from django.urls import include, path
from rest_framework import routers

from .views import SSOSettingsViewSet, RedirectToProviderView


router = routers.DefaultRouter()


urlpatterns = [
    path("", include(router.urls)),
    path("redirect", RedirectToProviderView.as_view(), name="sso-redirect"),
]
