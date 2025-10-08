import json
from collections.abc import MutableMapping
from datetime import date, timedelta
from typing import Optional
from typing import Dict, List

# from icecream import ic
from django.core.exceptions import NON_FIELD_ERRORS as DJ_NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as DjValidationError
from django.conf import settings
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import api_settings
from rest_framework.views import exception_handler as drf_exception_handler

from iam.models import Folder, Permission, RoleAssignment, User
from library.helpers import get_referential_translation

from statistics import mean
import math

from .models import *
from .utils import camel_case

DRF_NON_FIELD_ERRORS = api_settings.NON_FIELD_ERRORS_KEY


def flatten_dict(
    d: MutableMapping, parent_key: str = "", sep: str = "."
) -> MutableMapping:
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


STATUS_COLOR_MAP = {  # TODO: Move these kinds of color maps to frontend
    "undefined": "#CCC",
    "--": "#CCC",
    "to_do": "#BFDBFE",
    "active": "#46D39A",
    "deprecated": "#E55759",
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


def color_css_class(status):
    return {
        "not_assessed": "gray-300",
        "compliant": "green-500",
        "to_do": "gray-400",
        "in_progress": "blue-500",
        "done": "green-500",
        "non_compliant": "red-500",
        "partially_compliant": "yellow-400",
        "not_applicable": "black",
    }.get(status)


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
        .filter(expiry_date__lte=date.today() + timedelta(days=30))
        .order_by("expiry_date")
    )

    return measures


