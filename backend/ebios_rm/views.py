import django_filters as df
from core.serializers import RiskMatrixReadSerializer
from core.views import BaseModelViewSet as AbstractBaseModelViewSet, GenericFilterSet
from core.models import Terminology
from .helpers import ecosystem_radar_chart_data, ebios_rm_visual_analysis
from .models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    RoToQuerySet,
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

import structlog

logger = structlog.get_logger(__name__)

LONG_CACHE_TTL = 60  # mn


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "ebios_rm.serializers"


class EbiosRMStudyViewSet(BaseModelViewSet):
    """
    API endpoint that allows ebios rm studies to be viewed or edited.
    """

    filterset_fields = ["folder", "genericcollection"]

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
        url_path="workshop/(?P<workshop>[1-5])/step/(?P<step>[0-5])",
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

    @action(detail=True, name="Get ecosystem circular chart data")
    def ecosystem_circular_chart_data(self, request, pk):
        from .helpers import ecosystem_circular_chart_data

        return Response(
            ecosystem_circular_chart_data(Stakeholder.objects.filter(ebios_rm_study=pk))
        )

    @action(detail=True, name="Get EBIOS RM  study visual analysis")
    def visual_analysis(self, request, pk):
        study = get_object_or_404(EbiosRMStudy, id=pk)
        return Response(ebios_rm_visual_analysis(study))

    @action(detail=True, name="Get EBIOS RM study report data", url_path="report-data")
    def report_data(self, request, pk):
        """
        Endpoint to prepare comprehensive report data for an EBIOS RM study.
        Returns all study attributes and associated objects in a structured format.
        """
        study = get_object_or_404(EbiosRMStudy, id=pk)

        from .serializers import (
            EbiosRMStudyReadSerializer,
            FearedEventReadSerializer,
            RoToReadSerializer,
            StakeholderReadSerializer,
            StrategicScenarioReadSerializer,
            AttackPathReadSerializer,
            OperationalScenarioReadSerializer,
            OperatingModeReadSerializer,
        )
        from .models import OperatingMode
        from core.models import RequirementAssessment
        from .helpers import ecosystem_circular_chart_data

        # Get all related data
        feared_events = FearedEvent.objects.filter(
            ebios_rm_study=study, is_selected=True
        )
        ro_to_couples = RoTo.objects.filter(
            ebios_rm_study=study, is_selected=True
        ).with_pertinence()
        stakeholders = Stakeholder.objects.filter(
            ebios_rm_study=study, is_selected=True
        )
        strategic_scenarios = StrategicScenario.objects.filter(ebios_rm_study=study)
        attack_paths = AttackPath.objects.filter(ebios_rm_study=study, is_selected=True)
        operational_scenarios = OperationalScenario.objects.filter(ebios_rm_study=study)

        # Get operating modes for all operational scenarios
        operating_modes = OperatingMode.objects.filter(
            operational_scenario__in=operational_scenarios
        )

        # Build graph data for each operating mode
        def build_mode_graph(mo):
            """Build graph data for a single operating mode"""
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

            # Collect all elementary actions that are part of kill chain steps
            kill_chain_ea_ids = set()
            for step in mo.kill_chain_steps.all():
                kill_chain_ea_ids.add(step.elementary_action.id)
                # Also add antecedents
                for ant in step.antecedents.all():
                    kill_chain_ea_ids.add(ant.id)

            # Create nodes only for elementary actions in the kill chain
            kill_chain_eas = mo.elementary_actions.filter(
                id__in=kill_chain_ea_ids
            ).order_by("attack_stage")

            for ea in kill_chain_eas:
                stage = ea.attack_stage
                entry = {"id": str(ea.id), "label": ea.name, "group": groups.get(stage)}
                if ea.icon:
                    entry["icon"] = ea.icon_fa_hex
                nodes.append(entry)
                panel_name = panels.get(stage)
                if panel_name:
                    panel_nodes[panel_name].append(str(ea.id))

            # Build links based on kill chain steps
            for step in mo.kill_chain_steps.all().order_by(
                "elementary_action__attack_stage"
            ):
                ea = step.elementary_action
                if step.antecedents.exists():
                    target = str(ea.id)
                    if step.logic_operator:
                        # Get the stage from the first antecedent for panel placement
                        antecedent_stage = step.antecedents.first().attack_stage
                        nodes.append(
                            {
                                "id": str(step.id),
                                "icon": step.logic_operator,
                                "shape": "circle",
                                "size": 45,
                            }
                        )
                        # Add logic operator to the same panel as its antecedents
                        panel_name = panels.get(antecedent_stage)
                        if panel_name:
                            panel_nodes[panel_name].append(str(step.id))
                        target = str(step.id)
                        links.append({"source": str(step.id), "target": str(ea.id)})
                    for ant in step.antecedents.all().order_by("attack_stage"):
                        links.append({"source": str(ant.id), "target": target})

            # Only return graph data if there are nodes
            if nodes:
                return {"nodes": nodes, "links": links, "panelNodes": panel_nodes}
            return None

        # Get compliance assessments with their result counts
        compliance_assessments_data = []
        for assessment in study.compliance_assessments.all():
            result_counts = {}
            for count, result in assessment.get_requirements_result_count():
                result_counts[result] = count

            compliance_assessments_data.append(
                {
                    "id": str(assessment.id),
                    "name": assessment.name,
                    "framework": assessment.framework.name
                    if assessment.framework
                    else None,
                    "version": assessment.version,
                    "eta": assessment.eta,
                    "due_date": assessment.due_date,
                    "status": assessment.status,
                    "progress": assessment.get_progress(),
                    "result_counts": result_counts,
                }
            )

        # Get risk matrix data from last risk assessment
        risk_matrix_data = None
        if study.last_risk_assessment:
            from core.serializers import (
                RiskScenarioReadSerializer,
                RiskMatrixReadSerializer,
            )

            risk_scenarios = study.last_risk_assessment.risk_scenarios.all()
            risk_matrix_data = {
                "risk_assessment": {
                    "id": str(study.last_risk_assessment.id),
                    "name": study.last_risk_assessment.name,
                    "version": study.last_risk_assessment.version,
                },
                "risk_matrix": RiskMatrixReadSerializer(study.risk_matrix).data,
                "risk_scenarios": RiskScenarioReadSerializer(
                    risk_scenarios, many=True
                ).data,
            }

        # Get ecosystem radar data
        radar_data = ecosystem_circular_chart_data(stakeholders)

        # Get action plans from compliance assessments
        from core.serializers import AppliedControlReadSerializer
        from core.models import AppliedControl

        compliance_action_plans = []
        for assessment in study.compliance_assessments.all():
            requirement_assessments = assessment.get_requirement_assessments(
                include_non_assessable=False
            )
            applied_controls = (
                AppliedControl.objects.filter(
                    requirement_assessments__in=requirement_assessments
                )
                .distinct()
                .order_by("eta")
            )
            if applied_controls.exists():
                compliance_action_plans.append(
                    {
                        "assessment_id": str(assessment.id),
                        "assessment_name": assessment.name,
                        "framework": (
                            assessment.framework.name if assessment.framework else None
                        ),
                        "applied_controls": AppliedControlReadSerializer(
                            applied_controls, many=True
                        ).data,
                    }
                )

        # Get action plan from risk assessment
        risk_action_plan = None
        if study.last_risk_assessment:
            risk_scenarios = study.last_risk_assessment.risk_scenarios.all()
            risk_applied_controls = (
                AppliedControl.objects.filter(risk_scenarios__in=risk_scenarios)
                .distinct()
                .order_by("eta")
            )
            if risk_applied_controls.exists():
                risk_action_plan = {
                    "risk_assessment_id": str(study.last_risk_assessment.id),
                    "risk_assessment_name": study.last_risk_assessment.name,
                    "applied_controls": AppliedControlReadSerializer(
                        risk_applied_controls, many=True
                    ).data,
                }

        # Serialize operating modes with graph data
        operating_modes_data = []
        for mode in operating_modes:
            mode_data = OperatingModeReadSerializer(mode).data
            graph_data = build_mode_graph(mode)
            if graph_data:
                mode_data["graph"] = graph_data
            operating_modes_data.append(mode_data)

        # Build comprehensive report data
        report_data = {
            "study": EbiosRMStudyReadSerializer(study).data,
            "feared_events": FearedEventReadSerializer(feared_events, many=True).data,
            "ro_to_couples": RoToReadSerializer(ro_to_couples, many=True).data,
            "stakeholders": StakeholderReadSerializer(stakeholders, many=True).data,
            "strategic_scenarios": StrategicScenarioReadSerializer(
                strategic_scenarios, many=True
            ).data,
            "attack_paths": AttackPathReadSerializer(attack_paths, many=True).data,
            "operational_scenarios": OperationalScenarioReadSerializer(
                operational_scenarios, many=True
            ).data,
            "operating_modes": operating_modes_data,
            "compliance_assessments": compliance_assessments_data,
            "risk_matrix_data": risk_matrix_data,
            "radar": radar_data,
            "compliance_action_plans": compliance_action_plans,
            "risk_action_plan": risk_action_plan,
        }

        return Response(report_data)


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


