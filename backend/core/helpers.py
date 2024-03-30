from datetime import date, timedelta

from django.db.models import Count
from django.shortcuts import get_object_or_404
from iam.models import Folder, Permission, RoleAssignment, User

from core.serializers import ReferenceControlReadSerializer, ThreatReadSerializer

from .models import *
from .utils import camel_case

STATUS_COLOR_MAP = {  # TODO: Move these kinds of color maps to frontend
    "undefined": "#CCC",
    "planned": "#BFDBFE",
    "active": "#46D39A",
    "inactive": "#E55759",
    "in_progress": "#5470c6",
    "in_review": "#BBF7D0",
    "done": "#46D39A",
    "deprecated": "#E55759",
    "open": "#fac858",
    "mitigate": "#91cc75",
    "accept": "#73c0de",
    "avoid": "#ee6666",
    "on_hold": "#ee6666",
    "transfer": "#91cc75",
}


def applied_control_priority(user: User):
    def get_quadrant(applied_control):
        if applied_control.effort in ["S", "M"]:
            return "1st"
        elif applied_control.effort in ["L", "XL"]:
            return "2nd"
        else:
            return "undefined"

    clusters = {
        "1st": list(),
        "2nd": list(),
        "3rd": list(),
        "4th": list(),
        "undefined": list(),
    }
    (
        object_ids_view,
        object_ids_change,
        object_ids_delete,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, AppliedControl
    )

    for mtg in AppliedControl.objects.filter(id__in=object_ids_view):
        clusters[get_quadrant(mtg)].append(mtg)

    return clusters


def measures_to_review(user: User):
    (
        object_ids_view,
        object_ids_change,
        object_ids_delete,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, AppliedControl
    )
    measures = (
        AppliedControl.objects.filter(id__in=object_ids_view)
        .filter(eta__lte=date.today() + timedelta(days=30))
        .exclude(status__iexact="done")
        .order_by("eta")
    )

    return measures


def compile_project_for_composer(user: User, projects_list: list):
    """
    Compiling information from choosen projects for composer
    """
    compliance_assessments_status = {"values": [], "labels": []}
    applied_control_status = {"values": [], "labels": []}

    # Requirements assessment bar chart
    color_map = {
        "in_progress": "#3b82f6",
        "non_compliant": "#f87171",
        "to_do": "#d1d5db",
        "partially_compliant": "#fde047",
        "not_applicable": "#000000",
        "compliant": "#86efac",
    }
    for st in RequirementAssessment.Status:
        count = (
            RequirementAssessment.objects.filter(status=st)
            .filter(compliance_assessment__project__in=projects_list)
            .count()
        )
        v = {"value": count, "itemStyle": {"color": color_map[st]}}
        compliance_assessments_status["values"].append(v)
        compliance_assessments_status["labels"].append(st.label)

    # Applied controls bar chart
    color_map = {
        "open": "#93c5fd",
        "in_progress": "#fdba74",
        "on_hold": "#f87171",
        "done": "#86efac",
    }
    for st in AppliedControl.Status.choices:
        count = (
            AppliedControl.objects.filter(status=st[0])
            .filter(requirement_assessments__assessment__project__in=projects_list)
            .count()
        )
        v = {"value": count, "itemStyle": {"color": color_map[st[0]]}}
        applied_control_status["values"].append(v)
        applied_control_status["labels"].append(st[1])

    project_objects = []
    for project in projects_list:
        project_objects.append({"project": get_object_or_404(Project, pk=project)})

    return {
        "project_objects": project_objects,
        "compliance_assessments_status": compliance_assessments_status,
        "applied_control_status": applied_control_status,
        "change_usergroup": RoleAssignment.is_access_allowed(
            user=user,
            perm=Permission.objects.get(codename="change_usergroup"),
            folder=Folder.get_root_folder(),
        ),
    }


