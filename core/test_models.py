from django.db import models
from django.contrib.auth.models import User
from core.models import Analysis
from general.models import *
from asf_rm.settings import ARM_SETTINGS
from openpyxl import load_workbook
import pandas as pd
from django.urls import reverse
from django.utils.translation import ugettext as _
from datetime import date
import pytest

"""
@pytest.mark.django_db
def testAnalysis():
    projectsgroup = ProjectsGroup.objects.create()
    project=Project.objects.create(parent_group=projectsgroup)
    user = User.objects.create()
    analysis = Analysis.objects.create(
        project = project,
        auditor = user,
    )
    print(analysis) #problem proxy, maybe add str() to project.__str__ etc...
"""