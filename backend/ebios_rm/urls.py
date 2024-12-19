from django.urls import include, path
from rest_framework import routers

from ebios_rm.views import (
    EbiosRMStudyViewSet,
    FearedEventViewSet,
    RoToViewSet,
    StakeholderViewSet,
    StrategicScenarioViewSet,
    AttackPathViewSet,
    OperationalScenarioViewSet,
)

router = routers.DefaultRouter()

router.register(r"studies", EbiosRMStudyViewSet, basename="studies")
router.register(r"feared-events", FearedEventViewSet, basename="feared-events")
router.register(r"ro-to", RoToViewSet, basename="ro-to")
router.register(r"stakeholders", StakeholderViewSet, basename="stakeholders")
router.register(
    r"strategic-scenarios", StrategicScenarioViewSet, basename="strategic-scenarios"
)
router.register(r"attack-paths", AttackPathViewSet, basename="attack-paths")
router.register(
    r"operational-scenarios",
    OperationalScenarioViewSet,
    basename="operational-scenarios",
)

urlpatterns = [
    path("", include(router.urls)),
]