def get_compliance_assessment_stats(
    compliance_assessment: ComplianceAssessment,
) -> dict:
    """
    Function to calculate requirement groups statistics for a compliance assessment
    Optimization by limiting the calls to the database
    """

    requirement_nodes_candidates = list(
        RequirementNode.objects.filter(framework=compliance_assessment.framework)
    )
    requirement_assessment_candidates = list(
        RequirementAssessment.objects.filter(
            compliance_assessment=compliance_assessment
        )
    )
    requirement_assessment_candidates_per_status = {
        st: [ra for ra in requirement_assessment_candidates if ra.status == st]
        for st in RequirementAssessment.Status
    }

    def _get_all_requirement_nodes_id_in_requirement_node(
        requirement_node: RequirementNode, candidates
    ) -> list:
        requirement_list = []
        requirement_list.extend(
            [req.id for req in candidates if req.parent_urn == requirement_node.urn]
        )
        for rg in [rg for rg in candidates if rg.parent_urn == requirement_node.urn]:
            requirement_list += _get_all_requirement_nodes_id_in_requirement_node(
                rg, candidates
            )
        return requirement_list

    requirement_nodes_statistics = {}
    for requirement_node in requirement_nodes_candidates:
        requirement_nodes_statistics[requirement_node.id] = []
        requirement_id_list = _get_all_requirement_nodes_id_in_requirement_node(
            requirement_node, requirement_nodes_candidates
        )
        for st in RequirementAssessment.Status:
            count = len(
                [
                    a
                    for a in requirement_assessment_candidates_per_status[st]
                    if a.requirement_id in requirement_id_list
                ]
            )
            total = len(requirement_id_list)
            if total > 0:
                requirement_nodes_statistics[requirement_node.id].append(
                    (st, st.label, round(count * 100 / total))
                )
    return requirement_nodes_statistics


def get_sorted_requirement_nodes(
    requirement_nodes: list,
    requirements_assessed: list | None,
) -> dict:
    """
    Recursive function to build framework groups tree
    requirement_nodes: the list of all requirement_nodes
    requirements_assessed: the list of all requirements_assessed
    Returns a dictionary containing key=name and value={"description": description, "style": "leaf|node"}}
    Values are correctly sorted based on order_id
    If order_id is missing, sorting is based on created_at
    """

    # cope for old version not creating order_id correctly
    for req in requirement_nodes:
        if req.order_id is None:
            req.order_id = req.created_at

    requirement_assessment_from_requirement_id = (
        {str(ra.requirement_id): ra for ra in requirements_assessed}
        if requirements_assessed
        else {}
    )

    def get_sorted_requirement_nodes_rec(
        requirement_nodes: list,
        requirements_assessed: list,
        start: list,
    ) -> dict:
        """
        Recursive function to build framework groups tree, within get_sorted_requirements_nodes
        start: the initial list
        """
        result = {}
        for node in start:
            children = [
                requirement_node
                for requirement_node in requirement_nodes
                if requirement_node.parent_urn == node.urn
            ]
            result[str(node.id)] = {
                "urn": node.urn,
                "parent_urn": node.parent_urn,
                "ref_id": node.ref_id,
                "name": node.name,
                "node_content": node.display_long,
                "style": "node",
                "assessable": node.assessable,
                "description": node.description,
                "children": get_sorted_requirement_nodes_rec(
                    requirement_nodes, requirements_assessed, children
                ),
            }
            for req in sorted(
                [
                    requirement_node
                    for requirement_node in requirement_nodes
                    if requirement_node.parent_urn == node.urn
                ],
                key=lambda x: x.order_id,
            ):
                if requirements_assessed:
                    req_as = requirement_assessment_from_requirement_id[str(req.id)]
                    result[str(node.id)]["children"][str(req.id)].update(
                        {
                            "urn": req.urn,
                            "ref_id": req.ref_id,
                            "name": req.name,
                            "description": req.description,
                            "ra_id": str(req_as.id),
                            "status": req_as.status,
                            "status_display": req_as.get_status_display(),
                            "status_i18n": camel_case(req_as.status),
                            "style": "leaf",
                            "threats": ThreatReadSerializer(
                                req.threats.all(), many=True
                            ).data,
                            "reference_controls": ReferenceControlReadSerializer(
                                req.reference_controls.all(), many=True
                            ).data,
                        }
                    )
                else:
                    result[str(node.id)]["children"][str(req.id)].update(
                        {
                            "urn": req.urn,
                            "ref_id": req.ref_id,
                            "name": req.name,
                            "description": req.description,
                            "style": "leaf",
                            "threats": ThreatReadSerializer(
                                req.threats.all(), many=True
                            ).data,
                            "reference_controls": ReferenceControlReadSerializer(
                                req.reference_controls.all(), many=True
                            ).data,
                        }
                    )
        return result

    tree = get_sorted_requirement_nodes_rec(
        requirement_nodes,
        requirements_assessed,
        sorted(
            [rn for rn in requirement_nodes if not rn.parent_urn],
            key=lambda x: x.order_id,
        ),
    )
    return tree


