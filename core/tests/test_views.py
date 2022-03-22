from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser, User

from core.models import Analysis, RiskInstance, Mitigation
from core.views import *
from general.models import ParentRisk, Project, ProjectsGroup
from django.utils.translation import gettext_lazy as _

import pytest

list = {}
factory = RequestFactory()
request = factory.get('/core/analytics')
requestAnonym = factory.get('/core/analytics')

@pytest.fixture
def test_setUp(db):
    list["parentgroup"] = ProjectsGroup.objects.create()
    list["project"] = Project.objects.create(name="Test Project", parent_group = list.get("parentgroup"))
    list["analysis"] = Analysis.objects.create(project = list.get("project"))
    list["parentrisk"] = ParentRisk.objects.create()
    list["riskinstance"] = RiskInstance.objects.create(analysis = list.get("analysis"), parent_risk = list.get("parentrisk"), current_proba = "VL", current_impact="L")

@pytest.fixture
def create_user(db, django_user_model):
    def make_user(**kwargs):
        return django_user_model.objects.create_user(username='jacob', email='jacob@…', password='top_secret')
    return make_user

def test_create_user(db, create_user):
    user = create_user()
    request.user = user

def test_create_anonymousUser(db):
    requestAnonym.user = AnonymousUser()

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

def test_global_analytics(db, test_setUp):
    assert str(global_analytics(request)) == str(HttpResponse(status=200))

def test_generate_ra_pdf_login(db, test_setUp):
    assert str(generate_ra_pdf(requestAnonym, 2)) == str(HttpResponseRedirect(status=302, redirect_to="/accounts/login/?next=/core/analytics"))

def test_generate_mp_pdf_login(db, test_setUp):
    assert str(generate_mp_pdf(requestAnonym, 3)) == str(HttpResponseRedirect(status=302, redirect_to="/accounts/login/?next=/core/analytics"))
