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
    risk["parentgroup"] = ProjectsGroup.objects.create()
    risk["project"] = Project.objects.create(parent_group = risk.get("parentgroup"))
    risk["analysis"] = Analysis.objects.create(project = risk.get("project"))
    risk["parentrisk"] = ParentRisk.objects.create()
    risk["riskinstance"] = RiskInstance.objects.create(title = "Test Ri", analysis = risk.get("analysis"), 
                           parent_risk = risk.get("parentrisk"), current_proba = "H", current_impact="L"),
    risk["solution"] = Solution.objects.create(name = "Test Solution")
    risk["mitigation"] = Mitigation.objects.create(title = "Test Mitigation", risk_instance = RiskInstance.objects.get(title = "Test Ri"), 
                         solution = Solution.objects.get(name = "Test Solution"))

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

def test_mitigation_per_solution():
    print(mitigation_per_solution)

