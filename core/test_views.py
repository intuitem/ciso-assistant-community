from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.urls import reverse

from django.views.generic import ListView
from core.models import Analysis, RiskInstance, Mitigation
from core.views import *
from general.models import ParentRisk, Project, ProjectsGroup
from django.contrib.auth.views import LoginView
from .forms import LoginForm
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

import pytest

list = {}

class request:
    class user:
        is_authenticated = True

@pytest.fixture
def test_setUp(db):
    list["parentgroup"] = ProjectsGroup.objects.create()
    list["project"] = Project.objects.create(name="Test Project", parent_group = list.get("parentgroup"))
    list["analysis"] = Analysis.objects.create(project = list.get("project"))
    list["parentrisk"] = ParentRisk.objects.create()
    list["riskinstance"] = RiskInstance.objects.create(analysis = list.get("analysis"), parent_risk = list.get("parentrisk"), current_proba = "VL", current_impact="L")

def test_build_ri_clusters(db, test_setUp):
    matrix_current = [[set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()], [{'R.1'}, set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()]]
    matrix_residual = [[set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [{'R.1'}, set(), set(), set(), set()]]
    assert build_ri_clusters(list.get("analysis")) == {'current': matrix_current, 'residual': matrix_residual}

def test_generate_ra_pdf(db, test_setUp):
    assert generate_ra_pdf(request, 2)['Content-Disposition'] == f'filename="RA-2-Test Project-v-0.1.pdf"'
    assert str(generate_ra_pdf(request, 2)) == str(HttpResponse(status=200, content_type='application/pdf')) # Not good to compare strings, to review !

def test_generate_mp_pdf(db, test_setUp):
    assert generate_mp_pdf(request, 3)['Content-Disposition'] == f'filename="MP-3-Test Project-v-0.1.pdf"'
    assert str(generate_mp_pdf(request, 3)) == str(HttpResponse(status=200, content_type='application/pdf')) # Not good to compare strings, to review !