def get_parsed_matrices(user: User, risk_assessments: list | None = None):
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, RiskScenario
    )
    risk_matrices = list()
    if risk_assessments is None:
        risk_matrices = (
            RiskScenario.objects.filter(id__in=object_ids_view)
            .values_list("risk_assessment__risk_matrix__json_definition", flat=True)
            .distinct()
        )
    else:
        risk_matrices = (
            RiskScenario.objects.filter(id__in=object_ids_view)
            .filter(risk_assessment__in=risk_assessments)
            .values_list("risk_assessment__risk_matrix__json_definition", flat=True)
            .distinct()
        )
    parsed_matrices: list = [json.loads(m) for m in risk_matrices]
    return sorted(parsed_matrices, key=lambda m: len(m["risk"]), reverse=True)


def get_risk_field(user: User, field: str):
    """
    Returns a list of the field values of all risks in all matrices
    """
    parsed_matrices = get_parsed_matrices(user)
    return [m["risk"][i][field] for m in parsed_matrices for i in range(len(m["risk"]))]


def get_risk_color_map(user: User):
    """
    Returns a dictionary with the risk abbreviations as keys and its hex color as value
    """
    risk_abbreviations: list = get_risk_field(user, "abbreviation")
    risk_colors: list = get_risk_field(user, "hexcolor")
    return dict(zip(risk_abbreviations, risk_colors))


def get_risk_color_map_name(user: User):
    """
    Returns a dictionary with the risk names as keys and its hex color as value
    """
    risk_names: list = get_risk_field(user, "name")
    risk_colors: list = get_risk_field(user, "hexcolor")
    return dict(zip(risk_names, risk_colors))


def get_risk_color_ordered_list(user: User, risk_assessments_list: list | None = None):
    """
    Returns a list of hex colors ordered by risk matrix and risk
    """
    risk_colors = list()
    encountered_risks = set()
    parsed_matrices = get_parsed_matrices(user, risk_assessments_list)
    for m in parsed_matrices:
        for i in range(len(m["risk"])):
            if m["risk"][i]["name"] in encountered_risks:
                continue
            risk_colors.append(m["risk"][i]["hexcolor"])
            encountered_risks.add(m["risk"][i]["name"])
    return risk_colors


def get_rating_options(user: User) -> list:
    risk_labels: list = get_risk_field(user, "name")
    return [(i, l) for i, l in enumerate(risk_labels)]


def get_rating_options_abbr(user: User):
    risk_abbreviations: list = get_risk_field(user, "abbreviation")
    risk_names: list = get_risk_field(user, "name")
    return list(zip(risk_abbreviations, risk_names))


def get_rating_options_parsed_matrix(user: User, parsed_matrix):
    risk_names: list = [
        f"{parsed_matrix['risk'][i]['name']}" for i in range(len(parsed_matrix["risk"]))
    ]
    return [(i, l) for i, l in enumerate(risk_names)]


def risk_per_status(user: User):
    # NOTE: if we want to skip empty values, we could just use the user_group by using annotation
    # rs_groups =
    # RiskScenario.objects.all().values('treatment').annotate(total=Count('treatment')).order_by('treatment')

    labels = list()
    values = list()
    # Pal ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc']
    #

    # this formatting is a constraint from eCharts
    color_map = {
        "open": "#fac858",
        "mitigate": "#91cc75",
        "accept": "#73c0de",
        "avoid": "#ee6666",
        "transfer": "#3ba272",
    }

    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, RiskScenario
    )
    for st in RiskScenario.TREATMENT_OPTIONS:
        count = (
            RiskScenario.objects.filter(id__in=object_ids_view)
            .filter(treatment=st[0])
            .count()
        )
        v = {
            "value": count,
            "localName": st[0],
            "itemStyle": {"color": color_map[st[0]]},
        }
        values.append(v)
        labels.append(st[1])

    local_lables = [camel_case(str(label)) for label in labels]
    return {"localLables": local_lables, "labels": labels, "values": values}


