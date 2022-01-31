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
import uuid

list = {}

@pytest.fixture
def test_password():
   return 'strong-test-pass'

  
@pytest.fixture
def create_user(db, django_user_model, test_password):
   def make_user(**kwargs):
       kwargs['password'] = test_password
       if 'username' not in kwargs:
           kwargs['username'] = str(uuid.uuid4())
       return django_user_model.objects.create_user(**kwargs)
   return make_user

@pytest.fixture
def auto_login_user(db, client, create_user, test_password):
   def make_auto_login(user=None):
       if user is None:
           user = create_user()
       client.login(username=user.username, password=test_password)
       return client, user
   return make_auto_login

def test_home(client):
    url = reverse('home')
    response = client.get(url)
    assert response.status_code == 302


def test_build_ri_clusters(db):
    list["parentgroup"] = ProjectsGroup.objects.create()
    list["project"] = Project.objects.create(parent_group = list.get("parentgroup"))
    list["analysis"] = Analysis.objects.create(project = list.get("project"))
    list["parentrisk"] = ParentRisk.objects.create()
    list["riskinstance"] = RiskInstance.objects.create(analysis = list.get("analysis"), parent_risk = list.get("parentrisk"), current_proba = "VL", current_impact="L")
    matrix_current = [[set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()], [{'R.1'}, set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()]]
    matrix_residual = [[set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [{'R.1'}, set(), set(), set(), set()]]
    assert build_ri_clusters(list.get("analysis")) == {'current': matrix_current, 'residual': matrix_residual}

'''@pytest.mark.django_db
def test_get_queryset(self):
    print(RiskAnalysisView.get_queryset(self))

@pytest.mark.django_db
def test_generate_ra_pdf():
    print(generate_ra_pdf(list.get("analysis")))'''