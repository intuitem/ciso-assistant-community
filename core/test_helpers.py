import logging
from .models import *
from .helpers import *
from django.db.models import Count
from collections import Counter
import pytest

RISK_COLOR_MAP = {"VL": "#BBF7D0", 'L': "#BEF264", 'M': "#FEF08A", 'H': "#FBBF24", 'VH': "#F87171"}
STATUS_COLOR_MAP = {'open': '#fac858', 'mitigated': '#91cc75', 'accepted': '#73c0de', 'blocker': '#ee6666', 'in_progress': '#5470c6',
                    'on_hold': '#ee6666', 'done': '#91cc75'}
risk = {}

@pytest.fixture()
def test_setUp(db):
    risk["parentgroup"] = ProjectsGroup.objects.create(name = "Test ProjectsGroup")
    risk["project"] = Project.objects.create(name = "Test project", parent_group = risk.get("parentgroup"))
    risk["analysis"] = Analysis.objects.create(project = risk.get("project"))
    risk["parentrisk"] = ParentRisk.objects.create(title = "Test ParentRisk")
    risk["riskinstance"] = RiskInstance.objects.create(title = "Test Ri", analysis = risk.get("analysis"), 
                           parent_risk = risk.get("parentrisk"), current_proba = "H", current_impact="L"),
    risk["solution_one"] = Solution.objects.create(name = "Test SolutionOne")
    risk["solution_two"] = Solution.objects.create(name = "Test SolutionTwo")
    risk["mitigation"] = Mitigation.objects.create(title = "Test Mitigation", risk_instance = RiskInstance.objects.get(title = "Test Ri"), 
                         solution = Solution.objects.get(name = "Test SolutionOne"), effort = 'L')

def test_risk_matrix(db, test_setUp):
    matrix_current = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], 
                      [0, 0, 0, 0, 0], [0, 0, 0, 1, 0], 
                      [0, 0, 0, 0, 0]]
    matrix_residual = [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                       [1, 0, 0, 0, 0]]
    assert risk_matrix() == {'current': matrix_current, 'residual': matrix_residual}

def test_risk_per_status(db, test_setUp):
    assert risk_per_status() == {'labels': ['Open', 'Mitigated', 'Accepted', 'Show-stopper'], 'values': [{'value': 1, 'itemStyle': {'color': '#fac858'}}, 
                                {'value': 0, 'itemStyle': {'color': '#91cc75'}}, {'value': 0, 'itemStyle': {'color': '#73c0de'}}, 
                                {'value': 0, 'itemStyle': {'color': '#ee6666'}}]}

def test_mitigation_per_status(db, test_setUp):
    assert mitigation_per_status() == {'labels': ['Open', 'In Progress', 'On Hold', 'Done'], 'values': [{'itemStyle': {'color': '#fac858'}, 'value': 1}, 
                                      {'itemStyle': {'color': '#5470c6'}, 'value': 0}, {'itemStyle': {'color': '#ee6666'}, 'value': 0}, 
                                      {'itemStyle': {'color': '#91cc75'}, 'value': 0}]}

def test_mitigation_per_cur_risk(db, test_setUp):
    assert mitigation_per_cur_risk() == {'values': [{'name': 'Very Low', 'value': 0}, {'name': 'Low', 'value': 0}, {'name': 'Medium', 'value': 1}, 
                                        {'name': 'High', 'value': 0}, {'name': 'Very High', 'value': 0}]}

def test_mitigation_per_solution(db, test_setUp):
    assert mitigation_per_solution() == {'indicators': ['Test SolutionOne'], 'values': [1], 'min': 0, 'max': 2}

def test_risks_count_per_level(db, test_setUp):
    assert risks_count_per_level() == {'current': [{'name': 'Very Low', 'value': 0}, {'name': 'Low', 'value': 0}, {'name': 'Medium', 'value': 1}, 
                                      {'name': 'High', 'value': 0}, {'name': 'Very High', 'value': 0}], 'residual': [{'name': 'Very Low', 'value': 1}, 
                                      {'name': 'Low', 'value': 0}, {'name': 'Medium', 'value': 0}, {'name': 'High', 'value': 0}, {'name': 'Very High', 'value': 0}]}

