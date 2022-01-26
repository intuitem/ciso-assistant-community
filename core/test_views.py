from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator

from django.views.generic import ListView
from core.models import Analysis, RiskInstance, Mitigation
from core.views import build_ri_clusters
from general.models import ParentRisk, Project, ProjectsGroup
from django.contrib.auth.views import LoginView
from .forms import LoginForm
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

import pytest

@pytest.mark.django_db
def test_build_ri_clusters():
    parentgroup = ProjectsGroup.objects.create()
    project = Project.objects.create(parent_group = parentgroup)
    analysis = Analysis.objects.create(project = project)
    parentrisk = ParentRisk.objects.create()
    riskinstance = RiskInstance.objects.create(analysis = analysis, parent_risk = parentrisk, current_proba = "VL", current_impact="L")
    matrix_current = [[set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()], [{'R.1'}, set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()]]
    matrix_residual = [[set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [{'R.1'}, set(), set(), set(), set()]]
    assert build_ri_clusters(analysis) == {'current': matrix_current, 'residual': matrix_residual}