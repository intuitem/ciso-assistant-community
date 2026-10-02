import io
import uuid

import django_filters as df
import pandas as pd
from django.db.models import Case, F, FloatField, Value, When
from django.http import HttpResponse
from core.serializers import RiskMatrixReadSerializer
from core.views import (
    BaseModelViewSet as AbstractBaseModelViewSet,
    GenericFilterSet,
    SmartOrderingFilter,
    actor_prefetch,
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from core.models import Asset, Terminology
from openpyxl.styles import Alignment

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
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response


import structlog

logger = structlog.get_logger(__name__)

LONG_CACHE_TTL = 60  # mn


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "ebios_rm.serializers"


class EbiosRMStudyViewSet(BaseModelViewSet):
    """
    API endpoint that allows ebios rm studies to be viewed or edited.
    """

    filterset_fields = ["folder", "assets", "genericcollection", "classification"]

    model = EbiosRMStudy

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "folder",
                "reference_entity",
                "risk_matrix",
                "classification__object_classification",
                "responsibility_matrix",
            )
            .prefetch_related(
                "assets__folder",
                "compliance_assessments",
                "risk_assessments",
                actor_prefetch("authors"),
                actor_prefetch("reviewers"),
                "validationflow_set__approver",
                "roto_set",
                "operational_scenarios",
            )
        )

    def _process_responsibility_matrix(self, request) -> None:
        """
        Turn a name typed into the responsibility matrix picker into a matrix.

        Like typed evidences on task templates: reuse a matrix of that name the
        user can see in the study's domain, otherwise create one there through its
        write serializer (default roles for the preset, add permission checked).
        """
        value = request.data.get("responsibility_matrix")
        if not value or not isinstance(value, str):
            return
        try:
            uuid.UUID(value)
            return
        except ValueError:
            pass
        from iam.models import Folder, RoleAssignment
        from pmbok.models import ResponsibilityMatrix
        from pmbok.serializers import ResponsibilityMatrixWriteSerializer

        folder_id = request.data.get("folder")
        if not folder_id and self.kwargs.get("pk"):
            folder_id = self.get_object().folder_id
        folder = Folder.objects.filter(id=folder_id).first()
        if folder is None:
            return
        matrix = ResponsibilityMatrix.objects.filter(
            name=value,
            folder=folder,
            id__in=RoleAssignment.get_viewable_object_ids(
                request.user, ResponsibilityMatrix
            ),
        ).first()
        if matrix is None:
            serializer = ResponsibilityMatrixWriteSerializer(
                data={"name": value, "folder": str(folder.id)},
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            matrix = serializer.save()
        if hasattr(request.data, "_mutable"):
            request.data._mutable = True
        request.data["responsibility_matrix"] = str(matrix.id)

    def create(self, request, *args, **kwargs):
        self._process_responsibility_matrix(request)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._process_responsibility_matrix(request)
        return super().update(request, *args, **kwargs)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(EbiosRMStudy.Status.choices))

    @action(
        detail=False,
        name="Get default EBIOS RM rating scales",
        url_path="rating-kit-defaults",
    )
    def rating_kit_defaults(self, request):
        """Defaults a matrix's `ebios_rm` section falls back to, for `size` levels."""
        from ebios_rm.rating_kit import default_section

        try:
            size = int(request.query_params.get("size", 4))
        except ValueError:
            return Response({"error": "size must be an integer."}, status=400)
        if not 1 <= size <= 64:
            return Response({"error": "size must be between 1 and 64."}, status=400)
        return Response(default_section(size))

    @action(detail=True, name="Get EBIOS RM rating scales", url_path="rating-kit")
    def rating_kit(self, request, pk):
        """Scales and grids of the study's matrix, defaults filled in."""
        study = self.get_object()
        matrix = study.risk_matrix
        return Response(
            {
                **study.rating_kit(translated=True),
                "likelihood": [
                    {"name": level["name"], "hexcolor": level.get("hexcolor")}
                    for level in study.parsed_matrix["probability"]
                ],
                "matrix": {"id": str(matrix.id), "name": str(matrix)},
                "customized": bool(matrix.json_definition.get("ebios_rm")),
            }
        )

    @action(detail=True, name="Get motivation choices")
    def motivation(self, request, pk):
        return Response(ro_to_scale_choices(self.get_object(), "motivation"))

    @action(detail=True, name="Get resources choices")
    def resources(self, request, pk):
        return Response(ro_to_scale_choices(self.get_object(), "resources"))

    @action(detail=True, name="Get activity choices")
    def activity(self, request, pk):
        return Response(ro_to_scale_choices(self.get_object(), "activity"))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get quotation method choices")
    def quotation_method(self, request):
        return Response(
            {
                method.value: method.label
                for method in EbiosRMStudy.AVAILABLE_QUOTATION_METHODS
            }
        )

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
        study = self.get_object()
        return Response(
            ecosystem_radar_chart_data(Stakeholder.objects.filter(ebios_rm_study=study))
        )

    @action(detail=True, name="Get ecosystem circular chart data")
    def ecosystem_circular_chart_data(self, request, pk):
        from .helpers import ecosystem_circular_chart_data

        study = self.get_object()
        return Response(
            ecosystem_circular_chart_data(
                Stakeholder.objects.filter(ebios_rm_study=study)
            )
        )

    @action(detail=True, name="Get EBIOS RM  study visual analysis")
    def visual_analysis(self, request, pk):
        study = self.get_object()
        return Response(ebios_rm_visual_analysis(study))

    @action(detail=True, name="Get EBIOS RM study report data", url_path="report-data")
    def report_data(self, request, pk):
        """
        Endpoint to prepare comprehensive report data for an EBIOS RM study.
        Returns all study attributes and associated objects in a structured format.
        """
        study = self.get_object()

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

        # Get all related data, sorted per issue #3715
        feared_events = FearedEvent.objects.filter(
            ebios_rm_study=study, is_selected=True
        ).order_by("-gravity", "name")
        ro_to_couples = RoTo.objects.filter(
            ebios_rm_study=study, is_selected=True
        ).order_by("-pertinence", "risk_origin__name", "target_objective")
        stakeholders = Stakeholder.objects.filter(
            ebios_rm_study=study, is_selected=True
        ).order_by("entity__name")
        strategic_scenarios = StrategicScenario.objects.filter(ebios_rm_study=study)
        attack_paths = AttackPath.objects.filter(ebios_rm_study=study, is_selected=True)
        operational_scenarios = OperationalScenario.objects.filter(ebios_rm_study=study)

        # Get operating modes for all operational scenarios
        operating_modes = OperatingMode.objects.filter(
            operational_scenario__in=operational_scenarios
        )

        # Build graph data for each operating mode
        def build_mode_graph(mo):
            """Build kill chain steps and elementary actions"""
            from .serializers import KillChainReadSerializer

            steps = mo.kill_chain_steps.all()
            if not steps.exists():
                return None

            kill_chain_steps = KillChainReadSerializer(steps, many=True).data

            ea_ids = {step.elementary_action_id for step in steps}

            eas = ElementaryAction.objects.filter(id__in=ea_ids)
            elementary_actions = [
                {
                    "id": str(ea.id),
                    "name": ea.name,
                    "attack_stage": ea.attack_stage,
                    "icon_fa_class": ea.icon_fa_class,
                }
                for ea in eas
            ]

            return {
                "kill_chain_steps": kill_chain_steps,
                "elementary_actions": elementary_actions,
            }

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

            risk_scenarios = study.last_risk_assessment.risk_scenarios.all().order_by(
                "ref_id"
            )
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

        # Sort strategic scenarios by gravity desc, then name asc
        strategic_scenarios_data = sorted(
            StrategicScenarioReadSerializer(strategic_scenarios, many=True).data,
            key=lambda s: (-s.get("gravity", {}).get("value", -1), s.get("name", "")),
        )

        # Sort operational scenarios by gravity desc, likelihood desc, then name asc
        operational_scenarios_data = sorted(
            OperationalScenarioReadSerializer(operational_scenarios, many=True).data,
            key=lambda s: (
                -s.get("gravity", {}).get("value", -1),
                -s.get("likelihood", {}).get("value", -1),
                s.get("str", ""),
            ),
        )

        # Sort study assets: primary before support, then alphabetical
        study_data = EbiosRMStudyReadSerializer(study).data
        if study_data.get("assets"):
            study_data["assets"] = sorted(
                study_data["assets"],
                key=lambda a: (0 if a.get("type") == "PR" else 1, a.get("str", "")),
            )

        # Build comprehensive report data
        report_data = {
            "study": study_data,
            "feared_events": FearedEventReadSerializer(feared_events, many=True).data,
            "ro_to_couples": RoToReadSerializer(ro_to_couples, many=True).data,
            "stakeholders": StakeholderReadSerializer(stakeholders, many=True).data,
            "strategic_scenarios": strategic_scenarios_data,
            "attack_paths": AttackPathReadSerializer(attack_paths, many=True).data,
            "operational_scenarios": operational_scenarios_data,
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

        study = self.get_object()
        # Get all related data
        feared_events = FearedEvent.objects.filter(ebios_rm_study=study)
        ro_to_couples = RoTo.objects.filter(ebios_rm_study=study)
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
                    "classification": str(study.classification)
                    if study.classification
                    else "",
                    "objectives": study.objectives,
                    "constraints_hypotheses": study.constraints_hypotheses,
                    "responsibility_matrix": str(study.responsibility_matrix)
                    if study.responsibility_matrix
                    else "",
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
                        "target_objective_category": roto.target_objective_category.get_name_translated
                        if roto.target_objective_category
                        else "",
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
                as_kill_chain__operating_mode__operational_scenario__ebios_rm_study=study
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
                most_likely = os.most_likely_operating_mode() or {}
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
                        "most_likely_operating_mode": most_likely.get("str", ""),
                        "critical_steps": " → ".join(
                            step["name"]
                            for step in most_likely.get("critical_steps", [])
                        ),
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
                            [
                                f"{step.elementary_action.name} ({', '.join(asset.name for asset in step.assets.all())})"
                                if step.assets.all()
                                else step.elementary_action.name
                                for step in om.kill_chain_steps.all()
                            ]
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

            # Verify study exists
            try:
                study = EbiosRMStudy.objects.get(id=uuid.UUID(str(study_id)))
            except ValueError, AttributeError, EbiosRMStudy.DoesNotExist:
                return Response(
                    {"error": "EBIOS RM Study not found"},
                    status=http_status.HTTP_404_NOT_FOUND,
                )

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
                    name=feared_event_name, ebios_rm_study=study
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
                    "ebios_rm_study": str(study.id),
                }

                if ref_id:
                    feared_event_data["ref_id"] = ref_id

                serializer = FearedEventWriteSerializer(
                    data=feared_event_data, context={"request": request}
                )

                if serializer.is_valid():
                    try:
                        feared_event = serializer.save()
                    except PermissionDenied as e:
                        return Response(
                            {"error": e.detail},
                            status=http_status.HTTP_403_FORBIDDEN,
                        )

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


