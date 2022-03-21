from django.contrib.auth.models import User
from core.models import Analysis
from general.models import *
from django.utils.translation import gettext as _
import pytest


@pytest.mark.django_db
def testAnalysis():
    projectsgroup = ProjectsGroup.objects.create()
    project=Project.objects.create(parent_group=projectsgroup, name="Test")
    user = User.objects.create()
    analysis = Analysis.objects.create(
        project = project,
        auditor = user,
    )
    print(analysis) #problem proxy, maybe add str() to project.__str__ etc...
