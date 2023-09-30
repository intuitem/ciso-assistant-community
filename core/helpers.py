from datetime import timedelta
import logging
from .models import *
from iam.models import Folder, RoleAssignment, User, Permission
from django.db.models import Count
from collections import Counter
from django.shortcuts import get_object_or_404
from datetime import date

STATUS_COLOR_MAP = {'open': '#fac858', 'mitigated': '#91cc75', 'accepted': '#73c0de', 'blocker': '#ee6666', 'in_progress': '#5470c6',
                    'on_hold': '#ee6666', 'done': '#91cc75', 'transferred': '#91cc75'}


def get_rating_options(user: User) -> list:
    risk_labels: list = get_risk_field(user, 'name')
    return [(i, l) for i, l in enumerate(risk_labels)]


def get_rating_options_abbr(user: User):
    risk_abbreviations: list = get_risk_field(user, 'abbreviation')
    risk_names: list = get_risk_field(user, 'name')
    return list(zip(risk_abbreviations, risk_names))

def security_measure_per_status(user: User):
    values = list()
    labels = list()
    color_map = {"open": "#93c5fd", "in_progress": "#fdba74",
                 "on_hold": "#f87171", "done": "#86efac"}
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, SecurityMeasure)
    for st in SecurityMeasure.MITIGATION_STATUS:
        count = SecurityMeasure.objects.filter(
            id__in=object_ids_view).filter(status=st[0]).count()
        v = {
            "value": count,
            "itemStyle": {"color": color_map[st[0]]}
        }
        values.append(v)
        labels.append(st[1])
    return {"labels": labels, "values": values}


def security_measure_per_cur_risk(user: User):
    output = list()
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, SecurityMeasure)
    for lvl in get_rating_options(user):
        cnt = SecurityMeasure.objects.filter(id__in=object_ids_view).exclude(
            status='done').count()
        output.append({"name": lvl[1], "value": cnt})

    return {"values": output}


def security_measure_per_security_function(user: User):
    indicators = list()
    values = list()
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, SecurityMeasure)

    tmp = SecurityMeasure.objects.filter(id__in=object_ids_view).values(
        'security_function__name').annotate(total=Count('security_function')).order_by('security_function')
    for entry in tmp:
        indicators.append(entry['security_function__name'])
        values.append(entry['total'])

    return {"indicators": indicators, "values": values, "min": min(values, default=0) - 1, "max": max(values, default=0) + 1}


def get_counters(user: User):
    output = {}
    objects_dict = {
        "SecurityMeasure": SecurityMeasure,
        "Project": Project,
        "Security Function": SecurityFunction,
        "Assessment": Assessment,
        "Evidence": Evidence,
        }
    for name, type in objects_dict.items():
        (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), user, type)
        output[name] = type.objects.filter(id__in=object_ids_view).count()

    return output


def security_measure_priority(user: User):
    def get_quadrant(security_measure):
                if security_measure.effort in ['S', 'M']:
                    return "1st"
                elif security_measure.effort in ['L', 'XL']:
                    return "2nd"
                else:
                    return "undefined"

    clusters = {"1st": list(), "2nd": list(), "3rd": list(),
                "4th": list(), "undefined": list()}
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, SecurityMeasure)

    for mtg in SecurityMeasure.objects.filter(id__in=object_ids_view):
        clusters[get_quadrant(mtg)].append(mtg)

    return clusters


def measures_to_review(user: User):
    (object_ids_view, object_ids_change, object_ids_delete) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, SecurityMeasure)
    measures = SecurityMeasure.objects.filter(id__in=object_ids_view).filter(
        eta__lte=date.today()+timedelta(days=30)
    ).exclude(status__iexact='done'
              ).order_by('eta')

    return measures

def compile_project_for_composer(user: User, projects_list: list):
    """
    Compiling information from choosen projects for composer
    """
    assessments_status = {"values": [], "labels": []}
    security_measure_status = {"values": [], "labels": []}

    # Requirements assessment bar chart
    color_map = {"in_progress": "#3b82f6", "non_compliant": "#f87171",
                 "to_do": "#d1d5db", "partially_compliant": "#fde047",
                 "not_applicable": "#000000", "compliant": "#86efac"}
    for st in RequirementAssessment.Status:
        count = RequirementAssessment.objects.filter(status=st).filter(
            assessment__project__in=projects_list).count()
        v = {
            "value": count,
            "itemStyle": {"color": color_map[st]}
        }
        assessments_status["values"].append(v)
        assessments_status["labels"].append(st.label)

    # Security measures bar chart
    color_map = {"open": "#93c5fd", "in_progress": "#fdba74",
                 "on_hold": "#f87171", "done": "#86efac"}
    for st in SecurityMeasure.MITIGATION_STATUS:
        count = SecurityMeasure.objects.filter(status=st[0]).filter(
            requirement_assessments__assessment__project__in=projects_list).count()
        v = {
            "value": count,
            "itemStyle": {"color": color_map[st[0]]}
        }
        security_measure_status["values"].append(v)
        security_measure_status["labels"].append(st[1])
    
    project_objects = []
    for project in projects_list:
        project_objects.append({"project": get_object_or_404(Project, pk=project)})

    return {
        "project_objects": project_objects,
        "assessments_status": assessments_status,
        "security_measure_status": security_measure_status,
        "view_user": RoleAssignment.has_permission(user, "view_user"), # NOTE: Need to factorize with BaseContextMixin
        "change_usergroup": RoleAssignment.is_access_allowed(user=user, perm=Permission.objects.get(codename="change_usergroup"), folder=Folder.get_root_folder()),
    }