class RoToFilter(GenericFilterSet):
    # Add the custom ordering filter
    ordering = df.OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("updated_at", "updated_at"),
            ("risk_origin", "risk_origin"),
            ("motivation", "motivation"),
            ("resources", "resources"),
            ("activity", "activity"),
            (
                "pertinence",
                "pertinence",
            ),
        ),
    )

    pertinence = df.MultipleChoiceFilter(
        choices=RoTo.Pertinence.choices, label="Pertinence"
    )

    class Meta:
        model = RoTo
        fields = [
            "ebios_rm_study",
            "is_selected",
            "risk_origin",
            "motivation",
            "feared_events",
            "pertinence",
        ]


class RoToViewSet(BaseModelViewSet):
    model = RoTo

    filterset_class = RoToFilter

    def get_queryset(self):
        """Always return queryset with pertinence annotation"""
        queryset = super().get_queryset()
        return queryset.with_pertinence()

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


class NumberInFilter(df.BaseInFilter, df.NumberFilter):
    pass


class StakeholderFilter(df.FilterSet):
    current_criticality = NumberInFilter(method="filter_current_criticality")
    residual_criticality = NumberInFilter(method="filter_residual_criticality")

    class Meta:
        model = Stakeholder
        fields = [
            "ebios_rm_study",
            "is_selected",
            "applied_controls",
            "category",
            "entity",
        ]

    def filter_current_criticality(self, queryset, name, values):
        ids = [obj.id for obj in queryset if obj.current_criticality in values]
        return queryset.filter(id__in=ids)

    def filter_residual_criticality(self, queryset, name, values):
        ids = [obj.id for obj in queryset if obj.residual_criticality in values]
        return queryset.filter(id__in=ids)


