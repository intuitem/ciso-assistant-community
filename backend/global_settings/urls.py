from django.urls import include, path
from rest_framework import routers

from iam.sso.views import SSOSettingsViewSet

from .views import (
    GlobalSettingsViewSet,
    get_sso_info,
    update_general_settings,
    get_general_settings,
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

urlpatterns = [
    # This route should ideally be placed under the routes of the routers, but the DefaultRouter usage overwrite the route and makes it inaccessible.
    # Could we use DefaultSettingsRouter to register the "global" route to fix that ?
    path(r"general/update/", update_general_settings, name="update_general_settings"),
    path(r"general/info/", get_general_settings, name="get_general_settings"),
    path(r"", include(router.urls)),
    path(r"", include(settings_router.urls)),
    path(r"sso/info/", get_sso_info, name="get_sso_info"),
]