def compile_perimeter_for_composer(user: User, perimeters_list: list):
    """
    Compiling information from choosen perimeters for composer
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
            .filter(compliance_assessment__perimeter__in=perimeters_list)
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
            .filter(requirement_assessments__assessment__perimeter__in=perimeters_list)
            .count()
        )
        v = {"value": count, "itemStyle": {"color": color_map[st[0]]}}
        applied_control_status["values"].append(v)
        applied_control_status["labels"].append(st[1])

    perimeter_objects = []
    for perimeter in perimeters_list:
        perimeter_objects.append(
            {"perimeter": get_object_or_404(Perimeter, pk=perimeter)}
        )

    return {
        "perimeter_objects": perimeter_objects,
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
    requirements_assessed: Optional[list] = None,
    max_score: int = 0,
) -> dict:
    """
    Recursive function to build framework groups tree
    requirement_nodes: the list of all requirement_nodes
    requirements_assessed: the list of all requirements_assessed
    max_score: the maximum score. This is an attribute of the framework
    Returns a dictionary containing key=name and value={"description": description, "style": "leaf|node"}}
    Values are correctly sorted based on order_id
    If order_id is missing, sorting is based on created_at
    """

    # Cope for old version not creating order_id correctly
    for req in requirement_nodes:
        if req.order_id is None:
            req.order_id = req.created_at

    requirement_assessment_from_requirement_id = {
        str(ra.requirement_id): ra for ra in (requirements_assessed or [])
    }

    # Build a dictionary to quickly access children nodes
    children_dict = {}
    for node in requirement_nodes:
        if node.parent_urn not in children_dict:
            children_dict[node.parent_urn] = []
        children_dict[node.parent_urn].append(node)

    # Sort children nodes by order_id
    for key in children_dict:
        children_dict[key].sort(key=lambda x: x.order_id)

    def get_sorted_requirement_nodes_rec(start: list) -> dict:
        """
        Recursive function to build framework groups tree, within get_sorted_requirements_nodes
        start: the initial list
        """
        result = {}
        for node in start:
            req_as = requirement_assessment_from_requirement_id.get(str(node.id))

            node_data = {
                "urn": node.urn,
                "parent_urn": node.parent_urn,
                "ref_id": node.ref_id,
                "name": get_referential_translation(node, "name"),
                "implementation_groups": node.implementation_groups or None,
                "ra_id": str(req_as.id) if req_as else None,
                "status": req_as.status if req_as else None,
                "result": req_as.result if req_as else None,
                "is_scored": req_as.is_scored if req_as else None,
                "score": req_as.score if req_as else None,
                "documentation_score": req_as.documentation_score if req_as else None,
                "max_score": max_score if req_as else None,
                "questions": node.questions,
                "answers": req_as.answers if req_as else None,
                "mapping_inference": req_as.mapping_inference if req_as else None,
                "status_display": req_as.get_status_display() if req_as else None,
                "status_i18n": camel_case(req_as.status) if req_as else None,
                "result_i18n": camel_case(req_as.result)
                if req_as and req_as.result is not None
                else None,
                "node_content": node.display_long,
                "style": "node",
                "assessable": node.assessable,
                "description": get_referential_translation(node, "description"),
                "children": {},
            }

            result[str(node.id)] = node_data

            # Process children nodes recursively
            children = children_dict.get(node.urn, [])
            child_nodes = get_sorted_requirement_nodes_rec(children)
            result[str(node.id)]["children"] = child_nodes

            # Update each child node with associated requirements
            for child in children:
                child_req_as = requirement_assessment_from_requirement_id.get(
                    str(child.id)
                )

                child_data = {
                    "urn": child.urn,
                    "ref_id": child.ref_id,
                    "implementation_groups": child.implementation_groups or None,
                    "name": get_referential_translation(child, "name"),
                    "description": get_referential_translation(child, "description"),
                    "ra_id": str(child_req_as.id) if child_req_as else None,
                    "status": child_req_as.status if child_req_as else None,
                    "is_scored": child_req_as.is_scored if child_req_as else None,
                    "score": child_req_as.score if child_req_as else None,
                    "documentation_score": child_req_as.documentation_score
                    if child_req_as
                    else None,
                    "max_score": max_score if child_req_as else None,
                    "questions": child.questions,
                    "answers": child_req_as.answers if child_req_as else None,
                    "mapping_inference": child_req_as.mapping_inference
                    if child_req_as
                    else None,
                    "status_display": child_req_as.get_status_display()
                    if child_req_as
                    else None,
                    "status_i18n": camel_case(child_req_as.status)
                    if child_req_as
                    else None,
                    "result": child_req_as.result if child_req_as else None,
                    "result_i18n": camel_case(child_req_as.result)
                    if child_req_as and child_req_as.result is not None
                    else None,
                    "style": "leaf",
                }

                result[str(node.id)]["children"][str(child.id)].update(child_data)

        return result

    top_level_nodes = [rn for rn in requirement_nodes if not rn.parent_urn]
    top_level_nodes.sort(key=lambda x: x.order_id)

    tree = get_sorted_requirement_nodes_rec(top_level_nodes)
    return tree


def filter_graph_by_implementation_groups(
    graph: dict[str, dict], implementation_groups: set[str] | None
) -> dict[str, dict]:
    if not implementation_groups:
        return graph

    def should_include_node(node: dict) -> bool:
        node_groups = node.get("implementation_groups")
        if node_groups:
            return any(group in node_groups for group in implementation_groups)

        # Nodes without implementation groups but with children are included
        return bool(node.get("children"))

    filtered_graph = {}
    for key, value in graph.items():
        if value.get("children"):
            value["children"] = filter_graph_by_implementation_groups(
                value["children"], implementation_groups
            )
        if should_include_node(value):
            filtered_graph[key] = value

    return filtered_graph


def get_parsed_matrices(
    user: User, risk_assessments: list | None = None, folder_id=None
):
    scoped_folder = (
        Folder.objects.get(id=folder_id) if folder_id else Folder.get_root_folder()
    )
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(scoped_folder, user, RiskScenario)
    if risk_assessments is None:
        risk_matrices = list(
            RiskScenario.objects.filter(id__in=object_ids_view)
            .values_list("risk_assessment__risk_matrix__json_definition", flat=True)
            .distinct()
        )
    else:
        risk_matrices = list(
            RiskScenario.objects.filter(id__in=object_ids_view)
            .filter(risk_assessment__in=risk_assessments)
            .values_list("risk_assessment__risk_matrix__json_definition", flat=True)
            .distinct()
        )
    return sorted(risk_matrices, key=lambda m: len(m["risk"]), reverse=True)


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
        AppliedControl.Status.UNDEFINED: "#CCC",
        AppliedControl.Status.TO_DO: "#BFDBFE",
        AppliedControl.Status.ACTIVE: "#46D39A",
        AppliedControl.Status.IN_PROGRESS: "#392F5A",
        AppliedControl.Status.ON_HOLD: "#F4D06F",
        AppliedControl.Status.DEPRECATED: "#E55759",
    }
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, AppliedControl
    )
    viewable_applied_controls = AppliedControl.objects.filter(id__in=object_ids_view)
    for st in AppliedControl.Status.choices:
        count = viewable_applied_controls.filter(status=st[0]).count()
        v = {"value": count, "itemStyle": {"color": color_map[st[0]]}}
        values.append(v)
        labels.append(st[1])
    local_lables = [camel_case(str(label)) for label in labels]
    return {"localLables": local_lables, "labels": labels, "values": values}


def task_template_per_status(user: User):
    from core.models import TaskTemplate, TaskNode

    values = list()
    labels = list()
    local_lables = list()
    color_map = {
        "pending": "#BFDBFE",
        "in_progress": "#392F5A",
        "completed": "#46D39A",
        "cancelled": "#E55759",
    }
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, TaskTemplate
    )
    viewable_task_templates = TaskTemplate.objects.filter(id__in=object_ids_view)

    # Count statuses based on the logic:
    # - If not recurrent: get the status of the node
    # - If recurrent: get the status of the last occurrence (most recent past event)
    from django.db.models import Subquery, OuterRef
    from django.utils import timezone

    status_counts = {"pending": 0, "in_progress": 0, "completed": 0, "cancelled": 0}
    today = timezone.localdate()

    # For recurrent templates, get last occurrence status (most recent past)
    last_occurrence_subq = (
        TaskNode.objects.filter(task_template=OuterRef("pk"), due_date__lt=today)
        .order_by("-due_date")
        .values("status")[:1]
    )

    recurrent_with_status = (
        viewable_task_templates.filter(is_recurrent=True)
        .annotate(node_status=Subquery(last_occurrence_subq))
        .values_list("node_status", flat=True)
    )

    # For non-recurrent templates, get the single node's status
    single_node_subq = TaskNode.objects.filter(task_template=OuterRef("pk")).values(
        "status"
    )[:1]

    non_recurrent_with_status = (
        viewable_task_templates.filter(is_recurrent=False)
        .annotate(node_status=Subquery(single_node_subq))
        .values_list("node_status", flat=True)
    )

    # Count statuses
    for status in recurrent_with_status:
        status_counts[status or "pending"] += 1

    for status in non_recurrent_with_status:
        status_counts[status or "pending"] += 1

    for st in TaskNode.TASK_STATUS_CHOICES:
        count = status_counts[st[0]]
        v = {"value": count, "itemStyle": {"color": color_map[st[0]]}}
        values.append(v)
        labels.append(st[1])
    local_lables = [camel_case(str(label)) for label in labels]
    return {"localLables": local_lables, "labels": labels, "values": values}


def get_governance_calendar_data(user: User, year: int = None):
    """
    Generate calendar heatmap data for governance activities.
    Returns activity counts per date for:
    - TaskNode due dates
    - AppliedControl ETAs
    - RiskAcceptance expiry dates
    - RiskAssessment due dates and ETAs
    - ComplianceAssessment due dates and ETAs
    - FindingsAssessment due dates and ETAs
    """
    from core.models import (
        TaskNode,
        AppliedControl,
        RiskAcceptance,
        RiskAssessment,
        ComplianceAssessment,
        FindingsAssessment,
    )
    from datetime import datetime
    from collections import defaultdict

    if year is None:
        year = datetime.now().year

    start_date = datetime(year, 1, 1).date()
    end_date = datetime(year, 12, 31).date()

    # Dictionary to accumulate activity counts per date
    activity_counts = defaultdict(int)

    # Get accessible objects for each model
    (task_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, TaskNode
    )
    (control_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, AppliedControl
    )
    (acceptance_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, RiskAcceptance
    )
    (risk_assessment_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, RiskAssessment
    )
    (compliance_assessment_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, ComplianceAssessment
    )
    (findings_assessment_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, FindingsAssessment
    )

    # Count TaskNode due dates
    task_nodes = TaskNode.objects.filter(
        id__in=task_ids, due_date__gte=start_date, due_date__lte=end_date
    ).values_list("due_date", flat=True)

    for due_date in task_nodes:
        if due_date:
            activity_counts[str(due_date)] += 1

    # Count AppliedControl ETAs
    applied_controls = AppliedControl.objects.filter(
        id__in=control_ids, eta__gte=start_date, eta__lte=end_date
    ).values_list("eta", flat=True)

    for eta in applied_controls:
        if eta:
            activity_counts[str(eta)] += 1

    # Count RiskAcceptance expiry dates
    risk_acceptances = RiskAcceptance.objects.filter(
        id__in=acceptance_ids, expiry_date__gte=start_date, expiry_date__lte=end_date
    ).values_list("expiry_date", flat=True)

    for expiry_date in risk_acceptances:
        if expiry_date:
            activity_counts[str(expiry_date)] += 1

    # Helper function to count assessment dates
    def count_assessment_dates(assessment_ids, model):
        # Count due dates
        due_dates = model.objects.filter(
            id__in=assessment_ids, due_date__gte=start_date, due_date__lte=end_date
        ).values_list("due_date", flat=True)

        for due_date in due_dates:
            if due_date:
                activity_counts[str(due_date)] += 1

        # Count ETAs
        etas = model.objects.filter(
            id__in=assessment_ids, eta__gte=start_date, eta__lte=end_date
        ).values_list("eta", flat=True)

        for eta in etas:
            if eta:
                activity_counts[str(eta)] += 1

    # Count dates from all assessment types
    count_assessment_dates(risk_assessment_ids, RiskAssessment)
    count_assessment_dates(compliance_assessment_ids, ComplianceAssessment)
    count_assessment_dates(findings_assessment_ids, FindingsAssessment)

    # Convert to array format expected by frontend: [[date, value], ...]
    result = [[date_str, count] for date_str, count in sorted(activity_counts.items())]

    return result


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
    # add undefined as the first element in the labels to balance the values
    labels.insert(0, "undefined")
    local_lables = [camel_case(str(label)) for label in labels]
    return {"localLables": local_lables, "labels": labels, "values": values}


def combined_assessments_per_status(user: User):
    """
    Returns assessment counts grouped by status for all three assessment types:
    RiskAssessment, ComplianceAssessment, and FindingsAssessment
    """
    from .models import RiskAssessment, ComplianceAssessment, FindingsAssessment

    # Get all unique statuses across all assessment types
    # Using RiskAssessment.Status as they should all share the same status choices
    all_statuses = ["undefined"] + [
        choice[0] for choice in RiskAssessment.Status.choices
    ]
    status_labels = ["undefined"] + [
        choice[1] for choice in RiskAssessment.Status.choices
    ]

    # Initialize result structure
    result = {"statuses": all_statuses, "status_labels": status_labels, "series": []}

    # Process each assessment type
    assessment_types = [
        ("complianceAssessments", ComplianceAssessment),
        ("riskAssessments", RiskAssessment),
        ("findingsAssessments", FindingsAssessment),
    ]

    for series_name, model in assessment_types:
        # Get accessible objects
        (object_ids_view, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), user, model
        )
        viewable_assessments = model.objects.filter(id__in=object_ids_view)

        # Count by status in a single query
        status_counts = dict(
            viewable_assessments.exclude(status__isnull=True)
            .values_list("status")
            .annotate(count=Count("status"))
        )
        undefined_count = viewable_assessments.filter(status__isnull=True).count()

        # Build data array matching all_statuses order
        data = [undefined_count] + [
            status_counts.get(status, 0) for status in all_statuses[1:]
        ]

        result["series"].append({"name": series_name, "data": data})

    return result


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
            .exclude(status="active")
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
    user: User,
    field: str,
    residual: bool = False,
    inherent: bool = False,
    risk_assessments: list | None = None,
    folder_id=None,
):
    scoped_folder = (
        Folder.objects.get(id=folder_id) if folder_id else Folder.get_root_folder()
    )
    (
        object_ids_view,
        _,
        _,
    ) = RoleAssignment.get_accessible_object_ids(scoped_folder, user, RiskScenario)
    parsed_matrices: list = get_parsed_matrices(
        user=user, risk_assessments=risk_assessments, folder_id=folder_id
    )
    values = dict()
    for m in parsed_matrices:
        for i in range(len(m["risk"])):
            k = get_referential_translation(m["risk"][i], field)
            if k not in values:
                values[k] = dict()

            if residual:
                count = (
                    RiskScenario.objects.filter(id__in=object_ids_view)
                    .filter(residual_level=i)
                    .count()
                )
            elif inherent:
                count = (
                    RiskScenario.objects.filter(id__in=object_ids_view)
                    .filter(inherent_level=i)
                    .count()
                )
            else:
                count = (
                    RiskScenario.objects.filter(id__in=object_ids_view)
                    .filter(current_level=i)
                    .count()
                )

            if "count" not in values[k]:
                values[k]["count"] = count
                values[k]["color"] = m["risk"][i]["hexcolor"]
            else:
                values[k]["count"] += count
    return values


def risks_count_per_level(
    user: User,
    risk_assessments: list | None = None,
    folder_id=None,
    include_inherent=False,
):
    current_level = list()
    residual_level = list()
    inherent_level = list()

    for r in aggregate_risks_per_field(
        user, "name", risk_assessments=risk_assessments, folder_id=folder_id
    ).items():
        current_level.append(
            {
                "name": r[0],
                "value": r[1]["count"],
                "color": r[1]["color"],
            }
        )
    for r in aggregate_risks_per_field(
        user,
        "name",
        residual=True,
        risk_assessments=risk_assessments,
        folder_id=folder_id,
    ).items():
        residual_level.append(
            {
                "name": r[0],
                "value": r[1]["count"],
                "color": r[1]["color"],
            }
        )

    if not include_inherent:
        return {
            "current": current_level,
            "residual": residual_level,
        }

    for r in aggregate_risks_per_field(
        user,
        "name",
        inherent=True,
        risk_assessments=risk_assessments,
        folder_id=folder_id,
    ).items():
        inherent_level.append(
            {
                "name": r[0],
                "value": r[1]["count"],
                "color": r[1]["color"],
            }
        )
    return {
        "current": current_level,
        "residual": residual_level,
        "inherent": inherent_level,
    }


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


def risks_per_perimeter_groups(user: User):
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
            .filter(risk_assessment__perimeter__folder=folder)
            .values("current_level")
            .annotate(total=Count("current_level"))
        )
        output.append({"folder": folder, "ri_level": ri_level})
    return output


def get_counters(user: User):
    # Get all accessible applied controls
    applied_controls_ids = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, AppliedControl
    )[0]

    # Count policies and non-policies separately
    all_applied_controls = AppliedControl.objects.filter(id__in=applied_controls_ids)
    policies_count = all_applied_controls.filter(category="policy").count()
    applied_controls_count = all_applied_controls.exclude(category="policy").count()

    # Get accessible frameworks
    frameworks_ids = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, Framework
    )[0]

    # Get accessible risk acceptances
    risk_acceptances_ids = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, RiskAcceptance
    )[0]

    # Get accessible security exceptions
    security_exceptions_ids = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, SecurityException
    )[0]

    return {
        "domains": len(
            RoleAssignment.get_accessible_object_ids(
                Folder.get_root_folder(), user, Folder
            )[0]
        ),
        "frameworks": len(frameworks_ids),
        "applied_controls": applied_controls_count,
        "policies": policies_count,
        "exceptions": len(security_exceptions_ids),
        "risk_acceptances": len(risk_acceptances_ids),
    }


def build_audits_tree_metrics(user):
    (object_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, Folder
    )
    viewable_domains = Folder.objects.filter(id__in=object_ids)

    tree = list()
    domain_prj_children = list()
    for domain in viewable_domains.exclude(name="Global"):
        block_domain = {"name": domain.name, "children": []}
        domain_prj_children = []
        for perimeter in Perimeter.objects.filter(folder=domain):
            block_prj = {"name": perimeter.name, "domain": domain.name, "children": []}
            children = []
            for audit in ComplianceAssessment.objects.filter(perimeter=perimeter):
                cnt_res = {}
                for result in RequirementAssessment.Result.choices:
                    requirement_assessments = audit.get_requirement_assessments(
                        include_non_assessable=False
                    )
                    cnt_res[result[0]] = len(
                        [
                            requirement
                            for requirement in requirement_assessments
                            if requirement.result == result[0]
                        ]
                    )
                blk_audit = {
                    "name": audit.name,
                    "children": [
                        {
                            "name": "compliant",
                            "value": cnt_res["compliant"],
                        },
                        {
                            "name": "not assessed",
                            "value": cnt_res["not_assessed"],
                        },
                        {
                            "name": "Not Applicable",
                            "value": cnt_res["not_applicable"],
                        },
                        {
                            "name": "partial",
                            "value": cnt_res["partially_compliant"],
                        },
                        {
                            "name": "Non compliant",
                            "value": cnt_res["non_compliant"],
                        },
                    ],
                }
                children.append(blk_audit)
            block_prj["children"] = children
            domain_prj_children.append(block_prj)
        block_domain["children"] = domain_prj_children
        tree.append(block_domain)
    return tree


def build_audits_stats(user, folder_id=None):
    scoped_folder = (
        Folder.objects.get(id=folder_id) if folder_id else Folder.get_root_folder()
    )
    (object_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        scoped_folder, user, ComplianceAssessment
    )
    data = list()
    names = list()
    uuids = list()
    for audit in ComplianceAssessment.objects.filter(id__in=object_ids).order_by(
        "-updated_at"
    )[:10]:
        data.append([rs[0] for rs in audit.get_requirements_result_count()])
        names.append(audit.name)
        uuids.append(audit.id)
    return {"data": data, "names": names, "uuids": uuids}


def csf_functions(user, folder_id=None):
    scoped_folder = (
        Folder.objects.get(id=folder_id) if folder_id else Folder.get_root_folder()
    )
    (object_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        scoped_folder, user, AppliedControl
    )
    viewable_controls = AppliedControl.objects.filter(id__in=object_ids)
    cnt = dict()
    for choice in ReferenceControl.CSF_FUNCTION:
        cnt[choice[0]] = viewable_controls.filter(csf_function=choice[0]).count()
    undefined = viewable_controls.filter(csf_function__isnull=True).count()
    data = [
        {"name": "Govern", "value": cnt["govern"]},
        {"name": "Identify", "value": cnt["identify"]},
        {"name": "Protect", "value": cnt["protect"]},
        {"name": "Detect", "value": cnt["detect"]},
        {"name": "Respond", "value": cnt["respond"]},
        {"name": "Recover", "value": cnt["recover"]},
    ]
    if undefined > 0:
        data.append({"name": "(undefined)", "value": undefined})

    return data


def get_metrics(user: User, folder_id):
    def viewable_items(model, folder_id=None):
        scoped_folder = (
            Folder.objects.get(id=folder_id) if folder_id else Folder.get_root_folder()
        )
        (object_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            scoped_folder, user, model
        )
        return model.objects.filter(id__in=object_ids)

    viewable_controls = viewable_items(AppliedControl, folder_id)
    viewable_risk_assessments = viewable_items(RiskAssessment, folder_id)
    viewable_compliance_assessments = viewable_items(ComplianceAssessment, folder_id)
    viewable_risk_scenarios = viewable_items(RiskScenario, folder_id)
    viewable_threats = viewable_items(Threat, folder_id)
    viewable_risk_acceptances = viewable_items(RiskAcceptance, folder_id)
    viewable_evidences = viewable_items(Evidence, folder_id)
    viewable_requirement_assessments = viewable_items(RequirementAssessment, folder_id)
    controls_count = viewable_controls.count()
    progress_avg = math.ceil(
        mean([x.get_progress() for x in viewable_compliance_assessments] or [0])
    )
    missed_eta_count = (
        viewable_controls.filter(
            eta__lt=date.today(),
        )
        .exclude(status="active")
        .count()
    )

    data = {
        "controls": {
            "total": controls_count,
            "to_do": viewable_controls.filter(status="to_do").count(),
            "in_progress": viewable_controls.filter(status="in_progress").count(),
            "on_hold": viewable_controls.filter(status="on_hold").count(),
            "active": viewable_controls.filter(status="active").count(),
            "deprecated": viewable_controls.filter(status="deprecated").count(),
            "p1": viewable_controls.filter(priority=1).exclude(status="active").count(),
            "eta_missed": missed_eta_count,
        },
        "risk": {
            "assessments": viewable_risk_assessments.count(),
            "scenarios": viewable_risk_scenarios.count(),
            "threats": viewable_threats.filter(risk_scenarios__isnull=False)
            .distinct()
            .count(),
            "acceptances": viewable_risk_acceptances.count(),
        },
        "compliance": {
            "used_frameworks": viewable_compliance_assessments.values("framework_id")
            .distinct()
            .count(),
            "audits": viewable_compliance_assessments.count(),
            "active_audits": viewable_compliance_assessments.filter(
                status__in=["in_progress", "in_review", "done"]
            ).count(),
            "evidences": viewable_evidences.count(),
            "expired_evidences": viewable_evidences.filter(status="expired").count(),
            "non_compliant_items": viewable_requirement_assessments.filter(
                result="non_compliant"
            ).count(),
            "progress_avg": progress_avg,
        },
        "audits_stats": build_audits_stats(user, folder_id),
        "csf_functions": csf_functions(user, folder_id),
    }
    return data


def get_compliance_analytics(user: User, folder_id=None):
    """
    Returns analytics data for compliance assessments structured by:
    Framework -> Domain (folder) -> Assessment details

    Structure:
    {
        "framework_name": {
            "framework_id": "uuid",
            "framework_average": 75.5,
            "domains": [
                {
                    "domain": "Domain Name",
                    "domain_id": "uuid",
                    "domain_average": 80.0,
                    "assessments": [
                        {
                            "assessment_id": "uuid",
                            "assessment_name": "Assessment Name",
                            "progress": 85,
                            "perimeter": "Perimeter Name",
                            "perimeter_id": "uuid",
                            "status": "in_progress"
                        }
                    ]
                }
            ]
        }
    }
    """

    def viewable_items(model, folder_id=None):
        scoped_folder = (
            Folder.objects.get(id=folder_id) if folder_id else Folder.get_root_folder()
        )
        (object_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            scoped_folder, user, model
        )
        return model.objects.filter(id__in=object_ids)

    # Get viewable compliance assessments with related data and progress annotation
    from django.db.models import Count, Q, F, Value, IntegerField, ExpressionWrapper
    from django.db.models.functions import Greatest, Coalesce

    viewable_assessments = (
        viewable_items(ComplianceAssessment, folder_id)
        .select_related("framework", "folder", "perimeter")
        .annotate(
            total_requirements=Count(
                "requirement_assessments",
                filter=Q(requirement_assessments__requirement__assessable=True),
                distinct=True,
            ),
            assessed_requirements=Count(
                "requirement_assessments",
                filter=~Q(
                    requirement_assessments__result=RequirementAssessment.Result.NOT_ASSESSED
                )
                & Q(requirement_assessments__requirement__assessable=True),
                distinct=True,
            ),
            progress=ExpressionWrapper(
                F("assessed_requirements")
                * 100
                / Greatest(Coalesce(F("total_requirements"), Value(0)), Value(1)),
                output_field=IntegerField(),
            ),
        )
    )

    framework_data = {}

    for assessment in viewable_assessments:
        framework_name = assessment.framework.name
        framework_id = str(assessment.framework.id)
        domain_name = assessment.folder.name if assessment.folder else "No Domain"
        domain_id = str(assessment.folder.id) if assessment.folder else None
        perimeter_name = (
            assessment.perimeter.name if assessment.perimeter else "No Perimeter"
        )
        perimeter_id = str(assessment.perimeter.id) if assessment.perimeter else None

        # Initialize framework if not exists
        if framework_name not in framework_data:
            framework_data[framework_name] = {
                "framework_id": framework_id,
                "framework_average": 0,
                "domains": {},
            }

        # Initialize domain if not exists
        if domain_name not in framework_data[framework_name]["domains"]:
            framework_data[framework_name]["domains"][domain_name] = {
                "domain_id": domain_id,
                "domain_average": 0,
                "assessments": [],
            }

        # Add assessment data using annotated progress
        framework_data[framework_name]["domains"][domain_name]["assessments"].append(
            {
                "assessment_id": str(assessment.id),
                "assessment_name": assessment.name,
                "progress": assessment.progress,
                "perimeter": perimeter_name,
                "perimeter_id": perimeter_id,
                "status": assessment.status,
            }
        )

    # Calculate averages
    for framework_name, framework_info in framework_data.items():
        all_framework_progress = []

        for domain_name, domain_info in framework_info["domains"].items():
            # Calculate domain average
            domain_progress = [a["progress"] for a in domain_info["assessments"]]
            domain_info["domain_average"] = (
                round(sum(domain_progress) / len(domain_progress), 1)
                if domain_progress
                else 0
            )

            all_framework_progress.extend(domain_progress)

        # Calculate framework average
        framework_info["framework_average"] = (
            round(sum(all_framework_progress) / len(all_framework_progress), 1)
            if all_framework_progress
            else 0
        )

        # Convert domains dict to list for frontend consumption
        framework_info["domains"] = [
            {"domain": domain_name, **domain_data}
            for domain_name, domain_data in framework_info["domains"].items()
        ]

    return framework_data


def get_instance_metrics():
    """
    Returns the instance metrics such as the number of users, domains, perimeters, etc.
    """
    nb_users = User.objects.all().count()
    nb_first_login = User.objects.filter(first_login=True).count()
    nb_libraries = LoadedLibrary.objects.all().count()
    nb_domains = Folder.objects.filter(content_type="DO").count()
    nb_perimeters = Perimeter.objects.all().count()
    nb_assets = Asset.objects.all().count()
    nb_threats = Threat.objects.all().count()
    nb_functions = ReferenceControl.objects.all().count()
    nb_measures = AppliedControl.objects.all().count()
    nb_evidences = Evidence.objects.all().count()
    nb_compliance_assessments = ComplianceAssessment.objects.all().count()
    nb_risk_assessments = RiskAssessment.objects.all().count()
    nb_risk_scenarios = RiskScenario.objects.all().count()
    nb_risk_acceptances = RiskAcceptance.objects.all().count()
    nb_seats = getattr(settings, "LICENSE_SEATS", 0)
    nb_editors = len(User.get_editors())
    expiration = getattr(settings, "LICENSE_EXPIRATION", -1)

    created_at = int(Folder.get_root_folder().created_at.timestamp())
    last_login_dt = max(
        [
            x["last_login"]
            for x in User.objects.all().values("last_login")
            if x["last_login"]
        ],
        default=None,
    )
    last_login = int(last_login_dt.timestamp()) if last_login_dt else 0

    return {
        "nb_users": nb_users,
        "nb_first_login": nb_first_login,
        "nb_libraries": nb_libraries,
        "nb_domains": nb_domains,
        "nb_perimeters": nb_perimeters,
        "nb_assets": nb_assets,
        "nb_threats": nb_threats,
        "nb_functions": nb_functions,
        "nb_measures": nb_measures,
        "nb_evidences": nb_evidences,
        "nb_compliance_assessments": nb_compliance_assessments,
        "nb_risk_assessments": nb_risk_assessments,
        "nb_risk_scenarios": nb_risk_scenarios,
        "nb_risk_acceptances": nb_risk_acceptances,
        "nb_seats": nb_seats,
        "nb_editors": nb_editors,
        "expiration": expiration,
        "created_at": created_at,
        "last_login": last_login,
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
        "to_do": list(),
        "in_progress": list(),
        "on_hold": list(),
        "active": list(),
        "deprecated": list(),
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

        names.append(
            str(risk_assessment.perimeter) + " " + str(risk_assessment.version)
        )

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
        .filter(approver=user)
        .filter(state__in=["submitted", "accepted"])
        .order_by("expiry_date")
    )

    return acceptances


def build_scenario_clusters(risk_assessment: RiskAssessment, include_inherent=False):
    risk_matrix = risk_assessment.risk_matrix.parse_json()
    grid = risk_matrix["grid"]
    risk_matrix_current = [
        [set() for _ in range(len(grid[0]))] for _ in range(len(grid))
    ]
    risk_matrix_residual = [
        [set() for _ in range(len(grid[0]))] for _ in range(len(grid))
    ]
    risk_matrix_inherent = [
        [set() for _ in range(len(grid[0]))] for _ in range(len(grid))
    ]

    for ri in RiskScenario.objects.filter(risk_assessment=risk_assessment).order_by(
        "created_at"
    ):
        if ri.current_level >= 0:
            risk_matrix_current[ri.current_proba][ri.current_impact].add(ri.ref_id)
        if ri.residual_level >= 0:
            risk_matrix_residual[ri.residual_proba][ri.residual_impact].add(ri.ref_id)
        if include_inherent:
            if ri.inherent_level >= 0:
                risk_matrix_inherent[ri.inherent_proba][ri.inherent_impact].add(
                    ri.ref_id
                )

    clusters = {"current": risk_matrix_current, "residual": risk_matrix_residual}

    if include_inherent:
        clusters["inherent"] = risk_matrix_inherent

    return clusters


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
    # WARNING: this is wrong - FIX ME because we compute the controls multiple times if used accross multiple scenarios
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


def threats_count_per_name(user: User, folder_id=None) -> Dict[str, List]:
    scoped_folder = (
        Folder.objects.get(id=folder_id) if folder_id else Folder.get_root_folder()
    )
    object_ids_view, _, _ = RoleAssignment.get_accessible_object_ids(
        scoped_folder, user, Threat
    )
    viewable_scenarios = RoleAssignment.get_accessible_object_ids(
        scoped_folder, user, RiskScenario
    )[0]

    # Updated field name from 'riskscenario' to 'risk_scenarios'
    threats_with_counts = (
        Threat.objects.filter(id__in=object_ids_view)
        .annotate(
            scenario_count=Count(
                "risk_scenarios",
                filter=models.Q(risk_scenarios__id__in=viewable_scenarios),
            )
        )
        .filter(scenario_count__gt=0)
        .order_by("name")
        .values("name", "scenario_count")
    )

    labels = [{"name": threat["name"]} for threat in threats_with_counts]
    values = [threat["scenario_count"] for threat in threats_with_counts]

    max_offset = max(values, default=0)
    for label in labels:
        label["max"] = max_offset

    return {"labels": labels, "values": values}


def qualifications_count_per_name(user: User, folder_id=None) -> Dict[str, List]:
    scoped_folder = (
        Folder.objects.get(id=folder_id) if folder_id else Folder.get_root_folder()
    )
    viewable_scenarios = RoleAssignment.get_accessible_object_ids(
        scoped_folder, user, RiskScenario
    )[0]

    # Get all risk scenarios that user can view
    risk_scenarios = RiskScenario.objects.filter(id__in=viewable_scenarios)

    # Count occurrences of each qualification
    qualification_counts = {}
    for scenario in risk_scenarios:
        for qualification in scenario.qualifications.all():
            key = qualification.name
            qualification_counts[key] = qualification_counts.get(key, 0) + 1

    # Sort by qualification name and only include those with count > 0
    sorted_qualifications = sorted(
        [(qual, count) for qual, count in qualification_counts.items() if count > 0]
    )

    labels = [qualification for qualification, _ in sorted_qualifications]
    values = [count for _, count in sorted_qualifications]

    return {"labels": labels, "values": values}


def get_folder_content(
    folder: Folder, include_perimeters, viewable_objects, needed_folders
):
    content = []
    for f in Folder.objects.filter(parent_folder=folder).distinct():
        if f.id in viewable_objects or f.id in needed_folders:
            entry = {
                "name": f.name,
                "uuid": f.id,
                "viewable": viewable_objects and f.id in viewable_objects,
            }
            children = get_folder_content(
                f,
                include_perimeters=include_perimeters,
                viewable_objects=viewable_objects,
                needed_folders=needed_folders,
            )
            if len(children) > 0:
                entry.update({"children": children})
            content.append(entry)

    if include_perimeters and folder.id in viewable_objects:
        for p in Perimeter.objects.filter(folder=folder).distinct():
            content.append(
                {
                    "name": p.name,
                    "symbol": "circle",
                    "symbolSize": 10,
                    "itemStyle": {"color": "#222436"},
                    "children": [
                        {
                            "name": "Audits",
                            "symbol": "diamond",
                            "value": ComplianceAssessment.objects.filter(
                                perimeter=p
                            ).count(),
                        },
                        {
                            "name": "Risk assessments",
                            "symbol": "diamond",
                            "value": RiskAssessment.objects.filter(perimeter=p).count(),
                        },
                    ],
                }
            )
    return content


def handle(exc, context):
    # translate django validation error which ...
    # .. causes HTTP 500 status ==> DRF validation which will cause 400 HTTP status
    if isinstance(exc, DjValidationError):
        data = exc.message_dict
        if DJ_NON_FIELD_ERRORS in data:
            data[DRF_NON_FIELD_ERRORS] = data[DJ_NON_FIELD_ERRORS]
            del data[DJ_NON_FIELD_ERRORS]

        exc = DRFValidationError(detail=data)

    return drf_exception_handler(exc, context)


def duplicate_related_objects(
    source_object: models.Model,
    duplicate_object: models.Model,
    target_folder: Folder,
    field_name: str,
):
    """
    Duplicates related objects from a source object to a duplicate object, avoiding duplicates in the target folder.

    Parameters:
    - source_object (object): The source object containing related objects to duplicate.
    - duplicate_object (object): The object where duplicated objects will be linked.
    - target_folder (Folder): The folder where duplicated objects will be stored.
    - field_name (str): The field name representing the related objects in the source
    """

    def process_related_object(
        obj,
        duplicate_object,
        target_folder,
        target_parent_folders,
        sub_folders,
        field_name,
        model_class,
    ):
        """
        Process a single related object: add, link, or duplicate it based on folder and existence checks.
        """

        # Check if the object already exists in the target folder
        existing_obj = get_existing_object(obj, target_folder, model_class)

        if existing_obj:
            # If the object exists in the target folder, link it to the duplicate object
            link_existing_object(duplicate_object, existing_obj, field_name)

        elif obj.folder in target_parent_folders and obj.is_published:
            # If the object's folder is a parent and it's published, link it
            link_existing_object(duplicate_object, obj, field_name)

        elif obj.folder in sub_folders:
            # If the object's folder is a subfolder of the target folder, link it
            link_existing_object(duplicate_object, obj, field_name)

        else:
            # Otherwise, duplicate the object and link it
            duplicate_and_link_object(obj, duplicate_object, target_folder, field_name)

    def get_existing_object(obj, target_folder, model_class):
        """
        Check if an object with the same name already exists in the target folder.
        """
        return model_class.objects.filter(name=obj.name, folder=target_folder).first()

    def link_existing_object(duplicate_object, existing_obj, field_name):
        """
        Link an existing object to the duplicate object by adding it to the related field.
        """
        getattr(duplicate_object, field_name).add(existing_obj)

    def duplicate_and_link_object(new_obj, duplicate_object, target_folder, field_name):
        """
        Duplicate an object and link it to the duplicate object.
        """
        # Get the model of the object
        model_class = new_obj.__class__

        # Extract all fields except the primary key
        field_values = {}
        for field in new_obj._meta.fields:
            if not field.primary_key and not field.auto_created:
                field_values[field.name] = getattr(new_obj, field.name)

        # Apply changes
        field_values["folder"] = target_folder

        # Create the new object
        new_obj = model_class.objects.create(**field_values)
        link_existing_object(duplicate_object, new_obj, field_name)

    model_class = getattr(type(source_object), field_name).field.related_model

    # Get parent and sub-folders of the target folder
    target_parent_folders = list(target_folder.get_parent_folders())
    sub_folders = list(target_folder.get_sub_folders())

    # Get all related objects for the specified field
    related_objects = getattr(source_object, field_name).all()

    # Process each related object
    for obj in related_objects:
        process_related_object(
            obj,
            duplicate_object,
            target_folder,
            target_parent_folders,
            sub_folders,
            field_name,
            model_class,
        )