class StakeholderViewSet(BaseModelViewSet):
    model = Stakeholder
    filterset_class = StakeholderFilter

    @action(detail=False, name="Get category choices")
    def category(self, request):
        categories = Terminology.objects.filter(
            field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP, is_visible=True
        ).values_list("name", "name")
        return Response(dict(categories))

    @action(detail=False, name="Get chart data")
    def chart_data(self, request):
        return Response(ecosystem_radar_chart_data(Stakeholder.objects.all()))


class StrategicScenarioViewSet(BaseModelViewSet):
    model = StrategicScenario

    filterset_fields = {
        "ebios_rm_study": ["exact"],
        "attack_paths": ["exact", "isnull"],
    }


class AttackPathFilter(GenericFilterSet):
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


class ElementaryActionFilter(GenericFilterSet):
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
        instance: OperatingMode = self.get_object()
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

        # Collect all elementary actions that are part of kill chain steps
        kill_chain_ea_ids = set()
        for step in mo.kill_chain_steps.all():
            kill_chain_ea_ids.add(step.elementary_action.id)
            # Also add antecedents
            for ant in step.antecedents.all():
                kill_chain_ea_ids.add(ant.id)

        # Create nodes only for elementary actions in the kill chain
        kill_chain_eas = mo.elementary_actions.filter(
            id__in=kill_chain_ea_ids
        ).order_by("attack_stage")

        for ea in kill_chain_eas:
            stage = ea.attack_stage
            entry = {"id": ea.id, "label": ea.name, "group": groups.get(stage)}
            if ea.icon:
                entry["icon"] = ea.icon_fa_hex
            nodes.append(entry)
            panel_name = panels.get(stage)
            if panel_name:
                panel_nodes[panel_name].append(ea.id)

        # Build links based on kill chain steps
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
                            "size": 45,
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
