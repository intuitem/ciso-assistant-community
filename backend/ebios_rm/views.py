from core.serializers import RiskMatrixReadSerializer
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from core.serializers import RiskMatrixReadSerializer
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

    @action(detail=True, name="Get risk matrix", url_path="risk-matrix")
    def risk_matrix(self, request, pk=None):
        ebios_rm_study = self.get_object()
        return Response(RiskMatrixReadSerializer(ebios_rm_study.risk_matrix).data)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get gravity choices")
    def gravity(self, request, pk):
        ebios_rm_study: EbiosRMStudy = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in ebios_rm_study.parsed_matrix["impact"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)

    @action(detail=True, name="Get likelihood choices")
    def likelihood(self, request, pk):
        ebios_rm_study: EbiosRMStudy = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in ebios_rm_study.parsed_matrix["probability"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)


class FearedEventViewSet(BaseModelViewSet):
    model = FearedEvent

    filterset_fields = [
        "ebios_rm_study",
    ]

    @action(detail=True, name="Get risk matrix", url_path="risk-matrix")
    def risk_matrix(self, request, pk=None):
        feared_event = self.get_object()
        return Response(RiskMatrixReadSerializer(feared_event.risk_matrix).data)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get gravity choices")
    def gravity(self, request, pk):
        feared_event: FearedEvent = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in feared_event.parsed_matrix["impact"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)


class RoToViewSet(BaseModelViewSet):
    model = RoTo

    filterset_fields = [
        "ebios_rm_study",
    ]

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

    filterset_fields = [
        "ebios_rm_study",
    ]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(Stakeholder.Category.choices))


class AttackPathViewSet(BaseModelViewSet):
    model = AttackPath

    filterset_fields = [
        "ebios_rm_study",
    ]


class OperationalScenarioViewSet(BaseModelViewSet):
    model = OperationalScenario

    filterset_fields = [
        "ebios_rm_study",
    ]

    @action(detail=True, name="Get risk matrix", url_path="risk-matrix")
    def risk_matrix(self, request, pk=None):
        attack_path = self.get_object()
        return Response(RiskMatrixReadSerializer(attack_path.risk_matrix).data)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get likelihood choices")
    def likelihood(self, request, pk):
        attack_path: AttackPath = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in attack_path.parsed_matrix["probability"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)
