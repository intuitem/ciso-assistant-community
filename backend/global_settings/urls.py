from django.conf import settings
from django.urls import include, path

from iam.sso.views import SSOSettingsViewSet

from .views import (
    get_default_language,
    get_sso_info,
    GeneralSettingsViewSet,
    FeatureFlagsViewSet,
    VulnerabilitySlaViewSet,
    SecIntelFeedsViewSet,
    InfraConfigViewSet,
)
from .routers import DefaultSettingsRouter

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
    r"vulnerability-sla",
    VulnerabilitySlaViewSet,
    basename="vulnerability-sla",
)

settings_router.register(
    r"sec-intel-feeds",
    SecIntelFeedsViewSet,
    basename="sec-intel-feeds",
)

if getattr(settings, "ENABLE_INFRA_CONFIG_MANAGEMENT", False):
    settings_router.register(
        r"infra-config",
        InfraConfigViewSet,
        basename="infra-config",
    )


urlpatterns = [
    path(r"", include(settings_router.urls)),
    path(r"sso/info/", get_sso_info, name="get_sso_info"),
    path(
        r"general/default-language/",
        get_default_language,
        name="get_default_language",
    ),
]
