from django.urls import include, path
from rest_framework import routers

from iam.sso.views import SSOSettingsViewSet

from .views import (
    GlobalSettingsViewSet,
    get_sso_info,
    GeneralSettingsViewSet,
    FeatureFlagsViewSet,
    FeedsSettingsViewSet,
)
from .routers import DefaultSettingsRouter


router = routers.DefaultRouter()
router.register(r"global", GlobalSettingsViewSet, basename="global-settings")

settings_router = DefaultSettingsRouter()
settings_router.register(
    r"sso",
    SSOSettingsViewSet,
    basename="sso-settings",
)
settings_router.register(
    r"general",
    GeneralSettingsViewSet,
    basename="general-settings",
)

settings_router.register(
    r"feature-flags",
    FeatureFlagsViewSet,
    basename="feature-flags",
)

settings_router.register(
    r"feeds-settings",
    FeedsSettingsViewSet,
    basename="feeds-settings",
)

urlpatterns = [
    path(r"", include(router.urls)),
    path(r"", include(settings_router.urls)),
    path(r"sso/info/", get_sso_info, name="get_sso_info"),
]
