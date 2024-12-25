import django_filters as df
from core.serializers import RiskMatrixReadSerializer
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from core.serializers import RiskMatrixReadSerializer
from .models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    Stakeholder,
    StrategicScenario,
    AttackPath,
    OperationalScenario,
)
from .serializers import EbiosRMStudyReadSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.decorators import action
from rest_framework.response import Response

LONG_CACHE_TTL = 60  # mn

import math


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

    @action(
        detail=True,
        methods=["patch"],
        name="Update workshop step status",
        url_path="workshop/(?P<workshop>[1-5])/step/(?P<step>[1-5])",
    )
    def update_workshop_step_status(self, request, pk, workshop, step):
        ebios_rm_study: EbiosRMStudy = self.get_object()
        workshop = int(workshop)
        step = int(step)
        # NOTE: For now, just set it as done. Will allow undoing this later.
        ebios_rm_study.update_workshop_step_status(
            workshop, step, new_status=request.data.get("status", "in_progress")
        )
        return Response(EbiosRMStudyReadSerializer(ebios_rm_study).data)


class FearedEventViewSet(BaseModelViewSet):
    model = FearedEvent

    filterset_fields = ["ebios_rm_study", "ro_to_couples", "is_selected"]

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


class RoToFilter(df.FilterSet):
    used = df.BooleanFilter(method="is_used", label="Used")

    def is_used(self, queryset, name, value):
        if value:
            return queryset.filter(strategicscenario__isnull=False)
        return queryset.filter(strategicscenario__isnull=True)

    class Meta:
        model = RoTo
        fields = ["ebios_rm_study", "is_selected", "used"]


class RoToViewSet(BaseModelViewSet):
    model = RoTo

    filterset_class = RoToFilter

    @action(detail=False, name="Get risk origin choices", url_path="risk-origin")
    def risk_origin(self, request):
        return Response(dict(RoTo.RiskOrigin.choices))

    @action(detail=False, name="Get motivation choices")
    def motivation(self, request):
        return Response(dict(RoTo.Motivation.choices))

    @action(detail=False, name="Get resources choices")
    def resources(self, request):
        return Response(dict(RoTo.Resources.choices))

    @action(detail=False, name="Get activity choices")
    def activity(self, request):
        return Response(dict(RoTo.Activity.choices))


class StakeholderViewSet(BaseModelViewSet):
    model = Stakeholder

    filterset_fields = [
        "ebios_rm_study",
        "is_selected",
    ]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(Stakeholder.Category.choices))

    @action(detail=False, name="Get chart data")
    def chart_data(self, request):
        def get_exposure_segment_id(value):
            if value < 3:
                return 1
            if value >= 3 and value < 7:
                return 2
            if value >= 7 and value <= 9:
                return 3
            if value > 9:
                return 4
            return 0

        def get_reliability_cluster(value):
            if value < 4:
                return "clst1"
            if value >= 4 and value < 6:
                return "clst2"
            if value >= 6 and value <= 7:
                return "clst3"
            if value > 7:
                return "clst4"
            return 1

        """
        // data format: f1-f4 (fiabilité cyber = maturité x confiance ) to get the clusters and colors
        // x,y, z
        // x: criticité calculée avec cap à 5,5
        // y: the angle (output of dict to make sure they end up on the right quadrant, min: 45, max:-45) -> done on BE
        // z: the size of item (exposition = dependence x penetration) based on a dict, -> done on BE
        // label: name of the 3rd party entity
        Angles start at 56,25 (45+45/4) and end at -45-45/4 = 303,75
        """

        # we can add a filter on the Stakeholder concerned by the ebios study here
        qs = Stakeholder.objects.all()

        c_data = {"clst1": [], "clst2": [], "clst3": [], "clst4": []}
        r_data = {"clst1": [], "clst2": [], "clst3": [], "clst4": []}
        angle_offsets = {"client": 135, "partner": 225, "supplier": 45}

        cnt_c_not_displayed = 0
        cnt_r_not_displayed = 0
        for sh in qs:
            # current
            c_reliability = sh.current_maturity * sh.current_trust
            c_exposure = sh.current_dependency * sh.current_penetration
            c_exposure_val = get_exposure_segment_id(c_exposure) * 4

            c_criticality = (
                math.floor(sh.current_criticality * 100) / 100.0
                if sh.current_criticality <= 5
                else 5.25
            )

            angle = angle_offsets[sh.category] + (
                get_exposure_segment_id(c_exposure) * (45 / 4)
            )

            vector = [c_criticality, angle, c_exposure_val, str(sh)]

            cluser_id = get_reliability_cluster(c_reliability)
            c_data[cluser_id].append(vector)

            # residual
            r_reliability = sh.residual_maturity * sh.residual_trust
            r_exposure = sh.residual_dependency * sh.residual_penetration
            r_exposure_val = get_exposure_segment_id(r_exposure) * 4

            r_criticality = (
                math.floor(sh.residual_criticality * 100) / 100.0
                if sh.residual_criticality <= 5
                else 5.25
            )

            angle = angle_offsets[sh.category] + (
                get_exposure_segment_id(r_exposure) * (45 / 4)
            )

            vector = [r_criticality, angle, r_exposure_val, str(sh)]

            cluser_id = get_reliability_cluster(r_reliability)
            r_data[cluser_id].append(vector)

        return Response({"current": c_data, "residual": r_data})


class StrategicScenarioViewSet(BaseModelViewSet):
    model = StrategicScenario

    filterset_fields = [
        "ebios_rm_study",
    ]


class AttackPathFilter(df.FilterSet):
    used = df.BooleanFilter(method="is_used", label="Used")

    def is_used(self, queryset, name, value):
        if value:
            return queryset.filter(operational_scenario__isnull=False)
        return queryset.filter(operational_scenario__isnull=True)

    class Meta:
        model = AttackPath
        fields = ["ebios_rm_study", "is_selected", "used", "strategic_scenario"]


class AttackPathViewSet(BaseModelViewSet):
    model = AttackPath

    filterset_class = AttackPathFilter


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