def get_assessment_stats(assessment: Assessment) -> dict:
    """
    Function to calculate requirement groups statistics for an assessment
    Optimization by limiting the calls to the database
    """
    requirement_groups = list(RequirementGroup.objects.filter(framework=assessment.framework))
    requirements_candidates = list(Requirement.objects.filter(framework=assessment.framework))
    requirement_groups_candidates = list(RequirementGroup.objects.filter(framework=assessment.framework))
    requirement_assessment_candidates = list(RequirementAssessment.objects.filter(assessment=assessment))
    requirement_assessment_candidates_per_status = {st:[ra for ra in requirement_assessment_candidates if ra.status==st] for st in RequirementAssessment.Status}

    def _get_all_requirements_id_in_requirement_group(requirement_group: RequirementGroup, reqs, req_groups) -> list:
        requirement_list = []
        requirement_list.extend([req.id for req in reqs if req.parent_urn==requirement_group.urn])
        for rg in [rg for rg in req_groups if rg.parent_urn == requirement_group.urn]:
            requirement_list += _get_all_requirements_id_in_requirement_group(rg, reqs, req_groups)
        return requirement_list

    requirement_groups_statistics = {}
    for requirement_group in requirement_groups:
        requirement_groups_statistics[requirement_group.id] = []
        requirement_id_list = _get_all_requirements_id_in_requirement_group(requirement_group, requirements_candidates, requirement_groups_candidates)
        for st in RequirementAssessment.Status:
            count = len([a for a in requirement_assessment_candidates_per_status[st] if a.requirement_id in requirement_id_list])
            total = len(requirement_id_list)
            requirement_groups_statistics[requirement_group.id].append((st, st.label, round(count*100/total)))
    return requirement_groups_statistics

def get_sorted_requirements_and_groups(requirements: list, requirement_groups: list, requirements_assessed: list = None) -> dict:
    """
    Recursive function to build framework groups tree
    requirements: the list of all requirements
    requirement_groups: the list of all requirement_groups
    requirements_assessed: the list of all requirements_assessed
    Returns a dictionary containing key=name and value={"description": description, "style": "leaf|node"}}
    """
    requirement_assessment_from_requirement_id = {ra.requirement_id:ra for ra in requirements_assessed} if requirements_assessed else {}

    def get_sorted_requirements_and_groups_rec(requirements: list, requirement_groups: list, requirements_assessed: list, start: list) -> dict:
        """
        Recursive function to build framework groups tree, within get_sorted_requirements_and_groups
        start: the initial list
        """
        result = {}
        for req_group in start:
            children = [requirement_group for requirement_group in requirement_groups if requirement_group.parent_urn == req_group.urn]
            result[req_group.id] = {
                    "urn": req_group.urn,
                    "name": req_group.name,
                    "style": "node", 
                    "description": req_group.description, 
                    "children": get_sorted_requirements_and_groups_rec(requirements, requirement_groups, requirements_assessed, children)
                }
            for req in [requirement for requirement in requirements if requirement.parent_urn == req_group.urn]:
                if requirements_assessed:
                    req_as = requirement_assessment_from_requirement_id[req.id]
                    result[req_group.id]["children"].update({req.id: {"urn": req.urn, "name": req.name, "description": req.description,
                                                                          "ra_id":req_as.id, "status": req_as.status,
                                                                          "status_display": req_as.get_status_display(),
                                                                          "style": "leaf", "threats": list(req.threats.all()), "security_functions": list(req.security_functions.all())}})
                else:
                    result[req_group.id]["children"].update({req.id: {"urn": req.urn, "name": req.name, "description": req.description,
                                                                      "style": "leaf", "threats": list(req.threats.all()), "security_functions": list(req.security_functions.all())}})
        return result

    return get_sorted_requirements_and_groups_rec(
        requirements,
        requirement_groups,
        requirements_assessed,
        [rg for rg in requirement_groups if not rg.parent_urn])