def applied_control_per_status(user: User):
    values = list()
    labels = list()
    local_lables = list()
    color_map = {
        "undefined": "#CCC",
        "planned": "#BFDBFE",
        "active": "#46D39A",
        "inactive": "#E55759",
    }
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, AppliedControl
    )
    viewable_applied_controls = AppliedControl.objects.filter(id__in=object_ids_view)
    undefined_count = viewable_applied_controls.filter(status__isnull=True).count()
    values.append(
        {"value": undefined_count, "itemStyle": {"color": color_map["undefined"]}}
    )
    for st in AppliedControl.Status.choices:
        count = viewable_applied_controls.filter(status=st[0]).count()
        v = {"value": count, "itemStyle": {"color": color_map[st[0]]}}
        values.append(v)
        labels.append(st[1])
    local_lables = [camel_case(str(label)) for label in labels]
    return {"localLables": local_lables, "labels": labels, "values": values}


def assessment_per_status(user: User, model: RiskAssessment | ComplianceAssessment):
    values = list()
    labels = list()
    local_lables = list()
    color_map = {
        "undefined": "#CCC",
        "planned": "#BFDBFE",
        "in_progress": "#5470c6",
        "in_review": "#BBF7D0",
        "done": "#46D39A",
        "deprecated": "#E55759",
    }
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(Folder.get_root_folder(), user, model)
    viewable_applied_controls = model.objects.filter(id__in=object_ids_view)
    undefined_count = viewable_applied_controls.filter(status__isnull=True).count()
    values.append(
        {"value": undefined_count, "itemStyle": {"color": color_map["undefined"]}}
    )
    for st in model.Status.choices:
        count = viewable_applied_controls.filter(status=st[0]).count()
        v = {"value": count, "itemStyle": {"color": color_map[st[0]]}}
        values.append(v)
        labels.append(st[1])
    local_lables = [camel_case(str(label)) for label in labels]
    return {"localLables": local_lables, "labels": labels, "values": values}


def applied_control_per_cur_risk(user: User):
    output = list()
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, AppliedControl
    )
    for lvl in get_rating_options(user):
        cnt = (
            AppliedControl.objects.filter(id__in=object_ids_view)
            .exclude(status="done")
            .filter(risk_scenarios__current_level=lvl[0])
            .count()
        )
        output.append({"name": lvl[1], "value": cnt})

    return {"values": output}


def applied_control_per_reference_control(user: User):
    indicators = list()
    values = list()
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, AppliedControl
    )

    tmp = (
        AppliedControl.objects.filter(id__in=object_ids_view)
        .values("reference_control__name")
        .annotate(total=Count("reference_control"))
        .order_by("reference_control")
    )
    for entry in tmp:
        indicators.append(entry["reference_control__name"])
        values.append(entry["total"])

    return {
        "indicators": indicators,
        "values": values,
        "min": min(values, default=0) - 1,
        "max": max(values, default=0) + 1,
    }


def aggregate_risks_per_field(
    user: User, field: str, residual: bool = False, risk_assessments: list | None = None
):
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, RiskScenario
    )
    parsed_matrices: list = get_parsed_matrices(
        user=user, risk_assessments=risk_assessments
    )
    values = dict()
    for m in parsed_matrices:
        for i in range(len(m["risk"])):
            if m["risk"][i][field] not in values:
                values[m["risk"][i][field]] = dict()

            if residual:
                count = (
                    RiskScenario.objects.filter(id__in=object_ids_view)
                    .filter(residual_level=i)
                    # .filter(risk_assessment__risk_matrix__name=["name"])
                    .count()
                )  # What the second filter does ? Is this usefull ?
            else:
                count = (
                    RiskScenario.objects.filter(id__in=object_ids_view)
                    .filter(current_level=i)
                    # .filter(risk_assessment__risk_matrix__name=["name"])
                    .count()
                )  # What the second filter does ? Is this usefull ?

            if "count" not in values[m["risk"][i][field]]:
                values[m["risk"][i][field]]["count"] = count
                values[m["risk"][i][field]]["color"] = m["risk"][i]["hexcolor"]
                continue
            values[m["risk"][i][field]]["count"] += count
    return values


def risks_count_per_level(user: User, risk_assessments: list | None = None):
    current_level = list()
    residual_level = list()

    for r in aggregate_risks_per_field(
        user, "name", risk_assessments=risk_assessments
    ).items():
        current_level.append(
            {
                "name": r[0],
                "value": r[1]["count"],
                "color": r[1]["color"],
            }
        )

    for r in aggregate_risks_per_field(
        user, "name", residual=True, risk_assessments=risk_assessments
    ).items():
        residual_level.append(
            {
                "name": r[0],
                "value": r[1]["count"],
                "color": r[1]["color"],
            }
        )
    return {"current": current_level, "residual": residual_level}


