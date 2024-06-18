from django.urls import include, path
from rest_framework import routers

from iam.sso.views import SSOSettingsViewSet

from .views import GlobalSettingsViewSet
from .routers import DefaultSettingsRouter


router = routers.DefaultRouter()
router.register(r"global", GlobalSettingsViewSet, basename="global-settings")

settings_router = DefaultSettingsRouter()
settings_router.register(
    r"sso",
    SSOSettingsViewSet,
    basename="sso-settings",
)


urlpatterns = [
    path(r"", include(router.urls)),
    path(r"", include(settings_router.urls)),
]