def ro_to_scale_choices(study, scale: str) -> dict:
    levels = study.ro_to_scales(translated=True)[scale]
    return {0: "undefined"} | {
        index + 1: level["name"] for index, level in enumerate(levels)
    }


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
            "target_objective_category",
            "motivation",
            "feared_events",
            "pertinence",
        ]


class RoToViewSet(BaseModelViewSet):
    model = RoTo

    filterset_class = RoToFilter

    @action(detail=True, name="Get motivation choices", url_path="motivation")
    def study_motivation(self, request, pk):
        return Response(
            ro_to_scale_choices(self.get_object().ebios_rm_study, "motivation")
        )

    @action(detail=True, name="Get resources choices", url_path="resources")
    def study_resources(self, request, pk):
        return Response(
            ro_to_scale_choices(self.get_object().ebios_rm_study, "resources")
        )

    @action(detail=True, name="Get activity choices", url_path="activity")
    def study_activity(self, request, pk):
        return Response(
            ro_to_scale_choices(self.get_object().ebios_rm_study, "activity")
        )

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


class StakeholderOrderingFilter(SmartOrderingFilter):
    """Remap ordering fields that don't map directly to DB columns.

    FK fields like ``entity`` are redirected to ``entity__name`` so the sort
    is alphabetical instead of by UUID.  Computed properties like
    ``current_criticality`` are backed by SQL annotations so the database
    can ORDER BY them.
    """

    field_remap = {
        "entity": "entity__name",
        "current_criticality": "_current_criticality",
        "residual_criticality": "_residual_criticality",
    }

    @staticmethod
    def _criticality_annotation(prefix):
        denom = F(f"{prefix}_maturity") * F(f"{prefix}_trust")
        return Case(
            When(**{f"{prefix}_maturity": 0}, then=Value(0.0)),
            When(**{f"{prefix}_trust": 0}, then=Value(0.0)),
            default=F(f"{prefix}_dependency")
            * F(f"{prefix}_penetration")
            * 1.0
            / denom,
            output_field=FloatField(),
        )

    def get_valid_fields(self, queryset, view, context=None):
        valid = super().get_valid_fields(queryset, view, context or {})
        valid += [(src, src) for src in self.field_remap if src not in dict(valid)]
        return valid

    def filter_queryset(self, request, queryset, view):
        queryset = queryset.annotate(
            _current_criticality=self._criticality_annotation("current"),
            _residual_criticality=self._criticality_annotation("residual"),
        )
        return super().filter_queryset(request, queryset, view)

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if not ordering:
            return ordering
        remapped = []
        for f in ordering:
            descending = f.startswith("-")
            field = f[1:] if descending else f
            mapped = self.field_remap.get(field, field)
            remapped.append(f"-{mapped}" if descending else mapped)
        return remapped


