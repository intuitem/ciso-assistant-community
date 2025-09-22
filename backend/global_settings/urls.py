from django.conf import settings
from django.urls import include, path

from core.routers import RouterFactory
from iam.sso.views import SSOSettingsViewSet

from .views import (
    GlobalSettingsViewSet,
    get_sso_info,
    GeneralSettingsViewSet,
    FeatureFlagsViewSet,
)
from .routers import DefaultSettingsRouter


router_factory = RouterFactory()
router = router_factory.create_router(
    enforce_trailing_slash=settings.ENFORCE_TRAILING_SLASH
)
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


urlpatterns = [
    path(r"", include(router.urls)),
    path(r"", include(settings_router.urls)),
    path(r"sso/info/", get_sso_info, name="get_sso_info"),
]