def p_risks(user: User):
    p_risks_labels = list()
    p_risks_counts = list()
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(Folder.get_root_folder(), user, Threat)
    for p_risk in Threat.objects.filter(id__in=object_ids_view).order_by("name"):
        p_risks_labels.append(p_risk.name)
        p_risks_counts.append(RiskScenario.objects.filter(threat=p_risk).count())

    return {
        "indicators": p_risks_labels,
        "values": p_risks_counts,
        "min": min(p_risks_counts, default=0) - 1,
        "max": max(p_risks_counts, default=0) + 1,
    }


def p_risks_2(user: User):
    data = list()
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(Folder.get_root_folder(), user, Threat)
    for p_risk in Threat.objects.filter(id__in=object_ids_view).order_by("name"):
        cnt = RiskScenario.objects.filter(threat=p_risk).count()
        if cnt > 0:
            data.append(
                {
                    "value": RiskScenario.objects.filter(threat=p_risk).count(),
                    "name": p_risk.name,
                }
            )
    return data


def risks_per_project_groups(user: User):
    output = list()
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, RiskScenario
    )
    for folder in Folder.objects.all().order_by("name"):
        ri_level = (
            RiskScenario.objects.filter(id__in=object_ids_view)
            .filter(risk_assessment__project__folder=folder)
            .values("current_level")
            .annotate(total=Count("current_level"))
        )
        output.append({"folder": folder, "ri_level": ri_level})
    return output


def get_counters(user: User):
    return {
        "domains": Folder.objects.filter(
            content_type=Folder.ContentType.DOMAIN
        ).count(),
        "projects": Project.objects.all().count(),
        "applied_controls": AppliedControl.objects.all().count(),
        "risk_assessments": RiskAssessment.objects.all().count(),
        "compliance_assessments": ComplianceAssessment.objects.all().count(),
        "policies": Policy.objects.all().count(),
    }


def risk_status(user: User, risk_assessment_list):
    risk_color_map = get_risk_color_map(user)
    names = list()
    risk_abbreviations: list = get_risk_field(user, "abbreviation")
    current_out = {abbr: list() for abbr in risk_abbreviations}
    residual_out = {abbr: list() for abbr in risk_abbreviations}

    rsk_status_out = {
        "open": list(),
        "mitigate": list(),
        "accept": list(),
        "avoid": list(),
        "transfer": list(),
    }
    mtg_status_out = {
        "--": list(),
        "planned": list(),
        "active": list(),
        "inactive": list(),
    }

    max_tmp = list()
    abbreviations = [x[0] for x in get_rating_options_abbr(user)]
    for risk_assessment in risk_assessment_list:
        for lvl in get_rating_options(user):
            abbr = abbreviations[lvl[0]]
            cnt = RiskScenario.objects.filter(
                risk_assessment=risk_assessment, current_level=lvl[0]
            ).count()
            current_out[abbr].append(
                {"value": cnt, "itemStyle": {"color": risk_color_map[abbr]}}
            )

            cnt = RiskScenario.objects.filter(
                risk_assessment=risk_assessment, residual_level=lvl[0]
            ).count()
            residual_out[abbr].append(
                {"value": cnt, "itemStyle": {"color": risk_color_map[abbr]}}
            )

            max_tmp.append(
                RiskScenario.objects.filter(risk_assessment=risk_assessment).count()
            )

        for option in RiskScenario.TREATMENT_OPTIONS:
            cnt = RiskScenario.objects.filter(
                risk_assessment=risk_assessment, treatment=option[0]
            ).count()
            rsk_status_out[option[0]].append(
                {"value": cnt, "itemStyle": {"color": STATUS_COLOR_MAP[option[0]]}}
            )

        for status in AppliedControl.Status.choices:
            cnt = AppliedControl.objects.filter(
                risk_scenarios__risk_assessment=risk_assessment, status=status[0]
            ).count()
            mtg_status_out[status[0]].append(
                {"value": cnt, "itemStyle": {"color": STATUS_COLOR_MAP[status[0]]}}
            )

        names.append(str(risk_assessment.project) + " " + str(risk_assessment.version))

    y_max_rsk = max(max_tmp, default=0) + 1

    return {
        "names": names,
        "current_out": current_out,
        "residual_out": residual_out,
        "rsk_status_out": rsk_status_out,
        "mtg_status_out": mtg_status_out,
        "y_max_rsk": y_max_rsk,
    }


