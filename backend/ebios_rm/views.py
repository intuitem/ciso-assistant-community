from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    Stakeholder,
    AttackPath,
    OperationalScenario,
)
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.decorators import action
from rest_framework.response import Response

LONG_CACHE_TTL = 60  # mn


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "ebios_rm.serializers"


class EbiosRMStudyViewSet(BaseModelViewSet):
    """
    API endpoint that allows ebios rm studies to be viewed or edited.
    """

    model = EbiosRMStudy

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(EbiosRMStudy.Status.choices))


class FearedEventViewSet(BaseModelViewSet):
    model = FearedEvent


class RoToViewSet(BaseModelViewSet):
    model = RoTo

    @action(detail=False, name="Get risk origin choices", url_path="risk-origin")
    def risk_origin(self, request):
        return Response(dict(RoTo.RiskOrigin.choices))

    @action(detail=False, name="Get motivation choices")
    def motivation(self, request):
        return Response(dict(RoTo.Motivation.choices))

    @action(detail=False, name="Get resources choices")
    def resources(self, request):
        return Response(dict(RoTo.Resources.choices))

    @action(detail=False, name="Get pertinence choices")
    def pertinence(self, request):
        return Response(dict(RoTo.Pertinence.choices))


class StakeholderViewSet(BaseModelViewSet):
    model = Stakeholder

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(Stakeholder.Category.choices))


class AttackPathViewSet(BaseModelViewSet):
    model = AttackPath


class OperationalScenarioViewSet(BaseModelViewSet):
    model = OperationalScenario
