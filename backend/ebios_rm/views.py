import django_filters as df
from core.serializers import RiskMatrixReadSerializer
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .helpers import ecosystem_radar_chart_data, ebios_rm_visual_analysis
from .models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    Stakeholder,
    StrategicScenario,
    AttackPath,
    OperationalScenario,
    ElementaryAction,
    OperatingMode,
    KillChain,
)
from .serializers import EbiosRMStudyReadSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.decorators import action
from rest_framework.response import Response

from django.shortcuts import get_object_or_404
from icecream import ic

import structlog

logger = structlog.get_logger(__name__)

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

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get quotation method choices")
    def quotation_method(self, request):
        return Response(dict(EbiosRMStudy.QuotationMethod.choices))

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

    @action(detail=True, name="Get ecosystem radar chart data")
    def ecosystem_chart_data(self, request, pk):
        return Response(
            ecosystem_radar_chart_data(Stakeholder.objects.filter(ebios_rm_study=pk))
        )

    @action(detail=True, name="Get EBIOS RM  study visual analysis")
    def visual_analysis(self, request, pk):
        study = get_object_or_404(EbiosRMStudy, id=pk)
        return Response(ebios_rm_visual_analysis(study))


class FearedEventViewSet(BaseModelViewSet):
    model = FearedEvent

    filterset_fields = [
        "ebios_rm_study",
        "ro_to_couples",
        "is_selected",
        "assets",
        "gravity",
        "qualifications",
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


class RoToFilter(df.FilterSet):
    class Meta:
        model = RoTo
        fields = [
            "ebios_rm_study",
            "is_selected",
            "risk_origin",
            "motivation",
            "feared_events",
        ]


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

    @action(detail=False, name="Get pertinence choices")
    def pertinence(self, request):
        return Response(dict(RoTo.Pertinence.choices))


class StakeholderViewSet(BaseModelViewSet):
    model = Stakeholder

    filterset_fields = ["ebios_rm_study", "is_selected", "applied_controls", "category"]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(Stakeholder.Category.choices))

    @action(detail=False, name="Get chart data")
    def chart_data(self, request):
        return Response(ecosystem_radar_chart_data(Stakeholder.objects.all()))


class StrategicScenarioViewSet(BaseModelViewSet):
    model = StrategicScenario

    filterset_fields = {
        "ebios_rm_study": ["exact"],
        "attack_paths": ["exact", "isnull"],
    }


class AttackPathFilter(df.FilterSet):
    used = df.BooleanFilter(method="is_used", label="Used")

    def is_used(self, queryset, name, value):
        if value:
            return queryset.filter(operational_scenario__isnull=False)
        return queryset.filter(operational_scenario__isnull=True)

    class Meta:
        model = AttackPath
        fields = [
            "ebios_rm_study",
            "is_selected",
            "used",
            "strategic_scenario",
            "stakeholders",
        ]


class AttackPathViewSet(BaseModelViewSet):
    model = AttackPath

    filterset_class = AttackPathFilter


class OperationalScenarioViewSet(BaseModelViewSet):
    model = OperationalScenario

    filterset_fields = ["ebios_rm_study", "likelihood"]

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


class ElementaryActionFilter(df.FilterSet):
    operating_mode_available_actions = df.ModelChoiceFilter(
        queryset=OperatingMode.objects.all(),
        method="filter_operating_mode_available_actions",
        label="Operating mode available actions",
    )

    def filter_operating_mode_available_actions(self, queryset, name, value):
        operating_mode = value
        used_elementary_actions = KillChain.objects.filter(
            operating_mode=operating_mode
        ).values_list("elementary_action", flat=True)
        return value.elementary_actions.all().exclude(id__in=used_elementary_actions)

    class Meta:
        model = ElementaryAction
        fields = ["operating_modes", "operating_mode_available_actions"]