def acceptances_to_review(user: User):
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, RiskAcceptance
    )
    acceptances = (
        RiskAcceptance.objects.filter(id__in=object_ids_view)
        .filter(expiry_date__lte=date.today() + timedelta(days=30))
        .order_by("expiry_date")
    )
    acceptances |= (
        RiskAcceptance.objects.filter(id__in=object_ids_view)
        .filter(approver=user)
        .filter(state="submitted")
    )

    return acceptances


def build_scenario_clusters(risk_assessment: RiskAssessment):
    risk_matrix = risk_assessment.risk_matrix.parse_json()
    grid = risk_matrix["grid"]
    risk_matrix_current = [
        [set() for _ in range(len(grid[0]))] for _ in range(len(grid))
    ]
    risk_matrix_residual = [
        [set() for _ in range(len(grid[0]))] for _ in range(len(grid))
    ]

    for ri in RiskScenario.objects.filter(risk_assessment=risk_assessment).order_by(
        "created_at"
    ):
        if ri.current_level >= 0:
            risk_matrix_current[ri.current_proba][ri.current_impact].add(ri.rid)
        if ri.residual_level >= 0:
            risk_matrix_residual[ri.residual_proba][ri.residual_impact].add(ri.rid)

    return {"current": risk_matrix_current, "residual": risk_matrix_residual}


def compile_risk_assessment_for_composer(user, risk_assessment_list: list):
    rc = risks_count_per_level(user, risk_assessment_list)
    current_level = rc["current"]
    residual_level = rc["residual"]

    untreated = RiskScenario.objects.filter(
        risk_assessment__in=risk_assessment_list
    ).exclude(treatment__in=["mitigate", "accept"])
    untreated_h_vh = (
        RiskScenario.objects.filter(risk_assessment__in=risk_assessment_list)
        .exclude(treatment__in=["mitigate", "accept"])
        .filter(current_level__gte=2)
    )
    accepted = RiskScenario.objects.filter(
        risk_assessment__in=risk_assessment_list
    ).filter(treatment="accept")

    values = list()
    labels = list()

    for st in AppliedControl.Status.choices:
        count = (
            AppliedControl.objects.filter(status=st[0])
            .filter(risk_scenarios__risk_assessment__in=risk_assessment_list)
            .count()
        )
        v = {"value": count, "itemStyle": {"color": STATUS_COLOR_MAP[st[0]]}}
        values.append(v)
        labels.append(st[1])
    local_lables = [camel_case(str(l)) for l in labels]

    risk_assessment_objects = list()

    for _ra in risk_assessment_list:
        synth_table = list()
        _rc = risks_count_per_level(user=user, risk_assessments=[_ra])
        length = len(_rc["current"])
        for i in range(length):
            count_c = _rc["current"][i]["value"]
            count_r = _rc["residual"][i]["value"]
            lvl = _rc["current"][i]["name"]
            color = _rc["current"][i]["color"]
            synth_table.append(
                {"lvl": lvl, "current": count_c, "residual": count_r, "color": color}
            )
        hvh_risks = RiskScenario.objects.filter(risk_assessment__id=_ra).filter(
            current_level__gte=2
        )
        risk_assessment_objects.append(
            {
                "risk_assessment": get_object_or_404(RiskAssessment, pk=_ra),
                "synth_table": synth_table,
                "hvh_risks": hvh_risks,
            }
        )

    return {
        "risk_assessment_objects": risk_assessment_objects,
        "current_level": current_level,
        "residual_level": residual_level,
        "counters": {
            "untreated": untreated.count(),
            "untreated_h_vh": untreated_h_vh.count(),
            "accepted": accepted.count(),
        },
        "riskscenarios": {
            "untreated": untreated,
            "untreated_h_vh": untreated_h_vh,
            "accepted": accepted,
        },
        "applied_control_status": {
            "localLables": local_lables,
            "labels": labels,
            "values": values,
        },
        "colors": get_risk_color_ordered_list(user, risk_assessment_list),
    }