class StakeholderViewSet(BaseModelViewSet):
    model = Stakeholder
    filterset_class = StakeholderFilter
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        StakeholderOrderingFilter,
    ]

    @action(detail=False, name="Get category choices")
    def category(self, request):
        categories = Terminology.objects.filter(
            field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP, is_visible=True
        ).values_list("name", "name")
        return Response(dict(categories))

    @action(detail=False, name="Get chart data")
    def chart_data(self, request):
        return Response(ecosystem_radar_chart_data(self.get_queryset()))


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

    @action(detail=True, name="Get gravity choices")
    def gravity(self, request, pk):
        strategic_scenario: StrategicScenario = self.get_object()
        undefined = dict([(-1, "--")])
        _choices = dict(
            zip(
                list(range(0, 64)),
                [
                    x["name"]
                    for x in strategic_scenario.ebios_rm_study.parsed_matrix["impact"]
                ],
            )
        )
        return Response(undefined | _choices)


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

    filterset_fields = ["ebios_rm_study", "likelihood", "threats", "techniques"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related("threats", "techniques", "techniques__parent")
        )

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
    class Meta:
        model = ElementaryAction
        fields = ["attack_stage", "threat"]


class ElementaryActionViewSet(BaseModelViewSet):
    model = ElementaryAction

    filterset_class = ElementaryActionFilter

    def get_protected_error_response_data(self, instance, error):
        operating_modes = list(
            OperatingMode.objects.filter(
                kill_chain_steps__elementary_action=instance
            ).distinct()
        )
        names = ", ".join(om.name for om in operating_modes[:10])
        return {
            "detail": (
                f"Cannot delete elementary action '{instance.name}' — it is "
                f"used in {len(operating_modes)} operating mode kill chain(s)"
                + (f": {names}" if names else "")
                + ". Remove it from those kill chains first."
            ),
        }

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

    @action(detail=True, name="Likelihood roll-up of the kill chain steps")
    def quotation(self, request, pk):
        """Cumulative step values under the study's standard or advanced method."""
        mo = self.get_object()
        quotation = mo.quotation()
        if quotation is None:
            return Response({"method": mo.ebios_rm_study.quotation_method})
        return Response(
            {
                "method": mo.ebios_rm_study.quotation_method,
                "likelihood": quotation.likelihood,
                "steps": {
                    step_id: {
                        "probability": quotation.probability[step_id],
                        "difficulty": quotation.difficulty.get(step_id),
                        "likelihood": quotation.step_likelihood[step_id],
                        "critical": step_id in quotation.critical_path,
                    }
                    for step_id in quotation.probability
                },
            }
        )

    @action(detail=True, methods=["post"], name="Save graph for Operating Mode")
    def save_graph(self, request, pk):
        """
        Replace the operating mode's kill chain with the posted graph.

        Each step is keyed by "id": an existing step's UUID updates that step,
        any other key (a client-side id for a node not saved yet) creates one.
        Antecedents reference those keys. Steps left out are deleted. "assets"
        is applied only when sent, so a graph save never drops them.
        """
        from django.db import transaction

        from iam.models import RoleAssignment

        mo = self.get_object()
        kill_chain_steps = request.data.get("kill_chain_steps", [])
        if not isinstance(kill_chain_steps, list):
            return Response(
                {"errors": ["kill_chain_steps must be an array."]}, status=400
            )
        graph_columns = request.data.get("graph_columns", None)

        accessible_ea_ids = set(
            RoleAssignment.get_viewable_object_ids(request.user, ElementaryAction)
        )
        accessible_asset_ids = set(
            RoleAssignment.get_viewable_object_ids(request.user, Asset)
        )
        existing_steps = {str(step.id): step for step in mo.kill_chain_steps.all()}
        scale_size = len(mo.parsed_matrix["probability"])

        errors = []
        parsed = []
        keys = set()
        for i, step in enumerate(kill_chain_steps):
            if not isinstance(step, dict):
                errors.append(f"Step {i}: invalid step payload.")
                continue
            try:
                ea_id = uuid.UUID(str(step.get("elementary_action")))
            except ValueError, AttributeError, TypeError:
                errors.append(f"Step {i}: invalid elementary_action UUID.")
                continue
            if ea_id not in accessible_ea_ids:
                errors.append(f"Step {i}: elementary action is not accessible.")
                continue

            key = str(step.get("id") or ea_id)
            if key in keys:
                errors.append(f"Step {i}: duplicate step id.")
                continue
            keys.add(key)

            logic_operator = step.get("logic_operator")
            if logic_operator and logic_operator not in ("AND", "OR"):
                errors.append(f"Step {i}: logic_operator must be 'AND', 'OR', or null.")

            antecedent_keys = [str(a) for a in step.get("antecedents", []) or []]
            if key in antecedent_keys:
                errors.append(f"Step {i}: a step cannot be its own antecedent.")

            asset_ids = step.get("assets")
            if asset_ids is not None:
                if not isinstance(asset_ids, list):
                    errors.append(f"Step {i}: assets must be an array.")
                    asset_ids = None
                else:
                    try:
                        asset_ids = [uuid.UUID(str(a)) for a in asset_ids]
                    except ValueError, AttributeError, TypeError:
                        errors.append(f"Step {i}: invalid asset UUID.")
                        asset_ids = None
                    else:
                        if not set(asset_ids) <= accessible_asset_ids:
                            errors.append(f"Step {i}: asset is not accessible.")

            ratings = {}
            for field in ("success_probability", "technical_difficulty"):
                if field in step:
                    level = step[field]
                    if not isinstance(level, int) or not -1 <= level < scale_size:
                        errors.append(
                            f"Step {i}: {field} must be an integer between -1 and {scale_size - 1}."
                        )
                    else:
                        ratings[field] = level
            if "success_probability_pct" in step:
                pct = step["success_probability_pct"]
                if pct is not None and (
                    isinstance(pct, bool)
                    or not isinstance(pct, (int, float))
                    or not 0 <= pct <= 100
                ):
                    errors.append(
                        f"Step {i}: success_probability_pct must be between 0 and 100."
                    )
                else:
                    ratings["success_probability_pct"] = pct

            parsed.append(
                {
                    "ratings": ratings,
                    "index": i,
                    "key": key,
                    "ea_id": ea_id,
                    "antecedent_keys": antecedent_keys,
                    "logic_operator": logic_operator,
                    "assets": asset_ids,
                    "position_x": step.get("position_x", 0),
                    "position_y": step.get("position_y", 0),
                }
            )

        stages = dict(
            ElementaryAction.objects.filter(
                id__in={p["ea_id"] for p in parsed}
            ).values_list("id", "attack_stage")
        )
        stage_by_key = {p["key"]: stages.get(p["ea_id"]) for p in parsed}
        for p in parsed:
            for antecedent_key in p["antecedent_keys"]:
                if antecedent_key not in stage_by_key:
                    errors.append(f"Step {p['index']}: unknown antecedent.")
                elif stage_by_key[antecedent_key] > stage_by_key[p["key"]]:
                    errors.append(
                        f"Step {p['index']}: antecedent attack stage must be same or before the action's stage."
                    )

        # Kahn's algorithm: every step must be reachable without a cycle.
        indegree = {p["key"]: 0 for p in parsed}
        successors = {p["key"]: [] for p in parsed}
        for p in parsed:
            for antecedent_key in set(p["antecedent_keys"]):
                if antecedent_key in successors:
                    successors[antecedent_key].append(p["key"])
                    indegree[p["key"]] += 1
        queue = [k for k, d in indegree.items() if d == 0]
        visited = 0
        while queue:
            current = queue.pop()
            visited += 1
            for successor in successors[current]:
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    queue.append(successor)
        if visited != len(parsed):
            errors.append("The kill chain graph contains a cycle.")

        if errors:
            return Response({"errors": errors}, status=400)

        with transaction.atomic():
            if graph_columns is not None:
                mo.graph_columns = graph_columns
                mo.save(update_fields=["graph_columns"])

            saved = {}
            for p in parsed:
                antecedent_count = len(set(p["antecedent_keys"]))
                fields = {
                    "elementary_action_id": p["ea_id"],
                    "logic_operator": p["logic_operator"]
                    if antecedent_count > 1
                    else None,
                    "position_x": p["position_x"],
                    "position_y": p["position_y"],
                    **p["ratings"],
                }
                step = existing_steps.get(p["key"])
                if step is None:
                    step = KillChain.objects.create(
                        operating_mode=mo, folder=mo.folder, **fields
                    )
                else:
                    for name, value in fields.items():
                        setattr(step, name, value)
                    step.save()
                if p["assets"] is not None:
                    step.assets.set(p["assets"])
                saved[p["key"]] = step

            for p in parsed:
                saved[p["key"]].antecedents.set(
                    [saved[k] for k in set(p["antecedent_keys"])]
                )

            kept_ids = {step.id for step in saved.values()}
            mo.kill_chain_steps.exclude(id__in=kept_ids).delete()
            mo.refresh_likelihood()

        return self.build_graph(request, pk)

    @action(detail=True, name="Build graph for Operating Mode")
    def build_graph(self, request, pk):
        mo = self.get_object()
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

        steps = (
            mo.kill_chain_steps.select_related("elementary_action")
            .prefetch_related("antecedents__elementary_action")
            .order_by("elementary_action__attack_stage", "created_at")
        )
        for step in steps:
            ea = step.elementary_action
            entry = {
                "id": step.id,
                "label": ea.name,
                "group": groups.get(ea.attack_stage),
                "elementary_action": ea.id,
            }
            if ea.icon:
                entry["icon"] = ea.icon_fa_hex
            nodes.append(entry)
            panel_name = panels.get(ea.attack_stage)
            if panel_name:
                panel_nodes[panel_name].append(step.id)

        for step in steps:
            antecedents = sorted(
                step.antecedents.all(),
                key=lambda a: a.elementary_action.attack_stage,
            )
            if not antecedents:
                continue
            target = step.id
            if step.logic_operator:
                operator_id = f"{step.id}-{step.logic_operator}"
                nodes.append(
                    {
                        "id": operator_id,
                        "icon": step.logic_operator,
                        "shape": "circle",
                        "size": 45,
                    }
                )
                panel_name = panels.get(antecedents[0].elementary_action.attack_stage)
                if panel_name:
                    panel_nodes[panel_name].append(operator_id)
                links.append({"source": operator_id, "target": step.id})
                target = operator_id
            for antecedent in antecedents:
                links.append({"source": antecedent.id, "target": target})

        return Response(
            {"nodes": nodes, "links": links, "panelNodes": panel_nodes, "mo_id": mo.id}
        )