class ElementaryActionViewSet(BaseModelViewSet):
    model = ElementaryAction

    filterset_class = ElementaryActionFilter

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get icon choices")
    def icon(self, request):
        return Response(dict(ElementaryAction.Icon.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get attack stage choices")
    def attack_stage(self, request):
        return Response(dict(ElementaryAction.AttackStage.choices))


class OperatingModeViewSet(BaseModelViewSet):
    model = OperatingMode

    filterset_fields = ["operational_scenario"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=True, name="Get likelihood choices")
    def likelihood(self, request, pk):
        instance: AttackPath = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [x["name"] for x in instance.parsed_matrix["probability"]],
            )
        )
        choices = undefined | _choices
        return Response(choices)

    def _perform_write(self, serializer):
        if not serializer.validated_data.get(
            "ref_id"
        ) and serializer.validated_data.get("operational_scenario"):
            operational_scenario = serializer.validated_data["operational_scenario"]
            ref_id = OperatingMode.get_default_ref_id(operational_scenario)
            serializer.validated_data["ref_id"] = ref_id
        serializer.save()

    @action(detail=False, methods=["get"])
    def default_ref_id(self, request):
        operational_scenario_id = request.query_params.get("operational_scenario")
        if not operational_scenario_id:
            return Response(
                {"error": "Missing 'operational_scenario' parameter."}, status=400
            )
        try:
            operational_scenario = OperationalScenario.objects.get(
                pk=operational_scenario_id
            )

            # Use the class method to compute the default ref_id
            default_ref_id = OperatingMode.get_default_ref_id(operational_scenario)
            return Response({"results": default_ref_id})
        except Exception as e:
            logger.error("Error in default_ref_id: %s", str(e))
            return Response(
                {"error": "Error in default_ref_id has occurred."}, status=400
            )

    @action(detail=True, name="Build graph for Operating Mode")
    def build_graph(self, request, pk):
        mo = get_object_or_404(OperatingMode, id=pk)
        nodes = []
        links = []
        groups = {0: "grp00", 1: "grp10", 2: "grp20", 3: "grp30"}
        panels = {
            0: "reconnaissance",
            1: "initialAccess",
            2: "discovery",
            3: "exploitation",
        }
        panel_nodes = {panel: [] for panel in panels.values()}

        for ea in mo.elementary_actions.all().order_by("attack_stage"):
            stage = ea.attack_stage
            entry = {"id": ea.id, "label": ea.name, "group": groups.get(stage)}
            if ea.icon:
                entry["icon"] = ea.icon_fa_hex
            nodes.append(entry)
            panel_name = panels.get(stage)
            if panel_name:
                panel_nodes[panel_name].append(ea.id)
        for step in mo.kill_chain_steps.all().order_by(
            "elementary_action__attack_stage"
        ):
            ea = step.elementary_action

            if step.antecedents.exists():
                target = ea.id

                if step.logic_operator:
                    # Get the stage from the first antecedent for panel placement
                    antecedent_stage = step.antecedents.first().attack_stage

                    nodes.append(
                        {
                            "id": step.id,
                            "icon": step.logic_operator,
                            "shape": "circle",
                            "group": groups.get(antecedent_stage),
                        }
                    )

                    # Add logic operator to the same panel as its antecedents
                    panel_name = panels.get(antecedent_stage)
                    if panel_name:
                        panel_nodes[panel_name].append(step.id)

                    target = step.id
                    links.append({"source": step.id, "target": ea.id})

                for ant in step.antecedents.all().order_by("attack_stage"):
                    links.append({"source": ant.id, "target": target})

        return Response(
            {"nodes": nodes, "links": links, "panelNodes": panel_nodes, "mo_id": mo.id}
        )


class KillChainViewSet(BaseModelViewSet):
    model = KillChain

    filterset_fields = ["operating_mode"]

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get logic operators choices")
    def logic_operator(self, request):
        return Response(dict(KillChain.LogicOperator.choices))
