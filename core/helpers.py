from datetime import timedelta
import logging
from .models import *
from django.db.models import Count
from collections import Counter

RISK_COLOR_MAP = {"VL": "#BBF7D0", 'L': "#BEF264", 'M': "#FEF08A", 'H': "#FBBF24", 'VH': "#F87171"}
STATUS_COLOR_MAP = {'open': '#fac858', 'mitigated': '#91cc75', 'accepted': '#73c0de', 'blocker': '#ee6666', 'in_progress': '#5470c6',
                    'on_hold': '#ee6666', 'done': '#91cc75'}


def risk_matrix():
    matrix_current = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                      [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                      [0, 0, 0, 0, 0]]
    matrix_residual = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0]]
    map_impact = {'VH': 0, 'H': 1, 'M': 2, 'L': 3, 'VL': 4}
    map_proba = {'VL': 0, 'L': 1, 'M': 2, 'H': 3, 'VH': 4}
    for ri in RiskInstance.objects.all():
        matrix_current[map_impact[ri.current_impact]][map_proba[ri.current_proba]] += 1
        matrix_residual[map_impact[ri.residual_impact]][map_proba[ri.residual_proba]] += 1
    return {'current': matrix_current, 'residual': matrix_residual}


def risk_per_status():
    # NOTE: if we want to skip empty values, we could just use the group by using annotation
    # rs_groups =
    # RiskInstance.objects.all().values('treatment').annotate(total=Count('treatment')).order_by('treatment')

    labels = list()
    values = list()
    # Pal ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc']
    #

    # this formatting is a constraint from eCharts
    color_map = {"open": "#fac858", "mitigated": "#91cc75", "accepted": "#73c0de", "blocker": "#ee6666"}

    for st in RiskInstance.TREATMENT_OPTIONS:
        count = RiskInstance.objects.filter(treatment=st[0]).count()
        v = {
            "value": count,
            "itemStyle": {"color": color_map[st[0]]}
        }
        values.append(v)
        labels.append(st[1])

    return {"labels": labels, "values": values}


def mitigation_per_status():
    values = list()
    labels = list()
    color_map = {"open": "#fac858", "in_progress": "#5470c6", "on_hold": "#ee6666", "done": "#91cc75"}
    for st in Mitigation.MITIGATION_STATUS:
        count = Mitigation.objects.filter(status=st[0]).count()
        v = {
            "value": count,
            "itemStyle": {"color": color_map[st[0]]}
        }
        values.append(v)
        labels.append(st[1])
    return {"labels": labels, "values": values}


def mitigation_per_cur_risk():
    output = list()
    for lvl in RiskInstance.RATING_OPTIONS:
        cnt = Mitigation.objects.exclude(status='done').filter(risk_instance__current_level=lvl[0]).count()
        output.append({"name": lvl[1], "value": cnt})

    return {"values": output}


def mitigation_per_solution():
    indicators = list()
    values = list()

    tmp = Mitigation.objects.all().values('solution__name').annotate(total=Count('solution')).order_by('solution')
    for entry in tmp:
        indicators.append(entry['solution__name'])
        values.append(entry['total'])

    return {"indicators": indicators, "values": values, "min": min(values, default=0) - 1, "max": max(values, default=0) + 1}


def risks_count_per_level():
    current_level = list()
    residual_level = list()

    for lvl in RiskInstance.RATING_OPTIONS:
        count_c = RiskInstance.objects.filter(current_level=lvl[0]).count()
        count_r = RiskInstance.objects.filter(residual_level=lvl[0]).count()
        current_level.append({'name': lvl[1], 'value': count_c})
        residual_level.append({'name': lvl[1], 'value': count_r})

    return {"current": current_level, "residual": residual_level}


def p_risks():
    p_risks_labels = list()
    p_risks_counts = list()
    for p_risk in ParentRisk.objects.order_by('title'):
        p_risks_labels.append(p_risk.title)
        p_risks_counts.append(RiskInstance.objects.filter(parent_risk=p_risk).count())

    return {
        "indicators": p_risks_labels,
        "values": p_risks_counts,
        "min": min(p_risks_counts, default=0) - 1,
        "max": max(p_risks_counts, default=0) + 1,
    }

def p_risks_2():
    data = list()
    for p_risk in ParentRisk.objects.order_by('title'):
        cnt = RiskInstance.objects.filter(parent_risk=p_risk).count()
        if cnt > 0:
            data.append({"value": RiskInstance.objects.filter(parent_risk=p_risk).count(), "name": p_risk.title})
    return data



def risks_per_project_groups():
    output = list()
    for folder in Folder.objects.all().order_by('name'):
        ri_level = RiskInstance.objects.filter(analysis__project__folder=folder).values(
            'current_level').annotate(total=Count('current_level'))
        output.append({"folder": folder, "ri_level": ri_level})
    return output


