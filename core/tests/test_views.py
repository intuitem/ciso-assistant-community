from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser

from core.models import Analysis, RiskScenario, SecurityMeasure
from core.views import *
from core.models import Threat, Project
from library.utils import *
from iam.models import Folder
from django.utils.translation import gettext_lazy as _

import pytest

list = {}
factory = RequestFactory()
request = factory.get('/core/overview')
requestAnonym = factory.get('/core/overview')

@pytest.fixture
def matrix_fixture():
    Folder.objects.create(
        name="Global", content_type=Folder.ContentType.ROOT, builtin=True)
    import_library(get_library('Critical matrix 5x5'))

@pytest.fixture
def test_setUp(db, matrix_fixture):
    list["root_folder"] = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    list["folder"] = Folder.objects.create(name="Test Folder", content_type=Folder.ContentType.DOMAIN, parent_folder = list.get("root_folder"))
    list["project"] = Project.objects.create(name="Test Project", folder = list.get("folder"))
    list["analysis"] = Analysis.objects.create(project=list.get("project"), rating_matrix=RiskMatrix.objects.latest('created_at'))
    list["threat"] = Threat.objects.create(name="Test Threat", folder = list.get("root_folder"))
    list["riskscenario"] = RiskScenario.objects.create(analysis=list.get("analysis"), threat=list.get("threat"), current_proba=0, current_impact=1)

@pytest.fixture
def create_user(db, django_user_model):
    def make_user(**kwargs):
        return django_user_model.objects.create_user(email='john.doe@example.com', password='top_secret')
    return make_user

def test_create_user(db, create_user):
    user = create_user()
    request.user = user

def test_create_anonymousUser(db):
    requestAnonym.user = AnonymousUser()

def test_build_ri_clusters(db, test_setUp):
    matrix_current = [[set(), {'R.1'}, set(), set(), set()], [set(), set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                      [set(), set(), set(), set(), set()]]
    matrix_residual = [[set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [set(), set(), set(), set(), set()], [set(), set(), set(), set(), set()],
                       [set(), set(), set(), set(), set()]]
    assert build_ri_clusters(list.get("analysis")) == {'current': matrix_current, 'residual': matrix_residual}

# def test_generate_ra_pdf(db, test_setUp):
#     assert generate_ra_pdf(request, str(list["analysis"].id))['Content-Disposition'] == f'filename="RA-2-Test Project-v-0.1.pdf"'
#     assert str(generate_ra_pdf(request, 2)) == str(HttpResponse(status=200, content_type='application/pdf')) # Not good to compare strings, to review !

# def test_generate_mp_pdf(db, test_setUp):
#     assert generate_mp_pdf(request, 3)['Content-Disposition'] == f'filename="MP-3-Test Project-v-0.1.pdf"'
#     assert str(generate_mp_pdf(request, 3)) == str(HttpResponse(status=200, content_type='application/pdf')) # Not good to compare strings, to review !

def test_global_overview(db, test_setUp):
    assert str(global_overview(request)) == str(HttpResponse(status=200))

def test_generate_ra_pdf_login(db, test_setUp):
    assert str(generate_ra_pdf(requestAnonym, 2)) == str(HttpResponseRedirect(status=302, redirect_to="/accounts/login/?next=/core/overview"))

def test_generate_mp_pdf_login(db, test_setUp):
    assert str(generate_mp_pdf(requestAnonym, 3)) == str(HttpResponseRedirect(status=302, redirect_to="/accounts/login/?next=/core/overview"))