def test_p_risks(db, test_setUp):
    assert p_risks() == {'indicators': ['Test ParentRisk'], 'values': [1], 'min': 0, 'max': 2}

def test_p_risks_2(db, test_setUp):
    assert p_risks_2() == [{'value': 1, 'name': 'Test ParentRisk'}]

def test_risks_per_project_groups(db, test_setUp): # Syntax problem, not good to compare strings, to review!
    assert str(risks_per_project_groups()) == "[{'prj_grp': <ProjectsGroup: Test ProjectsGroup>, 'ri_level': <QuerySet [{'current_level': 'M', 'total': 1}]>}]"

def test_get_counters(db, test_setUp):
    assert get_counters() == {'RiskInstance': 1, 'Mitigation': 1, 'Analysis': 1, 'Project': 1, 'Solution': 2, 'RiskAcceptance': 0, 'ShowStopper': 0}

def test_mitigation_priority(db, test_setUp): # Syntax problem, not good to compare strings, to review!
    assert str(mitigation_priority()) == "{'1st': [], '2nd': [<Mitigation: Test Mitigation>], '3rd': [], '4th': [], 'undefined': []}"

def test_risk_status(db, test_setUp):
    list = [risk.get('analysis')]
    assert risk_status(list) == {'names': ['Test project 0.1'], 
                                 'current_out': {'VL': [{'value': 0, 'itemStyle': {'color': '#BBF7D0'}}], 'L': [{'value': 0, 'itemStyle': {'color': '#BEF264'}}], 'M': [{'value': 1, 'itemStyle': {'color': '#FEF08A'}}], 'H': [{'value': 0, 'itemStyle': {'color': '#FBBF24'}}], 'VH': [{'value': 0, 'itemStyle': {'color': '#F87171'}}]}, 
                                 'residual_out': {'VL': [{'value': 1, 'itemStyle': {'color': '#BBF7D0'}}], 'L': [{'value': 0, 'itemStyle': {'color': '#BEF264'}}], 'M': [{'value': 0, 'itemStyle': {'color': '#FEF08A'}}], 'H': [{'value': 0, 'itemStyle': {'color': '#FBBF24'}}], 'VH': [{'value': 0, 'itemStyle': {'color': '#F87171'}}]}, 
                                 'rsk_status_out': {'open': [{'value': 1, 'itemStyle': {'color': '#fac858'}}], 'mitigated': [{'value': 0, 'itemStyle': {'color': '#91cc75'}}], 'accepted': [{'value': 0, 'itemStyle': {'color': '#73c0de'}}], 'blocker': [{'value': 0, 'itemStyle': {'color': '#ee6666'}}]}, 
                                 'mtg_status_out': {'open': [{'value': 1, 'itemStyle': {'color': '#fac858'}}], 'in_progress': [{'value': 0, 'itemStyle': {'color': '#5470c6'}}], 'on_hold': [{'value': 0, 'itemStyle': {'color': '#ee6666'}}], 'done': [{'value': 0, 'itemStyle': {'color': '#91cc75'}}]}, 
                                 'y_max_rsk': 2}

def test_risks_levels_per_prj_grp(db, test_setUp):
    assert risks_levels_per_prj_grp() == {'names': ['Test ProjectsGroup'], 
                                          'current_out': {'VL': [{'value': 0, 'itemStyle': {'color': '#BBF7D0'}}], 'L': [{'value': 0, 'itemStyle': {'color': '#BEF264'}}], 'M': [{'value': 1, 'itemStyle': {'color': '#FEF08A'}}], 'H': [{'value': 0, 'itemStyle': {'color': '#FBBF24'}}], 'VH': [{'value': 0, 'itemStyle': {'color': '#F87171'}}]}, 
                                          'residual_out': {'VL': [{'value': 1, 'itemStyle': {'color': '#BBF7D0'}}], 'L': [{'value': 0, 'itemStyle': {'color': '#BEF264'}}], 'M': [{'value': 0, 'itemStyle': {'color': '#FEF08A'}}], 'H': [{'value': 0, 'itemStyle': {'color': '#FBBF24'}}], 'VH': [{'value': 0, 'itemStyle': {'color': '#F87171'}}]}, 
                                          'y_max_rsk': 2}