def get_counters():
    output = {
        "RiskInstance": RiskInstance.objects.count(),   # TODO: Update Name
        "Mitigation": Mitigation.objects.count(),   # TODO: Update Name
        "Analysis": Analysis.objects.count(),   # TODO: Update Name
        "Project": Project.objects.count(), # TODO: Update Name
        "Solution": Solution.objects.count(),   # TODO: Update Name
        "RiskAcceptance": RiskAcceptance.objects.count(),   # TODO: Update Name
        "ShowStopper": RiskInstance.objects.filter(treatment="blocker").count(),    # TODO: Update Name
        "Threat": ParentRisk.objects.count(),
    }
    return output


def mitigation_priority():
    def get_quadrant(mitigation):
        if mitigation.risk_instance.current_level in ['M', 'H', 'VH']:
            if mitigation.effort in ['S', 'M']:
                return "1st"
            elif mitigation.effort in ['L', 'XL']:
                return "2nd"
            else:
                return "undefined"
        else:
            if mitigation.effort in ['S', 'M']:
                return "3rd"
            elif mitigation.effort in ['L', 'XL']:
                return "4th"
            else:
                return "undefined"

    clusters = {"1st": list(), "2nd": list(), "3rd": list(), "4th": list(), "undefined": list()}

    for mtg in Mitigation.objects.all():
        clusters[get_quadrant(mtg)].append(mtg)

    return clusters


def risk_status(analysis_list):
    names = list()
    current_out = {'VL': list(), 'L': list(), 'M': list(), 'H': list(), 'VH': list()}
    residual_out = {'VL': list(), 'L': list(), 'M': list(), 'H': list(), 'VH': list()}

    rsk_status_out = {'open': list(), 'mitigated': list(), 'accepted': list(), 'blocker': list()}
    mtg_status_out = {'open': list(), 'in_progress': list(), 'on_hold': list(), 'done': list()}

    max_tmp = list()
    for analysis in analysis_list:

        for lvl in RiskInstance.RATING_OPTIONS:
            cnt = RiskInstance.objects.filter(analysis=analysis, current_level=lvl[0]).count()
            current_out[lvl[0]].append({'value': cnt, 'itemStyle': {'color': RISK_COLOR_MAP[lvl[0]]}})

            cnt = RiskInstance.objects.filter(analysis=analysis, residual_level=lvl[0]).count()
            residual_out[lvl[0]].append({'value': cnt, 'itemStyle': {'color': RISK_COLOR_MAP[lvl[0]]}})

            max_tmp.append(RiskInstance.objects.filter(analysis=analysis).count())

        for option in RiskInstance.TREATMENT_OPTIONS:
            cnt = RiskInstance.objects.filter(analysis=analysis, treatment=option[0]).count()
            rsk_status_out[option[0]].append({'value': cnt, 'itemStyle': {'color': STATUS_COLOR_MAP[option[0]]}})

        for status in Mitigation.MITIGATION_STATUS:
            cnt = Mitigation.objects.filter(risk_instance__analysis=analysis, status=status[0]).count()
            mtg_status_out[status[0]].append({'value': cnt, 'itemStyle': {'color': STATUS_COLOR_MAP[status[0]]}})

        names.append(str(analysis.project) + ' ' + str(analysis.version))

    y_max_rsk = max(max_tmp, default=0) + 1
    print("y_max_rsk: ", y_max_rsk)

    return {
        'names': names,
        'current_out': current_out,
        'residual_out': residual_out,
        'rsk_status_out': rsk_status_out,
        'mtg_status_out': mtg_status_out,
        "y_max_rsk": y_max_rsk
    }


def risks_levels_per_prj_grp():
    names = list()
    current_out = {'VL': list(), 'L': list(), 'M': list(), 'H': list(), 'VH': list()}
    residual_out = {'VL': list(), 'L': list(), 'M': list(), 'H': list(), 'VH': list()}

    max_tmp = list()
    for folder in Folder.objects.all():

        for lvl in RiskInstance.RATING_OPTIONS:
            cnt = RiskInstance.objects.filter(analysis__project__folder=folder, current_level=lvl[0]).count()
            current_out[lvl[0]].append({'value': cnt, 'itemStyle': {'color': RISK_COLOR_MAP[lvl[0]]}})

            cnt = RiskInstance.objects.filter(analysis__project__folder=folder, residual_level=lvl[0]).count()
            residual_out[lvl[0]].append({'value': cnt, 'itemStyle': {'color': RISK_COLOR_MAP[lvl[0]]}})

            max_tmp.append(RiskInstance.objects.filter(analysis__project__folder=folder).count())

        names.append(str(folder))

    y_max_rsk = max(max_tmp, default=0) + 1

    return {
        'names': names,
        'current_out': current_out,
        'residual_out': residual_out,
        "y_max_rsk": y_max_rsk
    }

def measures_to_review():
    measures = Mitigation.objects.filter(
        eta__lte=date.today()+timedelta(days=30)
        ).exclude(status__iexact='done'
        ).order_by('eta')

    return measures

def acceptances_to_review():
    acceptances = RiskAcceptance.objects.filter(
        expiry_date__lte=date.today()+timedelta(days=30)
        ).exclude(type__iexact='permanent'
        ).order_by('expiry_date')
    
    return acceptances