class KillChainFilter(GenericFilterSet):
    available_antecedents_for = df.UUIDFilter(
        method="filter_available_antecedents_for",
        label="Steps that can precede the given step",
    )
    max_attack_stage = df.NumberFilter(
        field_name="elementary_action__attack_stage", lookup_expr="lte"
    )

    def filter_available_antecedents_for(self, queryset, name, value):
        step = KillChain.objects.filter(id=value).first()
        if step is None:
            return queryset
        return queryset.filter(
            operating_mode=step.operating_mode,
            elementary_action__attack_stage__lte=step.elementary_action.attack_stage,
        ).exclude(id__in={step.id} | step.descendant_ids())

    class Meta:
        model = KillChain
        fields = ["operating_mode", "elementary_action"]


class KillChainViewSet(BaseModelViewSet):
    model = KillChain

    filterset_class = KillChainFilter

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get logic operators choices")
    def logic_operator(self, request):
        return Response(dict(KillChain.LogicOperator.choices))

    def perform_create(self, serializer):
        instance = super().perform_create(serializer)
        instance.operating_mode.refresh_likelihood()
        return instance

    def perform_update(self, serializer):
        instance = super().perform_update(serializer)
        instance.operating_mode.refresh_likelihood()
        return instance

    def perform_destroy(self, instance):
        operating_mode = instance.operating_mode
        super().perform_destroy(instance)
        operating_mode.refresh_likelihood()
