import io

import django_filters as df
import pandas as pd
from django.http import HttpResponse
from core.serializers import RiskMatrixReadSerializer
from core.views import BaseModelViewSet as AbstractBaseModelViewSet, GenericFilterSet
from core.models import Terminology
from iam.models import RoleAssignment
from openpyxl.styles import Alignment
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
                    "progress": assessment.progress,
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

    @action(detail=True, name="Export EBIOS RM study as XLSX", url_path="export-xlsx")
    def export_xlsx(self, request, pk):
        """Export EBIOS RM study data to Excel with multiple sheets."""
        study = get_object_or_404(EbiosRMStudy, id=pk)

        # Get all related data
        feared_events = FearedEvent.objects.filter(ebios_rm_study=study)
        ro_to_couples = RoTo.objects.filter(ebios_rm_study=study).with_pertinence()
        stakeholders = Stakeholder.objects.filter(ebios_rm_study=study)
        strategic_scenarios = StrategicScenario.objects.filter(ebios_rm_study=study)
        attack_paths = AttackPath.objects.filter(ebios_rm_study=study)
        operational_scenarios = OperationalScenario.objects.filter(ebios_rm_study=study)

        buffer = io.BytesIO()

        # Sheet names prefixed with workshop.activity for i18n and organization
        SHEET_NAMES = {
            "study": "1.1 Study",
            "assets": "1.2 Assets",
            "feared_events": "1.3 Feared Events",
            "ro_to": "2.1 RO-TO Couples",
            "stakeholders": "3.1 Stakeholders",
            "strategic_scenarios": "3.2.1 Strategic Scenarios",
            "attack_paths": "3.2.2 Attack Paths",
            "stakeholder_controls": "3.3 Stakeholder Controls",
            "elementary_actions": "4.0 Elementary Actions",
            "operational_scenarios": "4.1.1 Operational Scenarios",
            "operating_modes": "4.1.2 Operating Modes",
        }

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            # 1.1 Study sheet
            study_data = [
                {
                    "ref_id": study.ref_id,
                    "name": study.name,
                    "description": study.description or "",
                    "version": study.version or "",
                    "status": study.status or "",
                    "eta": str(study.eta) if study.eta else "",
                    "due_date": str(study.due_date) if study.due_date else "",
                    "observation": study.observation or "",
                }
            ]
            df_study = pd.DataFrame(study_data)
            df_study.to_excel(writer, sheet_name=SHEET_NAMES["study"], index=False)

            # 1.2 Assets sheet
            assets_data = []
            for asset in study.assets.all():
                assets_data.append(
                    {
                        "ref_id": asset.ref_id or "",
                        "name": asset.name,
                        "description": asset.description or "",
                        "type": asset.type or "",
                        "parent_asset": asset.parent_assets.first().name
                        if asset.parent_assets.exists()
                        else "",
                    }
                )
            if assets_data:
                df_assets = pd.DataFrame(assets_data)
                df_assets.to_excel(
                    writer, sheet_name=SHEET_NAMES["assets"], index=False
                )

            # 1.3 Feared Events sheet
            fe_data = []
            for fe in feared_events:
                fe_data.append(
                    {
                        "ref_id": fe.ref_id,
                        "name": fe.name,
                        "description": fe.description or "",
                        "gravity": fe.get_gravity_display().get("name", ""),
                        "is_selected": fe.is_selected,
                        "justification": fe.justification or "",
                        "assets": "\n".join([a.name for a in fe.assets.all()]),
                    }
                )
            if fe_data:
                df_fe = pd.DataFrame(fe_data)
                df_fe.to_excel(
                    writer, sheet_name=SHEET_NAMES["feared_events"], index=False
                )

            # 1.4.x Compliance Assessment sheets
            for idx, ca in enumerate(study.compliance_assessments.all(), start=1):
                ca_data = []
                for ra in (
                    ca.requirement_assessments.select_related("requirement")
                    .prefetch_related("applied_controls")
                    .order_by("requirement__order_id")
                ):
                    req = ra.requirement
                    # Skip non-assessable items
                    if not req.assessable:
                        continue
                    ca_data.append(
                        {
                            "urn": req.urn or "",
                            "ref_id": req.ref_id or "",
                            "name": req.name or "",
                            "description": req.description or "",
                            "result": ra.get_result_display(),
                            "observation": ra.observation or "",
                            "applied_controls": "\n".join(
                                [ac.name for ac in ra.applied_controls.all()]
                            ),
                        }
                    )
                if ca_data:
                    # Sheet name: "1.4.1 AuditName" (max 31 chars for Excel)
                    sheet_name = f"1.4.{idx} {ca.name}"[:31]
                    df_ca = pd.DataFrame(ca_data)
                    df_ca.to_excel(writer, sheet_name=sheet_name, index=False)

            # 2.1 RO/TO Couples sheet
            roto_data = []
            for roto in ro_to_couples:
                roto_data.append(
                    {
                        "risk_origin": roto.risk_origin.get_name_translated
                        if roto.risk_origin
                        else "",
                        "target_objective": roto.target_objective,
                        "motivation": roto.get_motivation_display(),
                        "resources": roto.get_resources_display(),
                        "activity": roto.get_activity_display(),
                        "pertinence": roto.get_pertinence_display(),
                        "is_selected": roto.is_selected,
                        "justification": roto.justification or "",
                        "feared_events": "\n".join(
                            [fe.name for fe in roto.feared_events.all()]
                        ),
                    }
                )
            if roto_data:
                df_roto = pd.DataFrame(roto_data)
                df_roto.to_excel(writer, sheet_name=SHEET_NAMES["ro_to"], index=False)

            # 3.1 Stakeholders sheet
            sh_data = []
            for sh in stakeholders:
                sh_data.append(
                    {
                        "entity": sh.entity.name if sh.entity else "",
                        "category": sh.category.get_name_translated
                        if sh.category
                        else "",
                        "current_dependency": sh.current_dependency,
                        "current_penetration": sh.current_penetration,
                        "current_maturity": sh.current_maturity,
                        "current_trust": sh.current_trust,
                        "current_criticality": sh.get_current_criticality_display(),
                        "residual_dependency": sh.residual_dependency,
                        "residual_penetration": sh.residual_penetration,
                        "residual_maturity": sh.residual_maturity,
                        "residual_trust": sh.residual_trust,
                        "residual_criticality": sh.get_residual_criticality_display(),
                        "is_selected": sh.is_selected,
                        "justification": sh.justification or "",
                    }
                )
            if sh_data:
                df_sh = pd.DataFrame(sh_data)
                df_sh.to_excel(
                    writer, sheet_name=SHEET_NAMES["stakeholders"], index=False
                )

            # 3.2.1 Strategic Scenarios sheet
            ss_data = []
            for ss in strategic_scenarios:
                roto = ss.ro_to_couple
                ss_data.append(
                    {
                        "ref_id": ss.ref_id,
                        "name": ss.name,
                        "description": ss.description or "",
                        "risk_origin": roto.risk_origin.get_name_translated
                        if roto and roto.risk_origin
                        else "",
                        "target_objective": roto.target_objective if roto else "",
                        "gravity": ss.get_gravity_display().get("name", ""),
                    }
                )
            if ss_data:
                df_ss = pd.DataFrame(ss_data)
                df_ss.to_excel(
                    writer, sheet_name=SHEET_NAMES["strategic_scenarios"], index=False
                )

            # 3.2 Attack Paths sheet
            ap_data = []
            for ap in attack_paths:
                ap_data.append(
                    {
                        "ref_id": ap.ref_id,
                        "name": ap.name,
                        "description": ap.description or "",
                        "strategic_scenario": ap.strategic_scenario.name
                        if ap.strategic_scenario
                        else "",
                        "stakeholders": "\n".join(
                            [str(s) for s in ap.stakeholders.all()]
                        ),
                        "is_selected": ap.is_selected,
                        "justification": ap.justification or "",
                    }
                )
            if ap_data:
                df_ap = pd.DataFrame(ap_data)
                df_ap.to_excel(
                    writer, sheet_name=SHEET_NAMES["attack_paths"], index=False
                )

            # 3.3 Stakeholder Controls sheet
            from core.models import AppliedControl

            stakeholder_controls = AppliedControl.objects.filter(
                stakeholders__ebios_rm_study=study
            ).distinct()
            sc_data = []
            for ac in stakeholder_controls:
                sc_data.append(
                    {
                        "ref_id": ac.ref_id or "",
                        "name": ac.name,
                        "description": ac.description or "",
                        "status": ac.get_status_display(),
                        "stakeholders": "\n".join(
                            [
                                str(s)
                                for s in ac.stakeholders.filter(ebios_rm_study=study)
                            ]
                        ),
                    }
                )
            if sc_data:
                df_sc = pd.DataFrame(sc_data)
                df_sc.to_excel(
                    writer, sheet_name=SHEET_NAMES["stakeholder_controls"], index=False
                )

            # 4.0 Elementary Actions sheet
            elementary_actions = ElementaryAction.objects.filter(
                operating_modes__operational_scenario__ebios_rm_study=study
            ).distinct()
            ea_data = []
            for ea in elementary_actions:
                ea_data.append(
                    {
                        "ref_id": ea.ref_id or "",
                        "name": ea.name,
                        "description": ea.description or "",
                        "attack_stage": ea.get_attack_stage_display(),
                        "icon": ea.get_icon_display() if ea.icon else "",
                    }
                )
            if ea_data:
                df_ea = pd.DataFrame(ea_data)
                df_ea.to_excel(
                    writer, sheet_name=SHEET_NAMES["elementary_actions"], index=False
                )

            # 4.1.1 Operational Scenarios sheet
            os_data = []
            for os in operational_scenarios:
                os_data.append(
                    {
                        "ref_id": os.ref_id,
                        "name": os.name,
                        "attack_path": os.attack_path.name if os.attack_path else "",
                        "likelihood": os.get_likelihood_display().get("name", ""),
                        "gravity": os.get_gravity_display().get("name", ""),
                        "risk_level": os.get_risk_level_display().get("name", ""),
                        "operating_modes_description": os.operating_modes_description
                        or "",
                        "is_selected": os.is_selected,
                        "justification": os.justification or "",
                    }
                )
            if os_data:
                df_os = pd.DataFrame(os_data)
                df_os.to_excel(
                    writer, sheet_name=SHEET_NAMES["operational_scenarios"], index=False
                )

            # 4.1.2 Operating Modes sheet
            operating_modes = OperatingMode.objects.filter(
                operational_scenario__ebios_rm_study=study
            )
            om_data = []
            for om in operating_modes:
                om_data.append(
                    {
                        "ref_id": om.ref_id or "",
                        "name": om.name,
                        "description": om.description or "",
                        "operational_scenario": om.operational_scenario.name
                        if om.operational_scenario
                        else "",
                        "likelihood": om.get_likelihood_display().get("name", ""),
                        "elementary_actions": "\n".join(
                            [ea.name for ea in om.elementary_actions.all()]
                        ),
                    }
                )
            if om_data:
                df_om = pd.DataFrame(om_data)
                df_om.to_excel(
                    writer, sheet_name=SHEET_NAMES["operating_modes"], index=False
                )

            # Apply styling to all sheets
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for col_idx, col in enumerate(worksheet.columns, 1):
                    worksheet.column_dimensions[col[0].column_letter].width = 20
                    for cell in col[1:]:
                        cell.alignment = Alignment(wrap_text=True, vertical="top")

        buffer.seek(0)

        filename = f"ebios-rm-{study.ref_id or study.name[:20]}.xlsx"
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


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

    @action(detail=False, methods=["post"], url_path="batch-create")
    def batch_create(self, request):
        """
        Batch create multiple feared events from a text list.
        Expected format:
        {
            "feared_events_text": "Feared Event 1\\nFeared Event 2\\nREF-001:Feared Event 3",
            "ebios_rm_study": "study-uuid"
        }
        Lines can optionally have a ref_id prefix (REF-001:Feared Event Name).
        Feared events with the same name in the study will be skipped.
        """
        from rest_framework import status as http_status
        from ebios_rm.serializers import FearedEventWriteSerializer
        import structlog

        logger = structlog.get_logger(__name__)

        try:
            feared_events_text = request.data.get("feared_events_text", "")
            study_id = request.data.get("ebios_rm_study")

            if not feared_events_text:
                return Response(
                    {"error": "feared_events_text is required"},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )

            if not study_id:
                return Response(
                    {"error": "ebios_rm_study is required"},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )

            # Verify study exists and user has access
            if not RoleAssignment.is_object_readable(
                request.user, EbiosRMStudy, study_id
            ):
                return Response(
                    {"error": "EBIOS RM Study not found"},
                    status=http_status.HTTP_404_NOT_FOUND,
                )
            study = EbiosRMStudy.objects.get(id=study_id)

            # Parse the feared events text
            lines = [
                line.strip() for line in feared_events_text.split("\n") if line.strip()
            ]
            created_feared_events = []
            skipped_feared_events = []
            errors = []

            for line in lines:
                # Check for ref_id prefix (REF-001:Feared Event Name)
                ref_id = ""
                feared_event_name = line

                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2 and parts[0].strip():
                        ref_id = parts[0].strip()
                        feared_event_name = parts[1].strip()

                if not feared_event_name:
                    errors.append({"line": line, "error": "Empty feared event name"})
                    continue

                # Check if feared event already exists in the study
                existing_feared_event = FearedEvent.objects.filter(
                    name=feared_event_name, ebios_rm_study=study_id
                ).first()

                if existing_feared_event:
                    # Skip existing feared event
                    skipped_feared_events.append(
                        {
                            "id": str(existing_feared_event.id),
                            "name": existing_feared_event.name,
                            "ref_id": existing_feared_event.ref_id,
                        }
                    )
                    continue

                # Create new feared event using the serializer to respect IAM
                feared_event_data = {
                    "name": feared_event_name,
                    "ebios_rm_study": study_id,
                }

                if ref_id:
                    feared_event_data["ref_id"] = ref_id

                serializer = FearedEventWriteSerializer(
                    data=feared_event_data, context={"request": request}
                )

                if serializer.is_valid():
                    feared_event = serializer.save()

                    created_feared_events.append(
                        {
                            "id": str(feared_event.id),
                            "name": feared_event.name,
                            "ref_id": feared_event.ref_id,
                        }
                    )
                else:
                    errors.append(
                        {
                            "line": line,
                            "errors": serializer.errors,
                        }
                    )

            return Response(
                {
                    "created": len(created_feared_events),
                    "skipped": len(skipped_feared_events),
                    "feared_events": created_feared_events,
                    "skipped_feared_events": skipped_feared_events,
                    "errors": errors,
                },
                status=http_status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error("Error in batch create feared events", error=str(e))
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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

    def get_queryset(self):
        """Optimize queryset to prefetch feared events from ro_to_couple"""
        queryset = super().get_queryset()
        return queryset.select_related("ro_to_couple").prefetch_related(
            "ro_to_couple__feared_events"
        )


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

    def perform_create(self, serializer):
        if not serializer.validated_data.get(
            "ref_id"
        ) and serializer.validated_data.get("strategic_scenario"):
            strategic_scenario = serializer.validated_data["strategic_scenario"]
            ref_id = AttackPath.get_default_ref_id(strategic_scenario)
            serializer.validated_data["ref_id"] = ref_id
        serializer.save()


class OperationalScenarioViewSet(BaseModelViewSet):
    model = OperationalScenario

    filterset_fields = ["ebios_rm_study", "likelihood"]

    @action(detail=True, name="Get risk matrix", url_path="risk-matrix")
    def risk_matrix(self, request, pk=None):
        attack_path = self.get_object()
        return Response(RiskMatrixReadSerializer(attack_path.risk_matrix).data)

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
